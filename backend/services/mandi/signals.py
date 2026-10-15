"""
Descriptive market signals computed from weekly series (pure functions, no I/O).

A weekly price series is a list of {"week_start": "YYYY-MM-DD" (Monday), "price": float},
sorted by week. Every signal for week t uses only points at or before t, so a
value never changes when later data arrives (no look-ahead).

Thresholds below are engineering defaults, not values from the literature; the
1.15 arrivals threshold follows the master report's ">15% over capacity" rule.
"""
import math
import statistics
from datetime import date, timedelta

from services.mandi.config import COMMODITIES, TIER_MULTIPLIER

ARRIVALS_HIGH = 1.15          # report: oversupply when >15% above normal
ARRIVALS_LOW = 0.85
PRICE_RISING = 0.05           # 4-week change that counts as rising / falling
SURGE_RATIO = 2.0             # daily arrivals vs trailing 28-day median
Z_ALERT = 3.0                 # robust z of the weekly price change
SEASONAL_YEARS = 3
MIN_NORM_POINTS = 2
MIN_RETURNS_FOR_Z = 8
MIN_RETURNS_FOR_VOL = 5
MAD_SCALE = 1.4826            # makes MAD comparable to a standard deviation

QUADRANTS = {
    ("high", "rising"): "strong_demand",     # more arriving and still dearer
    ("low", "rising"): "supply_shortage",    # less arriving, price up
    ("high", "falling"): "glut",             # more arriving, price down
    ("low", "falling"): "weak_demand",       # less arriving, price still down
}


def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def _upto(series: list[dict], week: str) -> list[dict]:
    return [p for p in series if p["week_start"] <= week]


def _value_near(series: list[dict], target: date, tolerance_days: int = 7):
    """Price of the point closest to `target` within the tolerance, or None."""
    best = None
    for point in series:
        gap = abs((_d(point["week_start"]) - target).days)
        if gap <= tolerance_days and (best is None or gap < best[0]):
            best = (gap, point["price"])
    return best[1] if best else None


def weekly_returns(series: list[dict]) -> list[tuple[str, float]]:
    """Log returns between consecutive weeks only (gaps break the chain)."""
    out = []
    for prev, cur in zip(series, series[1:]):
        if (_d(cur["week_start"]) - _d(prev["week_start"])).days == 7 and prev["price"] > 0 and cur["price"] > 0:
            out.append((cur["week_start"], math.log(cur["price"] / prev["price"])))
    return out


def robust_z(value: float, history: list[float]):
    if len(history) < MIN_RETURNS_FOR_Z:
        return None
    median = statistics.median(history)
    mad = statistics.median(abs(x - median) for x in history)
    if mad == 0:
        return None
    return (value - median) / (MAD_SCALE * mad)


def seasonal_norm(series: list[dict], week: str, years: int = SEASONAL_YEARS):
    """Median price in the same ISO week (+-1) of the previous `years` years."""
    target = _d(week)
    iso_week = target.isocalendar()[1]
    values = []
    for point in series:
        day = _d(point["week_start"])
        age_days = (target - day).days
        if not 300 <= age_days <= years * 365 + 30:  # strictly earlier years only
            continue
        gap = abs(day.isocalendar()[1] - iso_week)
        if min(gap, 52 - gap) <= 1:  # same ISO week +-1, wrapping at year end
            values.append(point["price"])
    return statistics.median(values) if len(values) >= MIN_NORM_POINTS else None


def seasonal_index(series: list[dict], min_weeks_per_year: int = 40) -> dict:
    """
    Month -> average of (price / that year's mean), over complete-enough years.
    1.10 means prices typically run 10% above the annual average in that month.
    """
    by_year = {}
    for point in series:
        by_year.setdefault(_d(point["week_start"]).year, []).append(point)
    ratios = {}
    for points in by_year.values():
        if len(points) < min_weeks_per_year:
            continue
        mean = statistics.fmean(p["price"] for p in points)
        for p in points:
            ratios.setdefault(_d(p["week_start"]).month, []).append(p["price"] / mean)
    return {month: round(statistics.fmean(v), 3) for month, v in sorted(ratios.items())}


def arrivals_ratio(arrivals_weekly: list[dict], week: str):
    """
    Weekly arrivals (mean tonnes/day) vs normal. Seasonal norm (same ISO week of
    prior years) when available, else the median of the previous 8 weeks.
    Returns (ratio, basis) or (None, None).
    """
    known = [a for a in arrivals_weekly if a["week_start"] <= week]
    current = next((a for a in known if a["week_start"] == week), None)
    if not current or not current["tonnes_per_day"]:
        return None, None
    seasonal = seasonal_norm(
        [{"week_start": a["week_start"], "price": a["tonnes_per_day"]} for a in known], week)
    if seasonal:
        return current["tonnes_per_day"] / seasonal, "seasonal"
    start = (_d(week) - timedelta(weeks=8)).isoformat()
    prior = [a["tonnes_per_day"] for a in known if start <= a["week_start"] < week and a["tonnes_per_day"]]
    if len(prior) >= 4:
        return current["tonnes_per_day"] / statistics.median(prior), "rolling_8w"
    return None, None


