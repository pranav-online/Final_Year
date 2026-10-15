"""
ALIP - legacy demand helpers for the /market/demand/{region} view.

The former "dynamic threshold" GradientBoostingRegressor was trained on 56
hand-typed rows with no data source and no evaluation; it was removed in the
demand-analysis redesign (phase 3). Real signals and forecasts now come from
services/mandi. Until the legacy view is replaced (phase 4), the expected
demand it shows is the configured per-crop threshold, labelled as such.
"""

import datetime

import numpy as np

from services.demand_analysis import get_demand_threshold

SEASON_MONTHS = {
    1:"rabi", 2:"rabi", 3:"rabi",  4:"zaid",
    5:"zaid", 6:"kharif",7:"kharif",8:"kharif",
    9:"kharif",10:"kharif",11:"rabi",12:"rabi"
}


def predict_dynamic_threshold(
    crop: str,
    region_type: str = None,
    population_density: int = None,
    market_size: str = None,
    month: int = None
) -> dict:
    """Configured per-crop threshold (placeholder; no ML model behind it)."""
    month = month or datetime.datetime.now().month
    return {
        "crop": crop,
        "season": SEASON_MONTHS.get(month, "kharif"),
        "month": month,
        "region_type": region_type,
        "population_density": population_density,
        "market_size": market_size,
        "predicted_threshold_kg": get_demand_threshold(crop),
        "threshold_type": "configured-static",
        "model": "Configured crop threshold (placeholder)",
    }


# ─── Supply Trend Analysis ─────────────────────────────
def analyze_supply_trend(
    supply_history: list,
    threshold: float
) -> dict:
    """
    Analyze supply trend over time using
    linear regression on historical data.
    Predicts next period and urgency level.
    Enhancement 3: Supply Trend Analysis
    """
    if len(supply_history) < 2:
        return {
            "trend":      "insufficient_data",
            "prediction": None,
            "urgency":    "unknown"
        }

    x = np.arange(len(supply_history), dtype=float)
    y = np.array(supply_history, dtype=float)

    # Linear regression coefficients
    coeffs    = np.polyfit(x, y, 1)
    slope     = coeffs[0]
    intercept = coeffs[1]

    # Next period prediction
    next_val  = slope * len(supply_history) + intercept
    next_val  = max(0.0, round(float(next_val), 2))

    # Trend classification
    mean_y      = float(np.mean(y))
    pct_change  = (slope / (mean_y + 1e-9)) * 100

    if pct_change > 15:
        trend   = "rapidly_increasing"
        urgency = "critical"
    elif pct_change > 5:
        trend   = "increasing"
        urgency = "high"
    elif pct_change < -15:
        trend   = "rapidly_decreasing"
        urgency = "monitor"
    elif pct_change < -5:
        trend   = "decreasing"
        urgency = "low"
    else:
        trend   = "stable"
        urgency = "normal"

    # Weeks until oversupply breach (1.5x threshold)
    breach_level      = threshold * 1.5
    weeks_to_breach   = None
    if slope > 0 and y[-1] < breach_level:
        remaining       = breach_level - y[-1]
        weeks_to_breach = max(0, int(round(remaining / slope)))

    # Trend message
    # In analyze_supply_trend, update message for critical:
    if urgency == "critical":
      if y[-1] >= breach_level:
        message = (
            f"CRITICAL: Supply already at {y[-1]:.0f} kg — "
            f"exceeds breach level of {breach_level:.0f} kg. "
            f"Immediate redistribution required!"
        )
      else:
        message = (
            f"CRITICAL: Supply rapidly increasing "
            f"({pct_change:.1f}%/period). "
            f"Oversupply breach expected in "
            f"{weeks_to_breach} weeks."
        )
    elif urgency == "high":
        message = (
            f"WARNING: Supply increasing steadily. "
            f"Monitor closely — breach in "
            f"{weeks_to_breach or 'unknown'} weeks."
        )
    elif urgency == "monitor":
        message = (
            f"MONITOR: Supply rapidly declining. "
            f"Undersupply risk developing."
        )
    elif urgency == "low":
        message = "Supply gradually declining. Normal seasonal pattern."
    else:
        message = "Supply stable within normal range."

    return {
        "history":           supply_history,
        "periods_analysed":  len(supply_history),
        "slope_per_period":  round(float(slope), 2),
        "pct_change":        round(float(pct_change), 2),
        "predicted_next_kg": next_val,
        "trend":             trend,
        "urgency":           urgency,
        "weeks_to_breach":   weeks_to_breach,
        "threshold":         threshold,
        "breach_level":      breach_level,
        "message":           message
    }
