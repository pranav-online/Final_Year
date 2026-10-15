"""
ALIP - legacy listing-based alert helpers (used by /notifications/alerts).

The former "dynamic threshold" GradientBoostingRegressor was trained on 56
hand-typed rows with no data source and no evaluation; it was removed in the
demand-analysis redesign. Real signals, forecasts and decisions now come from
services/mandi. The listing-based notifications still compare listed supply
with the configured per-crop threshold, labelled as a placeholder.
"""

import datetime

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