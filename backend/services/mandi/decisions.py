"""
Phase 4: broker decisions built on the mandi signals and forecasts.

best_markets  - destinations within 500 km ranked by expected net margin after
                freight (report section 2.6 ROI) with the report's 7-factor
                composite (section 2.4) computed from the factors that have data
break_even    - first forecast week at which shipping stops beating selling at source
match_listing - score a farmer listing for a broker (margin, distance, pressure, truck fill)
analysis      - the report's "full analysis" for one commodity at one location

Prices from mandi data are Rs/quintal; listing prices are Rs/kg (1 quintal = 100 kg).
"""
from datetime import datetime, timezone

from services.mandi import freight
from services.mandi.config import COMMODITIES, resolve_commodity, state_key
from services.region_service import REGIONS, get_coordinates, haversine_distance

QUINTAL_KG = 100

# Report section 2.4 weights. Reliability, storage and weather need data the app
# does not have yet (broker ratings, facility registry, route weather); they are
# reported as inactive and the remaining weights are rescaled.
FACTOR_WEIGHTS = {
    "demand_gap": 0.20, "reliability": 0.20, "price_advantage": 0.15,
    "transport_efficiency": 0.15, "saturation": 0.10, "storage": 0.10, "weather": 0.10,
}
INACTIVE_FACTORS = {
    "reliability": "no broker ratings recorded yet",
    "storage": "no storage-facility data for destinations",
    "weather": "route weather not connected",
}
# Destination pressure -> demand-gap score (proxy for deficit_dest / oversupply_source).
DEMAND_GAP_SCORE = {"supply_shortage": 100, "strong_demand": 75, "balanced": 50, "weak_demand": 25, "glut": 0}
SATURATION_LIMIT = 1.2  # report: score drops to 0 once incoming fills >120% of the gap
THIN_SAMPLE_MARKETS = 3  # a price from fewer reporting markets is flagged as thin

DEFAULT_SETTINGS = {
    "home_region": None,
    "watch_commodities": [],     # empty = every commodity
    "radius_km": 300,
    "truck_type": None,          # None = cheapest that fits
    "truck_rates": {},           # Rs/km overrides per truck type
    "commission_pct": 0.0,       # of sale value; 0 keeps ROI identical to the report formula
    "road_factor": freight.DEFAULT_ROAD_FACTOR,
}


class DecisionError(ValueError):
    pass


def settings_with_defaults(doc: dict = None) -> dict:
    return {**DEFAULT_SETTINGS, **{k: v for k, v in (doc or {}).items() if v is not None}}


def resolve_place(name: str) -> dict:
    """A city from the region table, or a state (mapped to its reference city)."""
    coords = get_coordinates(name or "")
    if coords is None:
        raise DecisionError(f"Unknown location '{name}'. Use a city such as Guntur or a state name.")
    key = (name or "").strip().lower()
    city = next((c for c in REGIONS if c.lower() == key), None)
    if city is None:  # a state name: use its reference city
        city = next(c for c, d in REGIONS.items() if (d["lat"], d["lng"]) == coords)
    return {"city": city, "state": REGIONS[city]["state"], "lat": coords[0], "lng": coords[1]}


def road_km(a: dict, b: dict, road_factor: float) -> float:
    return freight.road_distance_km(haversine_distance(a["lat"], a["lng"], b["lat"], b["lng"]), road_factor)


