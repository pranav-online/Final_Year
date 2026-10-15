"""
Phase 2: descriptive signals, alerts and the broker overview.

compute_signals  -> latest-week signals per commodity at market, state and national level
generate_alerts  -> glut / shortage / price spike / crash / arrival surge / listing alerts,
                    de-duplicated for 24 hours
overview         -> rows for the broker pressure heatmap, plus ALIP listing supply
"""
import logging
import statistics
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from services.mandi import signals as sig
from services.mandi.config import COMMODITIES, resolve_commodity, scoped_commodities, state_key
from services.mandi.normalize import utc_now_iso
from services.mandi.store import get_store

log = logging.getLogger("alip.mandi.insights")

HISTORY_WEEKS = 3 * 52 + 14   # 3 seasonal years plus the 13-week momentum window
STALE_WEEKS = 2
ALERT_WINDOW_HOURS = 24
OPPORTUNITY_QUADRANTS = {"supply_shortage", "strong_demand"}


def _week_of(day: date) -> str:
    return (day - timedelta(days=day.weekday())).isoformat()


def _median_by_week(points: list[dict]) -> list[dict]:
    weeks = defaultdict(list)
    for p in points:
        weeks[p["week_start"]].append(p["price"])
    return [{"week_start": w, "price": statistics.median(v), "markets": len(v)} for w, v in sorted(weeks.items())]


def weekly_arrivals(daily: list[dict]) -> list[dict]:
    """National daily arrivals -> mean tonnes per reported day for each week."""
    weeks = defaultdict(list)
    for a in daily:
        if a.get("arrival_tonnes") is not None:
            weeks[_week_of(date.fromisoformat(a["date"]))].append(a["arrival_tonnes"])
    return [{"week_start": w, "tonnes_per_day": statistics.fmean(v), "days": len(v)} for w, v in sorted(weeks.items())]


def _scope_doc(cid, level, scope_key, scope_name, state, series, latest_week, arrivals, computed_at):
    week = series[-1]["week_start"]
    doc = sig.week_signals(cid, series, week, arrivals)
    doc.update({
        "_id": f"{cid}|{level}|{scope_key}",
        "commodity": cid,
        "commodity_name": COMMODITIES[cid]["name"],
        "level": level,
        "scope_key": scope_key,
        "scope_name": scope_name,
        "state": state,
        "markets_reporting": series[-1].get("markets", 1),
        "stale": (date.fromisoformat(latest_week) - date.fromisoformat(week)).days > STALE_WEEKS * 7,
        "arrivals_scope": "national",
        "price_unit": "Rs/quintal",
        "computed_at": computed_at,
    })
    return doc


async def compute_signals(store=None, commodities=None, today: date = None) -> dict:
    store = store or await get_store()
    today = today or date.today()
    date_from = (today - timedelta(weeks=HISTORY_WEEKS)).isoformat()
    computed_at = utc_now_iso()
    summary = {}

    for cid in commodities or scoped_commodities():
        market_weeks = await store.weekly_market_medians(cid, date_from)
        if not market_weeks:
            await store.replace_signals(cid, [])
            summary[cid] = {"scopes": 0}
            continue
        arrivals = weekly_arrivals(await store.find_arrivals(cid, date_from=date_from))

        by_market, state_points, names = defaultdict(list), defaultdict(list), {}
        for p in market_weeks:
            by_market[p["market_key"]].append({"week_start": p["week_start"], "price": p["price"]})
            state_points[state_key(p["state"])].append(p)
            names[p["market_key"]] = p
        national = _median_by_week(market_weeks)
        latest_week = national[-1]["week_start"]

        docs = [_scope_doc(cid, "national", "india", "India", None, national, latest_week, arrivals, computed_at)]
        for skey, points in state_points.items():
            display = points[-1]["state"]
            docs.append(_scope_doc(cid, "state", skey, display, display,
                                   _median_by_week(points), latest_week, arrivals, computed_at))
        for market_key, series in by_market.items():
            market_name = market_key.split("|")[-1].title()
            docs.append(_scope_doc(cid, "market", market_key, market_name, names[market_key]["state"],
                                   series, latest_week, arrivals, computed_at))

        await store.replace_signals(cid, docs)
        summary[cid] = {"scopes": len(docs), "latest_week": latest_week,
                        "weeks_of_history": docs[0]["weeks_of_history"]}
    log.info("signals computed: %s", {c: s.get("scopes") for c, s in summary.items()})
    return summary


