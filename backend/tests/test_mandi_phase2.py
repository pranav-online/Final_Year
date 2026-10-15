"""Phase 2 acceptance checks: descriptive signals and alerts."""
import math
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from config.security import create_access_token
from services.mandi import insights
from services.mandi import signals as sig
from services.mandi.config import state_key
from services.mandi.normalize import build_price_row
from services.mandi.store import MarketWeekAggregator, SqliteMandiStore, set_store

MONDAY = date(2026, 1, 5)


def weekly(prices, start=MONDAY):
    return [{"week_start": (start + timedelta(weeks=i)).isoformat(), "price": p} for i, p in enumerate(prices)]


def seasonal_prices(years=3, start=date(2023, 1, 2), base=2000):
    """Onion-like series: peaks around Oct-Nov, bottoms around May."""
    points, day = [], start
    while day < start + timedelta(weeks=52 * years):
        angle = 2 * math.pi * (day.timetuple().tm_yday - 305) / 365  # peak ~1 Nov
        points.append({"week_start": day.isoformat(), "price": base * (1 + 0.35 * math.cos(angle))})
        day += timedelta(weeks=1)
    return points


def price_row(day, price, state="Maharashtra", market="Lasalgaon", source="datagov", min_price=None):
    row, problem = build_price_row(
        date=day.isoformat(), state=state, district="Nashik", market=market, commodity_raw="Onion",
        variety="Red", grade="FAQ", min_price=price - 100 if min_price is None else min_price,
        max_price=price + 100, modal_price=price, source=source, raw={})
    assert problem is None
    return row


@pytest.fixture
def store(tmp_path):
    s = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    yield s
    s.close()


# ─── Signal maths ──────────────────────────────────────────

def test_no_look_ahead_signals_unchanged_when_future_data_removed():
    series = seasonal_prices()
    arrivals = [{"week_start": p["week_start"], "tonnes_per_day": 1000 + i % 7 * 50} for i, p in enumerate(series)]
    week = series[120]["week_start"]
    full = sig.week_signals("onion", series, week, arrivals)
    truncated = sig.week_signals("onion", series[:121], week, arrivals[:121])
    assert full == truncated
    assert full["momentum_4w"] is not None and full["seasonal_norm"] is not None


def test_seasonal_index_peaks_oct_nov_and_bottoms_in_may():
    index = sig.seasonal_index(seasonal_prices())
    assert max(index, key=index.get) in {10, 11}
    assert min(index, key=index.get) in {4, 5, 6}


def test_seasonal_norm_uses_only_earlier_years():
    series = seasonal_prices(years=1, start=date(2026, 1, 5))  # a single year
    assert sig.seasonal_norm(series, series[-1]["week_start"]) is None


def test_momentum_and_robust_z_detect_a_crash():
    prices = [2000 + (i % 2) * 20 for i in range(30)] + [1000]
    s = sig.week_signals("onion", weekly(prices), weekly(prices)[-1]["week_start"])
    assert s["momentum_4w"] == pytest.approx(1000 / 2000 - 1, abs=0.02)
    assert s["price_z"] <= -sig.Z_ALERT


def test_flat_series_has_no_z_and_no_alert():
    s = sig.week_signals("onion", weekly([2000] * 30), weekly([2000] * 30)[-1]["week_start"])
    assert s["price_z"] is None  # zero spread -> no z, never a false alert
    assert s["momentum_4w"] == 0


@pytest.mark.parametrize("arrivals,momentum,expected", [
    (1.5, 0.10, "strong_demand"),
    (0.6, 0.10, "supply_shortage"),
    (1.5, -0.10, "glut"),
    (0.6, -0.10, "weak_demand"),
    (1.0, 0.0, "balanced"),
    (None, 0.1, "insufficient_data"),
])
def test_quadrants(arrivals, momentum, expected):
    assert sig.quadrant(arrivals, momentum) == expected


def test_urgency_is_bounded_and_tiered():
    for ratio in (0.2, 1.0, 1.5, 3.0, 10.0):
        for momentum in (-0.9, -0.2, 0.0, 0.5):
            for z in (-10, -3, 0, 4):
                for crop in ("tomato", "onion", "wheat"):
                    score, _ = sig.urgency_score(crop, ratio, momentum, z)
                    assert 1 <= score <= 10
                tomato, _ = sig.urgency_score("tomato", ratio, momentum, z)
                wheat, _ = sig.urgency_score("wheat", ratio, momentum, z)
                assert tomato >= wheat
    assert sig.urgency_score("tomato") == (None, ["not enough data"])


def test_daily_arrival_surge_ratio():
    days = [{"date": (date(2026, 9, 1) + timedelta(days=i)).isoformat(), "arrival_tonnes": 1000.0} for i in range(20)]
    days.append({"date": "2026-09-21", "arrival_tonnes": 2500.0})
    assert sig.daily_arrival_surge(days, "2026-09-21") == pytest.approx(2.5)
    assert sig.daily_arrival_surge(days[:5] + days[-1:], "2026-09-21") is None  # < 7 days of history


def test_state_aliases():
    assert state_key("Keralam") == state_key(" kerala ") == "kerala"


# ─── Aggregation ───────────────────────────────────────────

def test_market_week_aggregator_prefers_daily_feed_and_skips_invalid_rows():
    agg = MarketWeekAggregator()
    rows = [price_row(MONDAY, 1000), price_row(MONDAY, 5000, source="ceda"),
            price_row(MONDAY + timedelta(days=1), 1200),
            price_row(MONDAY + timedelta(days=2), 900, min_price=2000)]  # min > modal: invalid
    for row in sorted(rows, key=lambda r: (r["market_key"], r["date"])):
        agg.add(row)
    result = agg.finish()
    assert len(result) == 1
    assert result[0]["price"] == 1100 and result[0]["observations"] == 2


