"""
Freight and haul economics, following the master report section 2.6:

    Small truck   3 t   Rs 25/km      ROI = (agreed price - source cost) x Q_kg
    Medium truck 10 t   Rs 35/km            ---------------------------------
    Large truck  20 t   Rs 50/km               distance x rate_truck

    ROI >= 1.5 "Good", 1.0-1.5 "Acceptable", < 1.0 "Loss-Making".

Two documented additions: loads above one truck's capacity need several trucks
(cost multiplies), and road distance is estimated as straight-line distance x a
circuity factor (default 1.25, editable per broker) because only city
coordinates are known.
"""
import math

TRUCKS = {
    "small": {"capacity_kg": 3000, "rate_per_km": 25.0},
    "medium": {"capacity_kg": 10000, "rate_per_km": 35.0},
    "large": {"capacity_kg": 20000, "rate_per_km": 50.0},
}
DEFAULT_ROAD_FACTOR = 1.25
MAX_HAUL_KM = 500  # report section 2.4: "all reachable destinations (within 500 km)"


def road_distance_km(straight_km: float, road_factor: float = DEFAULT_ROAD_FACTOR) -> float:
    return round(straight_km * road_factor, 1)


def plan_transport(distance_km: float, quantity_kg: float, truck: str = None, rates: dict = None) -> dict:
    """
    Cheapest way to move `quantity_kg` over `distance_km`. If `truck` is given it is
    used; otherwise every truck type is costed and the cheapest total wins.
    `rates` overrides Rs/km per truck type (broker settings).
    """
    rates = rates or {}
    options = []
    for name in ([truck] if truck else TRUCKS):
        spec = TRUCKS[name]
        rate = float(rates.get(name, spec["rate_per_km"]))
        count = max(1, math.ceil(quantity_kg / spec["capacity_kg"]))
        options.append({
            "truck_type": name,
            "trucks": count,
            "capacity_kg": spec["capacity_kg"],
            "rate_per_km": rate,
            "distance_km": round(distance_km, 1),
            "cost": round(count * distance_km * rate, 2),
        })
    best = min(options, key=lambda o: (o["cost"], o["trucks"]))
    best["cost_per_100kg"] = round(best["cost"] / quantity_kg * 100, 2) if quantity_kg else None
    best["utilisation"] = round(quantity_kg / (best["trucks"] * best["capacity_kg"]), 3)
    return best


def roi(agreed_price_per_kg: float, source_cost_per_kg: float, quantity_kg: float,
        transport_cost: float, commission_pct: float = 0.0):
    """
    Report formula. `commission_pct` (of sale value, default 0 so the result matches
    the report exactly) lets brokers deduct arhtiya commission and mandi fees.
    """
    if not transport_cost:
        return None
    sale = agreed_price_per_kg * quantity_kg
    margin = (agreed_price_per_kg - source_cost_per_kg) * quantity_kg - sale * commission_pct / 100
    return round(margin / transport_cost, 2)


def roi_band(value):
    if value is None:
        return None
    if value >= 1.5:
        return "Good"
    if value >= 1.0:
        return "Acceptable"
    return "Loss-Making"


def transport_efficiency_score(cost_per_100kg: float) -> float:
    """Report section 2.4: Score = max(0, 100 - Cost_100kg / 5)."""
    return round(max(0.0, 100 - cost_per_100kg / 5), 1)