# ─── Alerts ────────────────────────────────────────────────
def _alert(kind, cid, scope, severity, title, message, **extra) -> dict:
    return {
        "_id": uuid.uuid4().hex,
        "dedupe_key": f"{kind}|{cid}|{scope['scope_key'] if scope else 'india'}",
        "type": kind,
        "commodity": cid,
        "level": scope["level"] if scope else "national",
        "scope_key": scope["scope_key"] if scope else "india",
        "scope_name": scope["scope_name"] if scope else "India",
        "severity": severity,
        "title": title,
        "message": message,
        "created_at": utc_now_iso(),
        **extra,
    }


def signal_alerts(doc: dict) -> list[dict]:
    """Alerts implied by one scope's signals (national and state levels only)."""
    if doc["level"] not in {"national", "state"} or doc.get("stale"):
        return []
    cid, name, where = doc["commodity"], doc["commodity_name"], doc["scope_name"]
    common = {"week_start": doc["week_start"], "urgency": doc.get("urgency"),
              "reasons": doc.get("urgency_reasons")}
    alerts = []
    if doc["quadrant"] == "glut":
        alerts.append(_alert("glut", cid, doc, "high", f"Glut risk - {name}, {where}",
                             f"Arrivals {doc['arrivals_ratio']:.2f}x normal and price "
                             f"{doc['momentum_4w']:+.0%} over 4 weeks.", **common))
    elif doc["quadrant"] == "supply_shortage":
        alerts.append(_alert("supply_shortage", cid, doc, "medium", f"Supply shortage - {name}, {where}",
                             f"Arrivals {doc['arrivals_ratio']:.2f}x normal while price is "
                             f"{doc['momentum_4w']:+.0%} over 4 weeks.", **common))
    z = doc.get("price_z")
    if z is not None and z >= sig.Z_ALERT:
        alerts.append(_alert("price_spike", cid, doc, "medium", f"Price spike - {name}, {where}",
                             f"This week's price move is {z:.1f} robust SDs above normal "
                             f"(modal Rs {doc['price']:.0f}/quintal).", **common))
    elif z is not None and z <= -sig.Z_ALERT:
        alerts.append(_alert("price_crash", cid, doc, "high", f"Price crash - {name}, {where}",
                             f"This week's price move is {abs(z):.1f} robust SDs below normal "
                             f"(modal Rs {doc['price']:.0f}/quintal).", **common))
    return alerts


def arrival_surge_alert(cid: str, daily: list[dict]):
    if not daily:
        return None
    latest = max(a["date"] for a in daily)
    ratio = sig.daily_arrival_surge(daily, latest)
    if ratio is None or ratio < sig.SURGE_RATIO:
        return None
    tonnes = next(a["arrival_tonnes"] for a in daily if a["date"] == latest)
    return _alert("arrival_surge", cid, None, "high", f"Arrival surge - {COMMODITIES[cid]['name']}, India",
                  f"{tonnes:,.0f} t arrived on {latest}: {ratio:.1f}x the 28-day median. "
                  f"Expect price pressure in the next few days.", date=latest, ratio=round(ratio, 2))


async def load_available_listings() -> list[dict]:
    """Farmer listings (MongoDB, else the local JSON store) without importing the ML-heavy market service."""
    from pymongo.errors import PyMongoError

    from config.database import market_collection
    from services import local_market_store

    try:
        return [doc async for doc in market_collection.find({"status": "available"})]
    except PyMongoError:
        return await local_market_store.find_listings({"status": "available"})


def listing_state(listing: dict):
    from services.region_service import STATE_TO_REFERENCE_REGION, get_region_info

    location = (listing.get("location") or "").strip().lower()
    info = get_region_info(location)
    if info:
        return info["state"]
    if location in STATE_TO_REFERENCE_REGION:
        return location.title()
    return None


def _listing_created(listing: dict):
    created = listing.get("created_at")
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created


