"""Ingestion jobs. Each run writes an ingest report so completeness can be audited."""
import asyncio
import logging
import statistics
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from services.mandi.config import (
    BACKFILL_STATES,
    COMMODITIES,
    resolve_commodity,
    scoped_commodities,
    using_sample_key,
)
from services.mandi.normalize import (
    FLAG_OUTLIER,
    build_price_row,
    is_usable,
    normalize_datagov_record,
    utc_now_iso,
)
from services.mandi.sources import (
    AgmarknetClient,
    CedaClient,
    DataGovClient,
    SourceError,
    parse_dashboard_arrivals,
)
from services.mandi.store import get_store

OUTLIER_WINDOW_DAYS = 28
OUTLIER_MAD_MULTIPLIER = 5
OUTLIER_MIN_HISTORY = 5
LOW_VOLUME_RATIO = 0.5

log = logging.getLogger("alip.mandi.ingest")


def _new_report(source: str) -> dict:
    return {
        "run_id": f"{source}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}",
        "source": source,
        "started_at": utc_now_iso(),
        "status": "running",
        "errors": [],
        "warnings": [],
    }


async def _finish(store, report: dict) -> dict:
    report["finished_at"] = utc_now_iso()
    await store.add_ingest_report(report)
    return report


# ─── Daily prices (data.gov.in) ────────────────────────────
async def ingest_prices(store=None, client=None, commodities=None) -> dict:
    store = store or await get_store()
    client = client or DataGovClient()
    commodities = commodities or scoped_commodities()
    report = _new_report("datagov")
    report.update({
        "storage": store.name,
        "sample_key": using_sample_key(),
        "commodities": commodities,
        "total_reported": 0,
        "fetched": 0,
        "pages": 0,
        "per_commodity": {},
        "rejected": {},
    })

    fetched_at = utc_now_iso()
    rejected = Counter()
    dates = set()
    report.update({"stored": 0, "inserted": 0, "updated": 0,
                   "duplicates_in_feed": 0, "flagged_invalid": 0})
    for cid in commodities:
        for source_name in COMMODITIES[cid]["datagov"]:
            try:
                result = await asyncio.to_thread(client.fetch_commodity, source_name)
            except SourceError as exc:
                report["errors"].append(f"{source_name}: {exc}")
                log.warning("data.gov.in %s failed: %s", source_name, exc)
                continue
            report["total_reported"] += result["total"]
            report["fetched"] += len(result["records"])
            report["pages"] += result["pages"]
            report["per_commodity"][source_name] = {
                "total": result["total"], "fetched": len(result["records"]),
            }
            log.info("data.gov.in %s: fetched %d/%d rows in %d pages",
                     source_name, len(result["records"]), result["total"], result["pages"])

            rows = []
            for record in result["records"]:
                row, problem = normalize_datagov_record(record, fetched_at)
                if problem:
                    rejected[problem] += 1
                elif row["commodity"] not in commodities:
                    rejected["out_of_scope_commodity"] += 1
                else:
                    rows.append(row)

            # Save each commodity as soon as it is fetched, so an interrupted
            # run (crash, restart, machine sleep) keeps what it already pulled.
            unique = {row["_id"]: row for row in rows}
            saved = await store.upsert_prices(list(unique.values()))
            report["inserted"] += saved["inserted"]
            report["updated"] += saved["updated"]
            report["stored"] += len(unique)
            report["duplicates_in_feed"] += len(rows) - len(unique)
            report["flagged_invalid"] += sum(1 for row in unique.values() if not is_usable(row))
            dates.update(row["date"] for row in unique.values())

    report["rejected"] = dict(rejected)
    report["dates"] = sorted(dates)
    report["unmapped_rate"] = (
        round(rejected["unmapped_commodity"] / report["fetched"], 4) if report["fetched"] else 0.0
    )
    report["outliers_flagged"] = (
        await flag_outliers(store, report["dates"], commodities) if report["dates"] else 0
    )

    # Volume sanity check against recent successful pulls.
    history = [
        r["total_reported"] for r in await store.recent_ingest_reports("datagov", 14)
        if r.get("status") in {"ok", "warning"} and r.get("total_reported")
    ]
    if len(history) >= 3:
        median_total = statistics.median(history)
        if report["total_reported"] < LOW_VOLUME_RATIO * median_total:
            report["warnings"].append(
                f"low_volume: {report['total_reported']} rows vs trailing median {median_total:.0f}"
            )

    report["complete"] = report["fetched"] == report["total_reported"] and not report["errors"]
    if report["errors"] and report["fetched"] == 0:
        report["status"] = "failed"
    elif not report["complete"]:
        report["status"] = "partial"
    elif report["warnings"]:
        report["status"] = "warning"
    else:
        report["status"] = "ok"
    return await _finish(store, report)