def quadrant(arr_ratio, momentum):
    if arr_ratio is None or momentum is None:
        return "insufficient_data"
    arrivals = "high" if arr_ratio > ARRIVALS_HIGH else "low" if arr_ratio < ARRIVALS_LOW else "normal"
    price = "rising" if momentum > PRICE_RISING else "falling" if momentum < -PRICE_RISING else "flat"
    return QUADRANTS.get((arrivals, price), "balanced")


def urgency_score(commodity: str, arr_ratio=None, momentum_4w=None, price_z=None,
                  listing_age_days=None):
    """
    The master report's 1-10 urgency score, fed with observed signals.
    Components in [0, 1]: oversupply, falling price, abnormal crash and (optionally)
    listing age; weighted, then scaled by the perishability tier multiplier
    (Tier 1 x2.0, Tier 2 x1.3, Tier 3 x1.0). Returns (score or None, reasons).
    """
    parts, reasons = [], []
    if arr_ratio is not None:
        parts.append((0.4, min(max((arr_ratio - 1.0) / 1.0, 0.0), 1.0)))
        if arr_ratio > ARRIVALS_HIGH:
            reasons.append(f"arrivals {arr_ratio:.2f}x normal")
    if momentum_4w is not None:
        parts.append((0.35, min(max(-momentum_4w / 0.30, 0.0), 1.0)))
        if momentum_4w < -PRICE_RISING:
            reasons.append(f"price {momentum_4w:+.0%} over 4 weeks")
    if price_z is not None:
        parts.append((0.25, min(max(-price_z / Z_ALERT, 0.0), 1.0)))
        if price_z <= -Z_ALERT:
            reasons.append("abnormal weekly price drop")
    if listing_age_days is not None:
        shelf = {1: 7, 2: 30, 3: 180}[COMMODITIES[commodity]["tier"]]
        parts.append((0.2, min(max(listing_age_days / shelf, 0.0), 1.0)))
        if listing_age_days >= shelf / 2:
            reasons.append(f"listed {listing_age_days} days ago")
    if not parts:
        return None, ["not enough data"]

    raw = sum(w * v for w, v in parts) / sum(w for w, _ in parts)
    multiplier = TIER_MULTIPLIER[COMMODITIES[commodity]["tier"]]
    score = 1 + 9 * min(1.0, raw * multiplier)
    return int(round(min(max(score, 1), 10))), reasons


def week_signals(commodity: str, series: list[dict], week: str, arrivals_weekly: list[dict] = None) -> dict:
    """All descriptive signals for one scope at week `week`, using data <= week only."""
    hist = _upto(series, week)
    current = next((p for p in hist if p["week_start"] == week), None)
    out = {
        "week_start": week,
        "weeks_of_history": len(hist),
        "price": current["price"] if current else None,
        "momentum_4w": None, "momentum_13w": None, "volatility_8w": None,
        "price_z": None, "seasonal_norm": None, "price_vs_norm": None,
        "seasonal_index_month": None, "seasonal_trend": None,
        "arrivals_ratio": None, "arrivals_basis": None,
    }
    if not current:
        out["quadrant"] = "insufficient_data"
        out["urgency"], out["urgency_reasons"] = None, ["no price this week"]
        return out

    price, day = current["price"], _d(week)
    for key, weeks in (("momentum_4w", 4), ("momentum_13w", 13)):
        past = _value_near(hist[:-1], day - timedelta(weeks=weeks))
        if past:
            out[key] = round(price / past - 1, 4)

    returns = weekly_returns(hist)
    if returns and returns[-1][0] == week:
        prior = [r for _, r in returns[-27:-1]]
        z = robust_z(returns[-1][1], prior)
        out["price_z"] = round(z, 2) if z is not None else None
    recent = [r for _, r in returns[-8:]]
    if len(recent) >= MIN_RETURNS_FOR_VOL:
        out["volatility_8w"] = round(statistics.stdev(recent), 4)

    norm = seasonal_norm(hist, week)
    if norm:
        out["seasonal_norm"] = round(norm, 2)
        out["price_vs_norm"] = round(price / norm - 1, 4)

    index = seasonal_index(hist)
    if day.month in index:
        out["seasonal_index_month"] = index[day.month]
        next_month = day.month % 12 + 1
        if next_month in index:
            out["seasonal_trend"] = "rising" if index[next_month] > index[day.month] else "receding"

    if arrivals_weekly:
        ratio, basis = arrivals_ratio(arrivals_weekly, week)
        if ratio is not None:
            out["arrivals_ratio"], out["arrivals_basis"] = round(ratio, 3), basis

    out["quadrant"] = quadrant(out["arrivals_ratio"], out["momentum_4w"])
    out["urgency"], out["urgency_reasons"] = urgency_score(
        commodity, out["arrivals_ratio"], out["momentum_4w"], out["price_z"])
    return out


def daily_arrival_surge(daily: list[dict], day: str, window_days: int = 28):
    """Ratio of `day`'s arrivals to the median of the previous 28 days (>= 7 days of data)."""
    current = next((a for a in daily if a["date"] == day), None)
    if not current or not current.get("arrival_tonnes"):
        return None
    start = (_d(day) - timedelta(days=window_days)).isoformat()
    prior = [a["arrival_tonnes"] for a in daily if start <= a["date"] < day and a.get("arrival_tonnes")]
    if len(prior) < 7:
        return None
    return current["arrival_tonnes"] / statistics.median(prior)