# ─── Price Sensitivity Database ────────────────────────
PRICE_SENSITIVITY = {
    "rice":      {"base_price": 22,  "elasticity": -0.35},
    "wheat":     {"base_price": 21,  "elasticity": -0.30},
    "maize":     {"base_price": 18,  "elasticity": -0.40},
    "cotton":    {"base_price": 65,  "elasticity": -0.25},
    "sugarcane": {"base_price": 3,   "elasticity": -0.20},
    "groundnut": {"base_price": 55,  "elasticity": -0.45},
    "soybean":   {"base_price": 43,  "elasticity": -0.38},
    "default":   {"base_price": 25,  "elasticity": -0.35}
}

def estimate_price_impact(
    crop: str,
    current_supply_kg: float,
    threshold_kg: float
) -> dict:
    """
    Estimate price drop due to oversupply using
    price elasticity model.
    Enhancement 4: Price Impact Estimation.
    Formula: %ΔP = elasticity × %ΔQ
    """
    sensitivity = PRICE_SENSITIVITY.get(
        crop.lower(),
        PRICE_SENSITIVITY["default"]
    )
    base_price = sensitivity["base_price"]
    elasticity = sensitivity["elasticity"]

    oversupply_ratio = (
        (current_supply_kg - threshold_kg) / threshold_kg
    )

    if oversupply_ratio <= 0:
        return {
            "crop":           crop,
            "status":         "no_oversupply",
            "price_impact_pct": 0,
            "recommendation": "No price intervention needed."
        }

    # Price elasticity formula
    pct_supply_increase = oversupply_ratio * 100
    pct_price_change    = elasticity * (pct_supply_increase / 100) * 100
    estimated_price     = base_price * (1 + pct_price_change / 100)
    estimated_price     = max(0.0, round(estimated_price, 2))

    loss_per_100kg = round(
        (base_price - estimated_price) * 100, 2
    )

    urgency = (
        "critical" if pct_price_change < -30
        else "high" if pct_price_change < -15
        else "medium"
    )

    if urgency == "critical":
        rec = (
            f"URGENT: Redistribute {crop} immediately. "
            f"Estimated {abs(pct_price_change):.1f}% price drop "
            f"(₹{estimated_price}/kg from ₹{base_price}/kg). "
            f"Loss: ₹{loss_per_100kg:.0f} per 100 kg."
        )
    elif urgency == "high":
        rec = (
            f"Redistribute {crop} within 48 hours. "
            f"Estimated {abs(pct_price_change):.1f}% price drop "
            f"if supply remains unchanged."
        )
    else:
        rec = (
            f"Monitor {crop} supply. "
            f"Moderate {abs(pct_price_change):.1f}% "
            f"potential price drop detected."
        )

    return {
        "crop":                     crop,
        "current_supply_kg":        current_supply_kg,
        "threshold_kg":             threshold_kg,
        "oversupply_ratio":         round(oversupply_ratio, 3),
        "base_price_per_kg":        base_price,
        "estimated_price_per_kg":   estimated_price,
        "price_drop_pct":           round(abs(pct_price_change), 2),
        "estimated_loss_per_100kg": loss_per_100kg,
        "urgency":                  urgency,
        "recommendation":           rec,
        "model":                    "Price elasticity model"
    }