async def flag_outliers(store, dates: list[str], commodities: list[str]) -> int:
    """
    Flag (never drop) rows whose modal price is more than 5 x MAD away from the
    same series' median over the previous 28 days. Returns rows newly flagged.
    """
    target_dates = set(dates)
    first = date.fromisoformat(min(dates)) - timedelta(days=OUTLIER_WINDOW_DAYS)
    updates, newly_flagged = {}, 0

    for cid in commodities:
        rows = await store.find_prices(cid, date_from=first.isoformat(), date_to=max(dates))
        series = defaultdict(list)
        for row in rows:
            series[(row["market_key"], row["variety"], row["grade"])].append(row)

        for group in series.values():
            for row in group:
                if row["date"] not in target_dates:
                    continue
                day = date.fromisoformat(row["date"])
                window_start = (day - timedelta(days=OUTLIER_WINDOW_DAYS)).isoformat()
                history = [
                    r["modal_price"] for r in group
                    if window_start <= r["date"] < row["date"] and is_usable(r)
                ]
                is_outlier = False
                if len(history) >= OUTLIER_MIN_HISTORY:
                    median = statistics.median(history)
                    mad = statistics.median(abs(x - median) for x in history)
                    is_outlier = mad > 0 and abs(row["modal_price"] - median) > OUTLIER_MAD_MULTIPLIER * mad

                flags = [f for f in row.get("flags") or [] if f != FLAG_OUTLIER]
                if is_outlier:
                    flags.append(FLAG_OUTLIER)
                if flags != (row.get("flags") or []):
                    updates[row["_id"]] = flags
                    newly_flagged += int(is_outlier)

    await store.set_flags(updates)
    return newly_flagged


# ─── Reference masters (Agmarknet 2.0) ─────────────────────
async def seed_masters(store=None, client=None) -> dict:
    store = store or await get_store()
    client = client or AgmarknetClient()
    report = _new_report("agmarknet_masters")
    try:
        commodities = await asyncio.to_thread(client.commodities)
        states = await asyncio.to_thread(client.states)
    except SourceError as exc:
        report["errors"].append(str(exc))
        report["status"] = "failed"
        return await _finish(store, report)

    await store.replace_master("agmarknet_commodity", [{
        "_id": c["id"], "name": " ".join(str(c.get("cmdt_name", "")).split()),
        "group": c.get("cmdt_group"), "varieties": [v.get("variety_name") for v in c.get("varieties") or []],
        "canonical": resolve_commodity(c.get("cmdt_name")),
    } for c in commodities])
    await store.replace_master("agmarknet_state", [{
        "_id": s["id"], "name": " ".join(str(s.get("state_name", "")).split()),
        "lgd_code": s.get("state_lg_code"),
        "districts": [{
            "id": d.get("id"), "name": " ".join(str(d.get("district_name", "")).split()),
            "lgd_code": d.get("district_lg_code"),
        } for d in s.get("districts") or []],
    } for s in states])

    mapping = await agmarknet_commodity_ids(store)
    report.update({
        "commodities": len(commodities),
        "states": len(states),
        "scope_mapping": mapping,
        "status": "ok" if all(mapping.values()) else "warning",
    })
    missing = [cid for cid, mid in mapping.items() if mid is None]
    if missing:
        report["warnings"].append(f"no Agmarknet id for: {', '.join(missing)}")
    return await _finish(store, report)


