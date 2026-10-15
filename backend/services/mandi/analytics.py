"""Read-side helpers over stored mandi data."""
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from services.mandi import config
from services.mandi.normalize import FLAG_OUTLIER, is_usable

SOURCE_PREFERENCE = {"datagov": 0, "ceda": 1}  # the daily feed wins where sources overlap
STALE_AFTER_HOURS = 36


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (pct in 0-100)."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    position = (len(ordered) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 2)


def _week_start(iso_date: str) -> str:
    day = date.fromisoformat(iso_date)
    return (day - timedelta(days=day.weekday())).isoformat()


def _prefer_daily_feed(rows: list[dict]) -> list[dict]:
    best = {}
    for row in rows:
        key = (row["date"], row["market_key"], row["variety"].lower(), row["grade"].lower())
        if key not in best or SOURCE_PREFERENCE.get(row["source"], 9) < SOURCE_PREFERENCE.get(best[key]["source"], 9):
            best[key] = row
    return list(best.values())


async def weekly_price_history(store, commodity: str, market_key: str = None, state: str = None,
                               weeks: int = 52, today: date = None) -> dict:
    """
    Weekly (Monday-start) aggregates of usable rows: median modal, lowest min,
    highest max, observation and market counts, plus national arrivals when known.
    """
    today = today or date.today()
    date_from = (today - timedelta(weeks=weeks)).isoformat()
    rows = await store.find_prices(commodity, date_from=date_from, date_to=today.isoformat(),
                                   market_key=market_key, state=state)
    usable = _prefer_daily_feed([r for r in rows if is_usable(r)])

    buckets = defaultdict(list)
    for row in usable:
        buckets[_week_start(row["date"])].append(row)

    arrivals = defaultdict(lambda: {"tonnes": 0.0, "days": 0})
    for item in await store.find_arrivals(commodity, date_from=date_from, date_to=today.isoformat()):
        if item.get("arrival_tonnes") is not None:
            bucket = arrivals[_week_start(item["date"])]
            bucket["tonnes"] += item["arrival_tonnes"]
            bucket["days"] += 1

    series = []
    for week in sorted(buckets):
        group = buckets[week]
        modal = [r["modal_price"] for r in group]
        mins = [r["min_price"] for r in group if r.get("min_price") is not None]
        maxs = [r["max_price"] for r in group if r.get("max_price") is not None]
        arrival = arrivals.get(week)
        # Medians and percentiles, not extremes: across hundreds of markets a single
        # bad row (e.g. min Rs 0.01, max Rs 24,000 seen live) would dominate min()/max().
        series.append({
            "week_start": week,
            "modal_price": round(statistics.median(modal), 2),
            "modal_p10": _percentile(modal, 10),
            "modal_p90": _percentile(modal, 90),
            "min_price": round(statistics.median(mins), 2) if mins else None,
            "max_price": round(statistics.median(maxs), 2) if maxs else None,
            "observations": len(group),
            "markets": len({r["market_key"] for r in group}),
            "outlier_observations": sum(FLAG_OUTLIER in (r.get("flags") or []) for r in group),
            "sources": sorted({r["source"] for r in group}),
            "national_arrival_tonnes": round(arrival["tonnes"], 2) if arrival else None,
            "national_arrival_days": arrival["days"] if arrival else 0,
        })

    return {
        "commodity": commodity,
        "market_key": market_key,
        "state": state,
        "weeks_requested": weeks,
        "unit": "Rs/quintal",
        "series": series,
        "data_as_of": max((r["date"] for r in usable), default=None),
        "excluded_invalid_rows": len(rows) - len([r for r in rows if is_usable(r)]),
    }


async def list_markets(store, commodity: str, state: str = None, days: int = 90,
                       today: date = None) -> list[dict]:
    today = today or date.today()
    rows = await store.find_prices(commodity, date_from=(today - timedelta(days=days)).isoformat(),
                                   date_to=today.isoformat(), state=state)
    markets = {}
    for row in sorted((r for r in rows if is_usable(r)), key=lambda r: r["date"]):
        entry = markets.setdefault(row["market_key"], {
            "market_key": row["market_key"], "market": row["market"], "district": row["district"],
            "state": row["state"], "observations": 0, "first_date": row["date"],
        })
        entry["observations"] += 1
        entry["latest_date"] = row["date"]
        entry["latest_modal_price"] = row["modal_price"]
    return sorted(markets.values(), key=lambda m: (-m["observations"], m["market"]))


def _hours_since(iso_timestamp: str):
    if not iso_timestamp:
        return None
    then = datetime.fromisoformat(iso_timestamp)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - then).total_seconds() / 3600, 1)


async def data_health(store, scheduler_info: dict = None) -> dict:
    stats = await store.price_stats()
    sources = {}
    for source in ("datagov", "agmarknet_arrivals", "agmarknet_masters", "ceda"):
        reports = await store.recent_ingest_reports(source, 20)
        last = reports[0] if reports else None
        last_ok = next((r for r in reports if r.get("status") in {"ok", "warning"}), None)
        sources[source] = {
            "last_run": _summarise_report(last),
            "last_success_at": last_ok.get("finished_at") if last_ok else None,
            "hours_since_success": _hours_since(last_ok.get("finished_at")) if last_ok else None,
        }

    latest = max((c["latest_date"] for c in stats["by_commodity"].values() if c.get("latest_date")), default=None)
    stale_commodities = []
    if latest:
        cutoff = (date.fromisoformat(latest) - timedelta(days=3)).isoformat()
        stale_commodities = sorted(c for c, s in stats["by_commodity"].items() if s["latest_date"] < cutoff)

    hours = sources["datagov"]["hours_since_success"]
    return {
        "storage": store.name,
        "status": "ok" if hours is not None and hours <= STALE_AFTER_HOURS else "stale",
        "prices": stats,
        "duplicate_groups": await store.duplicate_groups(),
        "sources": sources,
        "stale_commodities": stale_commodities,
        "data_as_of": latest,
        "config": {
            "datagov_sample_key": config.using_sample_key(),
            "datagov_page_size": config.datagov_page_size(),
            "ceda_key_configured": bool(config.ceda_api_key()),
            "commodities": config.scoped_commodities(),
        },
        "scheduler": scheduler_info or {"enabled": False},
    }


def _summarise_report(report):
    if not report:
        return None
    keys = ("run_id", "status", "started_at", "finished_at", "total_reported", "fetched", "stored",
            "inserted", "updated", "complete", "unmapped_rate", "outliers_flagged", "rows",
            "errors", "warnings", "dates")
    return {k: report[k] for k in keys if k in report}
