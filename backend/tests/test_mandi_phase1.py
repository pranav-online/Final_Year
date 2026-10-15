"""Phase 1 acceptance checks: real mandi data foundation."""
from datetime import date, timedelta

import pytest
import requests
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from config.security import create_access_token
from services.mandi import config, ingest, scheduler
from services.mandi.analytics import data_health, weekly_price_history
from services.mandi.normalize import (
    FLAG_MIN_GT_MODAL,
    FLAG_NONPOSITIVE,
    FLAG_OUTLIER,
    build_price_row,
    normalize_datagov_record,
    parse_date,
)
from services.mandi.sources import DataGovClient, SourceError, parse_dashboard_arrivals, request_json
from services.mandi.store import MongoMandiStore, SqliteMandiStore, set_store


# ─── Helpers ───────────────────────────────────────────────

def datagov_record(day: date, market="APMC Nasik ", modal=2000, commodity="Onion",
                   min_price=None, max_price=None, variety="Local", grade="FAQ"):
    return {
        "state": "Maharashtra", "district": "Nashik", "market": market,
        "commodity": commodity, "variety": variety, "grade": grade,
        "arrival_date": day.strftime("%d/%m/%Y"),
        "min_price": modal - 200 if min_price is None else min_price,
        "max_price": modal + 200 if max_price is None else max_price,
        "modal_price": modal,
    }


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class CappedDataGovSession:
    """Mimics data.gov.in with the sample key: ignores `limit`, returns 10 rows per page."""

    def __init__(self, records, cap=10):
        self.records, self.cap, self.calls = records, cap, 0

    def request(self, method, url, params=None, **kwargs):
        self.calls += 1
        offset = int(params["offset"])
        page = self.records[offset:offset + self.cap]
        return FakeResponse(payload={"total": len(self.records), "count": len(page), "records": page})


class FakeDataGovClient:
    def __init__(self, by_name):
        self.by_name = by_name

    def fetch_commodity(self, name):
        records = self.by_name.get(name, [])
        return {"commodity_name": name, "total": len(records), "records": records, "pages": 1}


@pytest.fixture
def sqlite_store(tmp_path):
    store = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    yield store
    store.close()


@pytest.fixture
def mongo_store():
    return MongoMandiStore(AsyncMongoMockClient()["alip_test"])


@pytest.fixture(params=["sqlite", "mongo"])
def store(request, tmp_path):
    if request.param == "sqlite":
        s = SqliteMandiStore(tmp_path / "mandi.sqlite3")
        yield s
        s.close()
    else:
        yield MongoMandiStore(AsyncMongoMockClient()["alip_test"])


# ─── Normalisation ─────────────────────────────────────────

def test_normalize_trims_names_parses_dates_and_maps_commodity():
    row, problem = normalize_datagov_record(datagov_record(date(2026, 10, 14)))
    assert problem is None
    assert row["market"] == "APMC Nasik"
    assert row["date"] == "2026-10-14"
    assert row["commodity"] == "onion"
    assert row["unit"] == "Rs/quintal"
    assert row["market_key"] == "maharashtra|nashik|apmc nasik"
    assert row["flags"] == []


def test_normalize_flags_invalid_prices_instead_of_dropping():
    row, _ = normalize_datagov_record(datagov_record(date(2026, 10, 14), modal=1000, min_price=1500))
    assert FLAG_MIN_GT_MODAL in row["flags"]
    row, _ = normalize_datagov_record(datagov_record(date(2026, 10, 14), modal=0, min_price=0, max_price=0))
    assert FLAG_NONPOSITIVE in row["flags"]


def test_normalize_rejects_unmapped_commodity_and_bad_date():
    _, problem = normalize_datagov_record(datagov_record(date(2026, 10, 14), commodity="Dragon Fruit"))
    assert problem == "unmapped_commodity"
    bad = datagov_record(date(2026, 10, 14))
    bad["arrival_date"] = "yesterday"
    assert normalize_datagov_record(bad)[1] == "unparseable_date"


def test_parse_date_formats():
    assert parse_date("14/10/2026") == parse_date("14-10-2026") == parse_date("2026-10-14") == "2026-10-14"


def test_resolve_commodity_aliases():
    assert config.resolve_commodity("  Tamatar ") == "tomato"
    assert config.resolve_commodity("Paddy(Common)") == "paddy"
    assert config.resolve_commodity("aloo") == "potato"
    assert config.resolve_commodity("kiwi") is None


# ─── Source clients ────────────────────────────────────────

def test_datagov_client_pages_past_10_row_cap():
    records = [datagov_record(date(2026, 10, 14), market=f"M{i}") for i in range(25)]
    session = CappedDataGovSession(records)
    result = DataGovClient(api_key="k", page_size=1000, session=session).fetch_commodity("Onion")
    assert result["total"] == 25
    assert len(result["records"]) == 25
    assert session.calls == 3