# ─── Prices and forecasts for a place ──────────────────────
async def place_price(store, commodity: str, place: dict) -> dict:
    """
    Latest weekly price near a city: the median of markets in the city's own
    district when any report, otherwise the state median. Includes the state
    forecast when one is served.
    """
    skey = state_key(place["state"])
    district = place["city"].lower()
    markets = [
        d for d in await store.find_scoped("signals", commodity, "market")
        if state_key(d.get("state")) == skey and d["scope_key"].split("|")[1] == district
        and d.get("price") and not d.get("stale")
    ]
    state_doc = next(iter(await store.find_scoped("signals", commodity, "state", skey)), None)
    if markets:
        prices = sorted(d["price"] for d in markets)
        price, basis = prices[len(prices) // 2], f"median of {len(markets)} {place['city']} district market(s)"
        week, sample = max(d["week_start"] for d in markets), len(markets)
    elif state_doc and state_doc.get("price"):
        price, basis, week = state_doc["price"], f"{place['state']} state median", state_doc["week_start"]
        sample = state_doc.get("markets_reporting") or 1
    else:
        return {"available": False, "reason": f"no recent {commodity} prices for {place['city']} or {place['state']}"}

    forecast_doc = next(iter(await store.find_scoped("forecasts", commodity, "state", skey)), None)
    horizons = forecast_doc["horizons"] if forecast_doc and forecast_doc.get("confidence") != "insufficient" else []
    return {
        "available": True, "price_per_quintal": price, "basis": basis, "week_start": week,
        "markets_in_sample": sample, "thin_sample": sample < THIN_SAMPLE_MARKETS,
        "forecast": horizons, "forecast_confidence": forecast_doc["confidence"] if forecast_doc else None,
        "quadrant": state_doc.get("quadrant") if state_doc else None,
        "urgency": state_doc.get("urgency") if state_doc else None,
    }


def _h(horizons: list, h: int):
    return next((x for x in horizons or [] if x["h_weeks"] == h), None)


# ─── Break-even ────────────────────────────────────────────
def break_even(source_forecast: list, dest_forecast: list, freight_per_kg: float) -> dict:
    """
    First forecast week (1, 2 or 4) at which destination P50 minus freight drops
    below source P50, i.e. after which shipping no longer beats selling locally.
    """
    if not source_forecast or not dest_forecast:
        return {"week": None, "reason": "needs served forecasts at both source and destination"}
    for h in (1, 2, 4):
        src, dst = _h(source_forecast, h), _h(dest_forecast, h)
        if src and dst and dst["p50"] / QUINTAL_KG - freight_per_kg < src["p50"] / QUINTAL_KG:
            return {"week": h, "target_week": dst["target_week"],
                    "reason": f"by week {h} the destination no longer pays for the freight"}
    return {"week": None, "reason": "shipping stays ahead for the whole 4-week forecast"}


# ─── Best markets ──────────────────────────────────────────
def _composite(factors: dict) -> dict:
    active = {k: v for k, v in factors.items() if v is not None}
    weight = sum(FACTOR_WEIGHTS[k] for k in active)
    score = sum(FACTOR_WEIGHTS[k] * v for k, v in active.items()) / weight if weight else None
    return {
        "score": round(score, 1) if score is not None else None,
        "factors": {k: (round(v, 1) if v is not None else None) for k, v in factors.items()},
        "active_weight": round(weight, 2),
    }


async def best_markets(store, commodity: str, source: str, quantity_kg: float,
                       source_price_per_kg: float = None, settings: dict = None,
                       limit: int = 5, sort: str = "net") -> dict:
    settings = settings_with_defaults(settings)
    if quantity_kg <= 0:
        raise DecisionError("quantity_kg must be positive")
    src = resolve_place(source)
    src_price = await place_price(store, commodity, src)
    if source_price_per_kg is None:
        if not src_price["available"]:
            raise DecisionError(f"No source price: {src_price['reason']}. Pass source_price_per_kg.")
        source_price_per_kg = src_price["price_per_quintal"] / QUINTAL_KG
        source_basis = src_price["basis"]
    else:
        source_basis = "price given (listing or agreed)"

    in_transit = await store.find_shipments(status="in_transit", commodity=commodity)
    candidates, skipped = [], []
    for city, data in REGIONS.items():
        if city == src["city"]:
            continue
        dest = {"city": city, "state": data["state"], "lat": data["lat"], "lng": data["lng"]}
        distance = road_km(src, dest, settings["road_factor"])
        if distance > freight.MAX_HAUL_KM:
            continue
        price = await place_price(store, commodity, dest)
        if not price["available"]:
            skipped.append({"city": city, "reason": price["reason"]})
            continue

        transport = freight.plan_transport(distance, quantity_kg, settings["truck_type"], settings["truck_rates"])
        h1 = _h(price["forecast"], 1)
        expected = (h1["p50"] if h1 else price["price_per_quintal"]) / QUINTAL_KG
        downside = h1["p10"] / QUINTAL_KG if h1 else None
        commission = expected * settings["commission_pct"] / 100
        net_per_kg = expected - commission - transport["cost"] / quantity_kg
        value = freight.roi(expected, source_price_per_kg, quantity_kg, transport["cost"], settings["commission_pct"])
        value_p10 = (freight.roi(downside, source_price_per_kg, quantity_kg, transport["cost"], settings["commission_pct"])
                     if downside is not None else None)

        incoming = sum(s["quantity_kg"] for s in in_transit if s["destination_key"] == city.lower())
        candidates.append({
            "destination": city, "state": data["state"], "distance_km": distance,
            "price_basis": price["basis"], "price_week": price["week_start"],
            "markets_in_sample": price["markets_in_sample"], "thin_sample": price["thin_sample"],
            "uses_forecast": bool(h1), "forecast_confidence": price["forecast_confidence"],
            "expected_price_per_kg": round(expected, 2),
            "downside_price_per_kg": round(downside, 2) if downside is not None else None,
            "source_price_per_kg": round(source_price_per_kg, 2),
            "transport": transport,
            "net_price_per_kg": round(net_per_kg, 2),
            "net_price_per_quintal": round(net_per_kg * QUINTAL_KG, 2),
            "expected_margin": round((net_per_kg - source_price_per_kg) * quantity_kg, 2),
            "roi": value, "roi_band": freight.roi_band(value),
            "roi_p10": value_p10, "roi_p10_band": freight.roi_band(value_p10),
            "destination_quadrant": price["quadrant"],
            "in_transit_kg": incoming,
            "_forecast": price["forecast"],
        })

    # 7-factor composite from the factors that have data.
    deltas = [c["expected_price_per_kg"] - c["source_price_per_kg"] for c in candidates]
    lo, hi = (min(deltas), max(deltas)) if deltas else (0, 0)
    for c, delta in zip(candidates, deltas):
        ratio = c["in_transit_kg"] / quantity_kg  # proxy: destination gap ~ this shipment's size
        c["composite"] = _composite({
            "demand_gap": DEMAND_GAP_SCORE.get(c["destination_quadrant"]),
            "reliability": None,
            "price_advantage": 50.0 if hi == lo else 100 * (delta - lo) / (hi - lo),
            "transport_efficiency": freight.transport_efficiency_score(c["transport"]["cost_per_100kg"]),
            "saturation": 0.0 if ratio > SATURATION_LIMIT else 100 * (1 - ratio / SATURATION_LIMIT),
            "storage": None,
            "weather": None,
        })

    key = (lambda c: -(c["composite"]["score"] or 0)) if sort == "composite" else (lambda c: -c["expected_margin"])
    ranked = sorted(candidates, key=key)[:limit]
    for c in ranked:
        c["break_even"] = break_even(src_price.get("forecast"), c.pop("_forecast"),
                                     c["transport"]["cost"] / quantity_kg)
    return {
        "commodity": commodity, "source": src["city"], "source_state": src["state"],
        "quantity_kg": quantity_kg, "source_price_per_kg": round(source_price_per_kg, 2),
        "source_price_basis": source_basis, "sort": sort, "settings_used": settings,
        "destinations": ranked, "candidates_considered": len(candidates),
        "skipped_no_price": skipped,
        "inactive_factors": INACTIVE_FACTORS,
        "notes": [
            "Distances are straight-line x road factor, not routed road distance.",
            "Without a served forecast the expected price is the latest observed weekly price and no downside is shown.",
            "Demand gap uses the destination's inferred pressure quadrant as a proxy for its deficit.",
            f"thin_sample marks prices from fewer than {THIN_SAMPLE_MARKETS} reporting markets; confirm before acting.",
        ],
    }


# ─── Listing matching ──────────────────────────────────────
MATCH_WEIGHTS = {"margin": 0.35, "distance": 0.25, "pressure": 0.20, "quantity": 0.20}


def listing_commodity(listing: dict):
    return listing.get("commodity_id") or resolve_commodity(listing.get("crop_name"))


async def match_listing(store, listing: dict, settings: dict) -> dict:
    """Score one listing for one broker, or explain why it does not match."""
    settings = settings_with_defaults(settings)
    cid = listing_commodity(listing)
    watch = [resolve_commodity(c) for c in settings["watch_commodities"]]
    if cid is None:
        return {"match": False, "reason": "listing crop is not a tracked commodity"}
    if watch and cid not in watch:
        return {"match": False, "reason": "commodity not on the watchlist"}
    if not settings["home_region"]:
        return {"match": False, "reason": "broker has no home region set"}
    try:
        home, origin = resolve_place(settings["home_region"]), resolve_place(listing.get("location"))
    except DecisionError as exc:
        return {"match": False, "reason": str(exc)}

    distance = road_km(origin, home, settings["road_factor"])
    if distance > settings["radius_km"]:
        return {"match": False, "reason": f"{distance} km away (radius {settings['radius_km']} km)"}

    qty = float(listing.get("quantity_kg") or 0)
    price = float(listing.get("price_per_kg") or 0)
    transport = freight.plan_transport(distance, qty, settings["truck_type"], settings["truck_rates"]) if qty else None
    home_price = await place_price(store, cid, home)
    origin_signal = next(iter(await store.find_scoped("signals", cid, "state", state_key(origin["state"]))), None)

    parts, margin_per_kg = {}, None
    if home_price["available"] and price and transport:
        margin_per_kg = home_price["price_per_quintal"] / QUINTAL_KG - price - transport["cost"] / qty
        parts["margin"] = min(max(margin_per_kg / price / 0.30, 0.0), 1.0)  # 30% margin -> full marks
    parts["distance"] = 1 - distance / settings["radius_km"] if settings["radius_km"] else 0.0
    if origin_signal and origin_signal.get("urgency"):
        parts["pressure"] = origin_signal["urgency"] / 10  # an urgent seller is a buying opportunity
    if transport:
        parts["quantity"] = min(1.0, transport["utilisation"])

    weight = sum(MATCH_WEIGHTS[k] for k in parts)
    score = 100 * sum(MATCH_WEIGHTS[k] * v for k, v in parts.items()) / weight
    return {
        "match": True, "score": round(score, 1), "commodity": cid,
        "distance_km": distance, "components": {k: round(v, 3) for k, v in parts.items()},
        "expected_margin_per_kg": round(margin_per_kg, 2) if margin_per_kg is not None else None,
        "home_price_basis": home_price.get("basis"), "transport": transport,
    }


async def matches_for_broker(store, settings: dict, listings: list[dict], commodity: str = None) -> list[dict]:
    results = []
    for listing in listings:
        if commodity and listing_commodity(listing) != commodity:
            continue
        m = await match_listing(store, listing, settings)
        if m["match"]:
            results.append({"listing": _public_listing(listing), **m})
    return sorted(results, key=lambda r: -r["score"])


def _public_listing(listing: dict) -> dict:
    out = {k: v for k, v in listing.items() if k not in {"_id", "contact"}}
    out["id"] = str(listing.get("_id"))
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    return out


async def notify_brokers_of_listing(store, listing: dict) -> int:
    """Create a broker-specific listing_match alert for every broker this listing matches."""
    from services.mandi.normalize import utc_now_iso
    import uuid

    created = 0
    for settings in await store.all_broker_settings():
        m = await match_listing(store, listing, settings)
        if not m["match"]:
            continue
        cid = m["commodity"]
        alert = {
            "_id": uuid.uuid4().hex,
            "dedupe_key": f"listing_match|{listing.get('_id')}|{settings['broker_id']}",
            "type": "listing_match", "commodity": cid, "level": "listing",
            "scope_key": str(listing.get("_id")), "scope_name": (listing.get("location") or "").title(),
            "severity": "medium", "broker_id": settings["broker_id"],
            "title": f"New {COMMODITIES[cid]['name']} listing near you - {(listing.get('location') or '').title()}",
            "message": (f"{float(listing.get('quantity_kg') or 0):,.0f} kg at Rs {listing.get('price_per_kg')}/kg, "
                        f"{m['distance_km']} km away. Match score {m['score']}/100."),
            "listing_id": str(listing.get("_id")), "score": m["score"],
            "created_at": utc_now_iso(),
        }
        if await store.insert_alert_if_new(alert, window_hours=24 * 30):
            created += 1
    return created


# ─── Action card ───────────────────────────────────────────
ACTION_BAND = 0.02  # forecast moves within +-2% read as "no clear direction"
ACTION_WINDOW = {1: "1-2 days", 2: "5 days", 3: "14 days"}  # report section 2.5 tiers


def _rs(value: float) -> str:
    return f"Rs {value:,.0f}"


def action_card(commodity: str, signal: dict = None, forecast_doc: dict = None) -> dict:
    """
    SELL / HOLD / WATCH with a plain reason and a confidence label.
    Forecast-based when a forecast is served, else from descriptive signals (low
    confidence), else "not enough signal".
    """
    tier = COMMODITIES[commodity]["tier"]
    card = {"action_window": ACTION_WINDOW[tier], "tier": tier,
            "urgency": (signal or {}).get("urgency"), "range_text": None}
    h1 = _h((forecast_doc or {}).get("horizons"), 1)
    if forecast_doc and forecast_doc.get("confidence") not in (None, "insufficient") and h1:
        base = forecast_doc["origin_price"]
        change, low, high = h1["p50"] / base - 1, h1["p10"] / base - 1, h1["p90"] / base - 1
        if change < -ACTION_BAND:
            action, reason = "SELL", f"Price likely to fall next week (median {change:+.0%}, range {low:+.0%} to {high:+.0%})."
        elif change > ACTION_BAND:
            action, reason = "HOLD", f"Price likely to rise next week (median {change:+.0%}, range {low:+.0%} to {high:+.0%})."
        else:
            action, reason = "WATCH", f"Price expected to stay within +-{ACTION_BAND:.0%} next week."
        card.update(action=action, reason=reason, confidence=forecast_doc["confidence"], basis="forecast",
                    range_text=(f"8 in 10 times next week's price lands between {_rs(h1['p10'])} and "
                                f"{_rs(h1['p90'])} per quintal."))
        return card

    quadrant = (signal or {}).get("quadrant")
    if signal and quadrant not in (None, "insufficient_data"):
        reasons = "; ".join(signal.get("urgency_reasons") or []) or quadrant.replace("_", " ")
        if quadrant in {"glut", "weak_demand"} or (signal.get("urgency") or 0) >= 7:
            action, reason = "SELL", f"Market under pressure: {reasons}."
        elif quadrant in {"supply_shortage", "strong_demand"}:
            action, reason = "HOLD", f"Supply is tight ({quadrant.replace('_', ' ')}); prices are firm."
        else:
            action, reason = "WATCH", "Arrivals and prices are close to normal."
        card.update(action=action, reason=reason + " No forecast yet, so this is based on recent signals only.",
                    confidence="low", basis="signals")
        return card

    weeks = (signal or {}).get("weeks_of_history", 0)
    card.update(action="WATCH", confidence="insufficient", basis="none",
                reason=f"Not enough signal yet: {weeks} week(s) of price history for this area.")
    return card


# ─── Full analysis ─────────────────────────────────────────
async def analysis(store, commodity: str, location: str, quantity_kg: float = None,
                   price_per_kg: float = None, settings: dict = None, listings: list[dict] = None) -> dict:
    """Signal card, forecast, top destinations with break-even, matched listings and local listed supply."""
    place = resolve_place(location)
    skey = state_key(place["state"])
    signal = next(iter(await store.find_scoped("signals", commodity, "state", skey)), None)
    national = next(iter(await store.find_scoped("signals", commodity, "national", "india")), None)
    forecast_doc = next(iter(await store.find_scoped("forecasts", commodity, "state", skey)), None)
    for doc in (signal, national, forecast_doc):
        if doc:
            doc.pop("_id", None)

    destinations = None
    if quantity_kg:
        try:
            destinations = await best_markets(store, commodity, location, quantity_kg, price_per_kg, settings)
        except DecisionError as exc:
            destinations = {"error": str(exc)}

    last_pull = next((r for r in await store.recent_ingest_reports("datagov", 10)
                      if r.get("status") in {"ok", "warning"}), None)
    hours = None
    if last_pull and last_pull.get("finished_at"):
        hours = (datetime.now(timezone.utc) - datetime.fromisoformat(last_pull["finished_at"])).total_seconds() / 3600
    freshness = {
        "last_price_pull_at": last_pull.get("finished_at") if last_pull else None,
        "hours_since_pull": round(hours, 1) if hours is not None else None,
        "price_week": (signal or {}).get("week_start"),
        "markets_reporting": (signal or {}).get("markets_reporting"),
        "stale": hours is None or hours > 36,
    }

    listings = listings or []
    local = [l for l in listings if listing_commodity(l) == commodity
             and _same_state(l.get("location"), skey)]
    matched = await matches_for_broker(store, settings, listings, commodity) if settings else []
    return {
        "commodity": commodity, "commodity_name": COMMODITIES[commodity]["name"],
        "tier": COMMODITIES[commodity]["tier"], "location": place["city"], "state": place["state"],
        "action": action_card(commodity, signal, forecast_doc),
        "freshness": freshness,
        "signal": signal, "national_signal": national,
        "forecast": forecast_doc,
        "seasonal_context": {
            "seasonal_index_month": (signal or {}).get("seasonal_index_month"),
            "seasonal_trend": (signal or {}).get("seasonal_trend"),
        },
        "best_markets": destinations,
        "listed_supply_in_state": {
            "listings": len(local),
            "quantity_kg": round(sum(float(l.get("quantity_kg") or 0) for l in local), 2),
        },
        "matched_listings": matched[:10],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "is_demo": False,
    }


def _same_state(location: str, skey: str) -> bool:
    try:
        return state_key(resolve_place(location)["state"]) == skey
    except DecisionError:
        return False