async def agmarknet_commodity_ids(store) -> dict:
    masters = await store.get_master("agmarknet_commodity")
    by_name = {m["name"].lower(): m["_id"] for m in masters}
    return {
        cid: by_name.get(COMMODITIES[cid]["agmarknet"].lower())
        for cid in scoped_commodities()
    }


# ─── National arrivals (Agmarknet 2.0 dashboard) ───────────
async def ingest_arrivals(store=None, client=None, as_of: date = None) -> dict:
    """Best-effort: national price + arrival tonnage for the last three reported days."""
    store = store or await get_store()
    client = client or AgmarknetClient()
    report = _new_report("agmarknet_arrivals")

    mapping = await agmarknet_commodity_ids(store)
    if not any(mapping.values()):
        await seed_masters(store)
        mapping = await agmarknet_commodity_ids(store)
    ids = [mid for mid in mapping.values() if mid]
    if not ids:
        report["errors"].append("Agmarknet commodity masters unavailable")
        report["status"] = "failed"
        return await _finish(store, report)

    try:
        payload = await asyncio.to_thread(client.national_price_arrivals, as_of or date.today(), ids)
    except SourceError as exc:
        report["errors"].append(str(exc))
        report["status"] = "failed"
        return await _finish(store, report)

    fetched_at = utc_now_iso()
    rows = []
    for item in parse_dashboard_arrivals(payload):
        cid = resolve_commodity(item["commodity_raw"])
        if cid is None or cid not in mapping:
            continue
        rows.append({
            **item,
            "_id": f"agmarknet|national|{cid}|{item['date']}",
            "commodity": cid,
            "level": "national",
            "unit": "tonnes",
            "price_unit": "Rs/quintal",
            "source": "agmarknet",
            "fetched_at": fetched_at,
        })
    report.update(await store.upsert_arrivals(rows))
    report["rows"] = len(rows)
    report["dates"] = sorted({r["date"] for r in rows})
    # The dashboard returns a fixed list of ~24 major commodities regardless of
    # the filter (banana and rice are not in it), so name the gaps explicitly.
    uncovered = sorted(set(mapping) - {r["commodity"] for r in rows})
    report["commodities_without_arrivals"] = uncovered
    if uncovered:
        report["warnings"].append(f"no national arrivals from Agmarknet for: {', '.join(uncovered)}")
    report["status"] = "warning" if report["warnings"] or not rows else "ok"
    return await _finish(store, report)