def test_clients_send_an_explicit_user_agent():
    # Both government APIs block the default python-requests User-Agent.
    from services.mandi.sources import AgmarknetClient, new_session

    assert "python-requests" not in new_session().headers["User-Agent"]
    assert "ALIP" in AgmarknetClient().session.headers["User-Agent"]
    assert "ALIP" in DataGovClient(api_key="k").session.headers["User-Agent"]


def test_request_json_retries_network_errors_and_5xx():
    responses = [requests.ConnectionError("down"), FakeResponse(503), FakeResponse(payload={"ok": 1})]

    class Session:
        def request(self, *args, **kwargs):
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

    assert request_json(Session(), "GET", "http://x", sleep=lambda s: None) == {"ok": 1}


def test_request_json_gives_up_after_retries():
    class Session:
        def request(self, *args, **kwargs):
            return FakeResponse(payload=None, text="<html>WAF</html>")

    with pytest.raises(SourceError):
        request_json(Session(), "GET", "http://x", retries=2, sleep=lambda s: None)


def test_parse_dashboard_arrivals_uses_column_dates():
    payload = {"data": {
        "columns": [
            {"key": "price_group", "columns": [
                {"key": "as_on_price", "title": "12 Oct, 2026"},
                {"key": "one_day_ago_price", "title": "11 Oct, 2026"},
                {"key": "two_day_ago_price", "title": "10 Oct, 2026"}]},
            {"key": "arrival_group", "columns": [
                {"key": "as_on_arrival", "title": "12 Oct, 2026"},
                {"key": "one_day_ago_arrival", "title": "11 Oct, 2026"},
                {"key": "two_day_ago_arrival", "title": "10 Oct, 2026"}]},
        ],
        "records": [{"cmdt_name": "Tomato", "as_on_price": "1500.50", "as_on_arrival": "9000.25",
                     "one_day_ago_price": "1400", "one_day_ago_arrival": "8000",
                     "two_day_ago_price": "1300", "two_day_ago_arrival": "7000"}],
    }}
    rows = parse_dashboard_arrivals(payload)
    assert [r["date"] for r in rows] == ["2026-10-12", "2026-10-11", "2026-10-10"]
    assert rows[0]["arrival_tonnes"] == 9000.25
    assert rows[0]["national_price"] == 1500.5


# ─── Ingestion ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_is_complete_and_idempotent(store):
    day = date(2026, 10, 14)
    client = FakeDataGovClient({
        "Onion": [datagov_record(day, market=f"M{i}") for i in range(12)],
        "Tomato": [datagov_record(day, market="Kolar", commodity="Tomato")],
    })

    first = await ingest.ingest_prices(store, client, commodities=["onion", "tomato"])
    assert first["complete"] is True
    assert first["fetched"] == first["total_reported"] == 13
    assert first["inserted"] == 13 and first["updated"] == 0
    assert first["status"] == "ok"

    second = await ingest.ingest_prices(store, client, commodities=["onion", "tomato"])
    assert second["inserted"] == 0 and second["updated"] == 13
    stats = await store.price_stats()
    assert stats["rows"] == 13
    assert await store.duplicate_groups() == 0


@pytest.mark.asyncio
async def test_ingest_reports_partial_when_a_commodity_fails(sqlite_store):
    class FlakyClient(FakeDataGovClient):
        def fetch_commodity(self, name):
            if name == "Tomato":
                raise SourceError("HTTP 503")
            return super().fetch_commodity(name)

    client = FlakyClient({"Onion": [datagov_record(date(2026, 10, 14))]})
    report = await ingest.ingest_prices(sqlite_store, client, commodities=["onion", "tomato"])
    assert report["status"] == "partial"
    assert report["complete"] is False
    assert report["stored"] == 1


@pytest.mark.asyncio
async def test_interrupted_run_keeps_commodities_already_fetched(sqlite_store):
    class CrashingClient(FakeDataGovClient):
        def fetch_commodity(self, name):
            if name == "Tomato":
                raise KeyboardInterrupt  # e.g. the server process is stopped mid-pull
            return super().fetch_commodity(name)

    client = CrashingClient({"Onion": [datagov_record(date(2026, 10, 14), market=f"M{i}") for i in range(5)]})
    with pytest.raises(KeyboardInterrupt):
        await ingest.ingest_prices(sqlite_store, client, commodities=["onion", "tomato"])
    assert (await sqlite_store.price_stats())["rows"] == 5


@pytest.mark.asyncio
async def test_low_volume_day_raises_warning(sqlite_store):
    big = FakeDataGovClient({"Onion": [datagov_record(date(2026, 10, 1), market=f"M{i}") for i in range(20)]})
    for _ in range(3):
        await ingest.ingest_prices(sqlite_store, big, commodities=["onion"])
    small = FakeDataGovClient({"Onion": [datagov_record(date(2026, 10, 2), market="M1")]})
    report = await ingest.ingest_prices(sqlite_store, small, commodities=["onion"])
    assert report["status"] == "warning"
    assert any(w.startswith("low_volume") for w in report["warnings"])