# ─── Jobs, alerts and API ──────────────────────────────────

async def seed_history(store, weeks=60, crash=False):
    rows = []
    for i in range(weeks):
        day = date(2025, 8, 4) + timedelta(weeks=i)
        price = 2000 + (i % 3) * 30
        if crash and i == weeks - 1:
            price = 900
        rows.append(price_row(day, price))
        rows.append(price_row(day, price * 1.1, state="Karnataka", market="Kolar"))
    await store.upsert_prices(rows)
    return date(2025, 8, 4) + timedelta(weeks=weeks - 1)


@pytest.mark.asyncio
async def test_compute_signals_builds_national_state_and_market_scopes(store):
    last = await seed_history(store)
    summary = await insights.compute_signals(store, ["onion"], today=last)
    assert summary["onion"]["weeks_of_history"] == 60
    docs = await store.find_signals("onion")
    assert {d["level"] for d in docs} == {"national", "state", "market"}
    assert {d["scope_key"] for d in docs if d["level"] == "state"} == {"maharashtra", "karnataka"}
    national = next(d for d in docs if d["level"] == "national")
    assert national["momentum_4w"] is not None and national["volatility_8w"] is not None
    assert national["quadrant"] == "insufficient_data"  # no arrivals stored yet


@pytest.mark.asyncio
async def test_price_crash_alert_fires_once_per_24h(store):
    last = await seed_history(store, crash=True)
    await insights.compute_signals(store, ["onion"], today=last)
    first = await insights.generate_alerts(store, listings=[])
    second = await insights.generate_alerts(store, listings=[])
    assert first["created"].get("price_crash", 0) >= 1
    assert second["created"] == {}
    assert all(a["type"] == "price_crash" for a in await store.find_alerts())


@pytest.mark.asyncio
async def test_flat_market_raises_no_alerts(store):
    last = await seed_history(store)
    await insights.compute_signals(store, ["onion"], today=last)
    assert (await insights.generate_alerts(store, listings=[]))["created"] == {}


@pytest.mark.asyncio
async def test_arrival_surge_alert_fires_once(store):
    days = [date(2026, 9, 1) + timedelta(days=i) for i in range(21)]
    await store.upsert_arrivals([{
        "_id": f"agmarknet|national|onion|{d}", "date": d.isoformat(), "commodity": "onion",
        "level": "national", "arrival_tonnes": 2500.0 if d == days[-1] else 1000.0,
    } for d in days])
    first = await insights.generate_alerts(store, listings=[])
    again = await insights.generate_alerts(store, listings=[])
    assert first["created"] == {"arrival_surge": 1}
    assert again["created"] == {}


@pytest.mark.asyncio
async def test_glut_and_listing_opportunity_alerts(store):
    shortage = {"_id": "onion|state|andhra pradesh", "commodity": "onion", "commodity_name": "Onion",
                "level": "state", "scope_key": "andhra pradesh", "scope_name": "Andhra Pradesh",
                "state": "Andhra Pradesh", "quadrant": "supply_shortage", "arrivals_ratio": 0.6,
                "momentum_4w": 0.12, "price_z": None, "price_vs_norm": None, "price": 2400,
                "week_start": "2026-10-12", "stale": False, "urgency": 2, "urgency_reasons": []}
    glut = {**shortage, "_id": "onion|state|maharashtra", "scope_key": "maharashtra",
            "scope_name": "Maharashtra", "state": "Maharashtra", "quadrant": "glut",
            "arrivals_ratio": 1.6, "momentum_4w": -0.18}
    await store.replace_signals("onion", [shortage, glut])
    listing = {"_id": "L1", "crop_name": "onion", "location": "guntur", "quantity_kg": 2500,
               "price_per_kg": 22, "created_at": datetime.now(timezone.utc).isoformat()}
    old = {**listing, "_id": "L2", "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()}

    result = await insights.generate_alerts(store, listings=[listing, old])
    assert result["created"] == {"supply_shortage": 1, "glut": 1, "listing_opportunity": 1}
    opportunity = next(a for a in await store.find_alerts() if a["type"] == "listing_opportunity")
    assert opportunity["listing_id"] == "L1"


@pytest.mark.asyncio
async def test_overview_endpoint_is_broker_only_and_not_shadowed_by_region_route(store, monkeypatch):
    from main import app

    last = await seed_history(store)
    await insights.compute_signals(store, ["onion"], today=last)

    async def no_listings():
        return [{"crop_name": "Pyaz", "location": "pune", "quantity_kg": 400}]

    monkeypatch.setattr(insights, "load_available_listings", no_listings)
    set_store(store)
    try:
        client = TestClient(app)
        broker = {"Authorization": f"Bearer {create_access_token({'sub': 'b', 'role': 'broker'})}"}
        farmer = {"Authorization": f"Bearer {create_access_token({'sub': 'f', 'role': 'farmer'})}"}
        assert client.get("/market/demand/overview", headers=farmer).status_code == 403

        body = client.get("/market/demand/overview?level=state&commodities=onion", headers=broker).json()
        assert body["success"] is True and body["level"] == "state"  # not the legacy region analysis
        assert {r["scope_name"] for r in body["rows"]} == {"Maharashtra", "Karnataka"}
        assert body["listing_supply"]["onion"]["quantity_kg"] == 400
        assert body["listing_supply"]["onion"]["states"] == ["Maharashtra"]

        alerts = client.get("/market/demand/alerts", headers=broker)
        assert alerts.status_code == 200 and alerts.json()["total"] == 0
        assert client.get("/market/demand/overview?commodities=kiwi", headers=broker).status_code == 404
    finally:
        set_store(None)