# ─── Historical backfill (CEDA) ────────────────────────────
def _year_chunks(start: date, end: date):
    current = start
    while current <= end:
        chunk_end = min(date(current.year, 12, 31), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


async def backfill_ceda(store=None, client=None, commodities=None, states=None,
                        from_date: date = date(2018, 1, 1), to_date: date = None) -> dict:
    store = store or await get_store()
    client = client or CedaClient()
    commodities = commodities or scoped_commodities()
    states = states or BACKFILL_STATES
    to_date = to_date or date.today()
    report = _new_report("ceda")
    report.update({"storage": store.name, "inserted": 0, "updated": 0, "fetched": 0,
                   "chunks": 0, "rejected": {}, "commodities": commodities, "states": states})
    rejected = Counter()

    try:
        ceda_commodities = await asyncio.to_thread(client.commodities)
        geographies = await asyncio.to_thread(client.geographies)
    except SourceError as exc:
        report["errors"].append(str(exc))
        report["status"] = "failed"
        return await _finish(store, report)

    commodity_ids = {}
    for item in ceda_commodities:
        cid = resolve_commodity(item.get("commodity_name"))
        if cid and cid not in commodity_ids:
            commodity_ids[cid] = (item.get("commodity_id"), item.get("commodity_name"))
    state_ids, district_names = {}, {}
    for geo in geographies:
        if geo.get("census_state_name"):
            state_ids[" ".join(geo["census_state_name"].lower().split())] = geo.get("census_state_id")
        if geo.get("census_district_id") is not None:
            district_names[geo["census_district_id"]] = geo.get("census_district_name") or ""

    for cid in commodities:
        if cid not in commodity_ids:
            report["warnings"].append(f"CEDA has no commodity matching '{cid}'")
            continue
        ceda_cid, ceda_name = commodity_ids[cid]
        for state in states:
            state_id = state_ids.get(state.lower())
            if state_id is None:
                report["warnings"].append(f"CEDA has no state matching '{state}'")
                continue
            try:
                markets = await asyncio.to_thread(client.markets, ceda_cid, state_id)
            except SourceError as exc:
                report["errors"].append(f"{cid}/{state} markets: {exc}")
                continue
            market_names = {m.get("market_id"): m.get("market_name") for m in markets}

            for chunk_start, chunk_end in _year_chunks(from_date, to_date):
                try:
                    records = await asyncio.to_thread(
                        client.prices, ceda_cid, state_id, chunk_start.isoformat(), chunk_end.isoformat())
                except SourceError as exc:
                    report["errors"].append(f"{cid}/{state} {chunk_start.year}: {exc}")
                    continue
                report["chunks"] += 1
                report["fetched"] += len(records)
                rows = {}
                for rec in records:
                    row, problem = build_price_row(
                        date=rec.get("date"), state=state,
                        district=district_names.get(rec.get("census_district_id"), ""),
                        market=market_names.get(rec.get("market_id"), f"market-{rec.get('market_id')}"),
                        commodity_raw=ceda_name, variety=None, grade=None,
                        min_price=rec.get("min_price"), max_price=rec.get("max_price"),
                        modal_price=rec.get("modal_price"), source="ceda", raw=rec,
                    )
                    if problem:
                        rejected[problem] += 1
                    else:
                        rows[row["_id"]] = row
                result = await store.upsert_prices(list(rows.values()))
                report["inserted"] += result["inserted"]
                report["updated"] += result["updated"]

    report["rejected"] = dict(rejected)
    if report["errors"] and report["fetched"] == 0:
        report["status"] = "failed"
    elif report["errors"]:
        report["status"] = "partial"
    else:
        report["status"] = "warning" if report["warnings"] else "ok"
    return await _finish(store, report)


async def probe_ceda_arrivals(client=None, commodity: str = "onion", state: str = "Maharashtra") -> dict:
    """
    Settle the plan's biggest data risk: does CEDA expose market-level arrivals?
    Tries candidate `indicator` values on /agmarknet/markets and reports which work.
    """
    client = client or CedaClient()
    ceda_commodities = await asyncio.to_thread(client.commodities)
    geographies = await asyncio.to_thread(client.geographies)
    commodity_id = next((c.get("commodity_id") for c in ceda_commodities
                         if resolve_commodity(c.get("commodity_name")) == commodity), None)
    state_id = next((g.get("census_state_id") for g in geographies
                     if (g.get("census_state_name") or "").lower() == state.lower()), None)
    results = {}
    for indicator in ("price", "quantity", "arrival", "arrivals", "volume"):
        try:
            data = await asyncio.to_thread(client._call, "POST", "/agmarknet/markets", {
                "commodity_id": commodity_id, "state_id": state_id, "indicator": indicator,
            })
            results[indicator] = {"ok": True, "markets": len(data)}
        except SourceError as exc:
            results[indicator] = {"ok": False, "error": str(exc)[:200]}
    return {"commodity_id": commodity_id, "state_id": state_id, "indicators": results}