@pytest.mark.asyncio
async def test_outlier_is_flagged_but_kept(store):
    start = date(2026, 9, 1)
    normal = [datagov_record(start + timedelta(days=i), modal=2000 + (i % 3) * 20) for i in range(10)]
    client = FakeDataGovClient({"Onion": normal})
    await ingest.ingest_prices(store, client, commodities=["onion"])

    spike_day = start + timedelta(days=10)
    client = FakeDataGovClient({"Onion": [datagov_record(spike_day, modal=9000)]})
    report = await ingest.ingest_prices(store, client, commodities=["onion"])

    assert report["outliers_flagged"] == 1
    rows = await store.find_prices("onion", date_from=spike_day.isoformat())
    assert len(rows) == 1 and FLAG_OUTLIER in rows[0]["flags"]


# ─── Read side ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weekly_history_medians_and_daily_feed_preference(store):
    monday = date(2026, 9, 7)
    rows = []
    for offset, modal in enumerate([1000, 1200, 1400]):  # one week, three days
        row, _ = normalize_datagov_record(datagov_record(monday + timedelta(days=offset), modal=modal))
        rows.append(row)
    # CEDA copy of the first day with a different price: the daily feed must win.
    ceda_row, _ = build_price_row(
        date=monday.isoformat(), state="Maharashtra", district="Nashik", market="APMC Nasik",
        commodity_raw="Onion", variety="Local", grade="FAQ", min_price=100, max_price=9000,
        modal_price=5000, source="ceda", raw={},
    )
    rows.append(ceda_row)
    bad, _ = normalize_datagov_record(datagov_record(monday + timedelta(days=7), modal=1500, min_price=1600))
    rows.append(bad)
    await store.upsert_prices(rows)

    result = await weekly_price_history(store, "onion", weeks=8, today=monday + timedelta(days=10))
    assert len(result["series"]) == 1  # the only row in week 2 is invalid and excluded
    week = result["series"][0]
    assert week["week_start"] == "2026-09-07"
    assert week["modal_price"] == 1200
    assert week["modal_p10"] == 1040 and week["modal_p90"] == 1360
    assert week["min_price"] == 1000  # median of daily mins (800, 1000, 1200)
    assert week["observations"] == 3
    assert week["sources"] == ["datagov"]
    assert result["excluded_invalid_rows"] == 1


@pytest.mark.asyncio
async def test_health_reports_storage_and_last_pull(sqlite_store):
    client = FakeDataGovClient({"Onion": [datagov_record(date.today())]})
    await ingest.ingest_prices(sqlite_store, client, commodities=["onion"])
    health = await data_health(sqlite_store)
    assert health["storage"] == "sqlite"
    assert health["status"] == "ok"
    assert health["duplicate_groups"] == 0
    assert health["sources"]["datagov"]["last_run"]["complete"] is True


# ─── API and scheduler ─────────────────────────────────────

def test_history_endpoint_requires_broker_and_serves_rows(sqlite_store):
    from main import app

    set_store(sqlite_store)
    try:
        client = TestClient(app)
        assert client.get("/market/prices/history?commodity=onion").status_code == 401
        farmer = {"Authorization": f"Bearer {create_access_token({'sub': 'f', 'role': 'farmer'})}"}
        assert client.get("/market/prices/history?commodity=onion", headers=farmer).status_code == 403

        broker = {"Authorization": f"Bearer {create_access_token({'sub': 'b', 'role': 'broker'})}"}
        assert client.get("/market/prices/history?commodity=kiwi", headers=broker).status_code == 404
        res = client.get("/market/prices/history?commodity=pyaz", headers=broker)
        assert res.status_code == 200 and res.json()["commodity"] == "onion"
        assert client.get("/health/data").json()["storage"] == "sqlite"
    finally:
        set_store(None)


def test_scheduler_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "0")
    assert scheduler.start_scheduler() is None
    assert scheduler.scheduler_status()["running"] is False


def test_only_one_process_can_hold_the_scheduler_lock(tmp_path):
    lock = tmp_path / "scheduler.lock"
    first = scheduler.acquire_singleton_lock(lock)
    try:
        assert first is not None
        assert scheduler.acquire_singleton_lock(lock) is None  # a second worker is refused
    finally:
        first.close()
    second = scheduler.acquire_singleton_lock(lock)  # released lock can be taken again
    assert second is not None
    second.close()


@pytest.mark.asyncio
async def test_scheduler_jobs_are_single_instance():
    sched = scheduler.build_scheduler()
    sched.start(paused=True)  # job defaults are applied once the scheduler starts
    try:
        ids = {job.id for job in sched.get_jobs()}
        assert {"ingest_prices_1430", "ingest_prices_1730", "ingest_prices_2030", "ingest_prices_2330",
                "ingest_arrivals_1630", "seed_masters_weekly"} <= ids
        assert not any(job_id.startswith("ingest_prices_0") for job_id in ids)  # feed is empty mornings
        for job in sched.get_jobs():
            assert job.max_instances == 1 and job.coalesce is True
    finally:
        sched.shutdown(wait=False)