async def generate_alerts(store=None, listings=None) -> dict:
    store = store or await get_store()
    created = defaultdict(int)
    candidates = []

    state_signals = {}
    for doc in await store.find_signals():
        candidates.extend(signal_alerts(doc))
        if doc["level"] == "state":
            state_signals[(doc["commodity"], doc["scope_key"])] = doc
    for cid in scoped_commodities():
        surge = arrival_surge_alert(cid, await store.find_arrivals(cid))
        if surge:
            candidates.append(surge)

    # ALIP's own forward-supply signal: fresh listings where the market looks tight.
    listings = listings if listings is not None else await load_available_listings()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_WINDOW_HOURS)
    for listing in listings:
        cid, state = resolve_commodity(listing.get("crop_name")), listing_state(listing)
        when = _listing_created(listing)
        if not cid or not state or when is None or when < cutoff:
            continue
        doc = state_signals.get((cid, state_key(state)))
        tight = doc and (doc["quadrant"] in OPPORTUNITY_QUADRANTS or (doc.get("price_vs_norm") or 0) > 0.10)
        if tight:
            alert = _alert("listing_opportunity", cid, doc, "medium",
                           f"Buying opportunity - {COMMODITIES[cid]['name']}, {listing.get('location', '').title()}",
                           f"{listing.get('quantity_kg', 0):,.0f} kg listed at Rs {listing.get('price_per_kg')}/kg "
                           f"while {state} looks tight ({doc['quadrant'].replace('_', ' ')}).",
                           listing_id=str(listing.get("_id")))
            alert["dedupe_key"] = f"listing_opportunity|{listing.get('_id')}"
            candidates.append(alert)

    for alert in candidates:
        if await store.insert_alert_if_new(alert, ALERT_WINDOW_HOURS):
            created[alert["type"]] += 1
    log.info("alerts: %d candidates, %d new %s", len(candidates), sum(created.values()), dict(created))
    return {"candidates": len(candidates), "created": dict(created)}


async def refresh(store=None) -> dict:
    """Recompute signals, then alerts (run after every ingest)."""
    store = store or await get_store()
    return {"signals": await compute_signals(store), "alerts": await generate_alerts(store)}


# ─── Broker overview ───────────────────────────────────────
def listing_supply(listings: list[dict]) -> dict:
    supply = defaultdict(lambda: {"quantity_kg": 0.0, "listings": 0, "states": set()})
    for listing in listings:
        cid = resolve_commodity(listing.get("crop_name"))
        if not cid:
            continue
        entry = supply[cid]
        entry["quantity_kg"] += float(listing.get("quantity_kg") or 0)
        entry["listings"] += 1
        state = listing_state(listing)
        if state:
            entry["states"].add(state)
    return {cid: {**v, "states": sorted(v["states"])} for cid, v in supply.items()}


async def overview(store=None, level: str = "state", state: str = None, commodities=None) -> dict:
    store = store or await get_store()
    wanted = set(commodities or scoped_commodities())
    rows = [
        d for d in await store.find_signals(level=level)
        if d["commodity"] in wanted and (not state or state_key(d.get("state")) == state_key(state))
    ]
    rows.sort(key=lambda d: (-(d.get("urgency") or 0), d["commodity"], d["scope_name"]))
    for row in rows:
        row.pop("_id", None)

    last_pull = next(iter(await store.recent_ingest_reports("datagov", 1)), None)
    weeks = max((r["weeks_of_history"] for r in rows), default=0)
    return {
        "level": level,
        "rows": rows,
        "listing_supply": listing_supply(await load_available_listings()),
        "data_as_of": max((r["week_start"] for r in rows), default=None),
        "last_price_pull_at": last_pull.get("finished_at") if last_pull else None,
        "max_weeks_of_history": weeks,
        "history_note": (
            None if weeks >= 13 else
            f"Only {weeks} week(s) of price history so far: momentum needs 5+ weeks, volatility 6+, "
            f"robust z 9+, and seasonal norms a year. Signals fill in as daily pulls accumulate "
            f"or after the CEDA backfill."
        ),
        "thresholds": {
            "arrivals_high": sig.ARRIVALS_HIGH, "arrivals_low": sig.ARRIVALS_LOW,
            "price_rising": sig.PRICE_RISING, "z_alert": sig.Z_ALERT, "surge_ratio": sig.SURGE_RATIO,
        },
        "is_demo": False,
        "generated_at": utc_now_iso(),
    }
