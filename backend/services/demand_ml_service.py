"""
ALIP - Dynamic ML Demand Prediction Service
Replaces static hardcoded thresholds with
ML-predicted dynamic demand thresholds.
Algorithm: Gradient Boosting Regressor
"""

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency during startup
    np = None

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score
except Exception:  # pragma: no cover - optional dependency during startup
    GradientBoostingRegressor = None
    cross_val_score = None

import joblib, os, datetime

os.makedirs("data", exist_ok=True)

# ─── Encodings ─────────────────────────────────────────
CROP_MAP    = {"rice":0,"wheat":1,"maize":2,"cotton":3,
               "sugarcane":4,"groundnut":5,"soybean":6,
               "default":7}
SEASON_MAP  = {"kharif":0,"rabi":1,"zaid":2}
RTYPE_MAP   = {"urban":0,"semi-urban":1,"rural":2}
MSIZE_MAP   = {"large":2,"medium":1,"small":0}
SEASON_MONTHS = {
    1:"rabi", 2:"rabi", 3:"rabi",  4:"zaid",
    5:"zaid", 6:"kharif",7:"kharif",8:"kharif",
    9:"kharif",10:"kharif",11:"rabi",12:"rabi"
}

# ─── Training Data ─────────────────────────────────────
# Features: [crop, season, region_type,
#            population_density, market_size, month]
# Target:   demand_threshold_kg

X_TRAIN = [
    # rice - kharif - urban - high density
    [0,0,0,18480,2,7],[0,0,0,10100,2,7],
    [0,0,0,26903,2,7],[0,0,0,20667,2,8],
    [0,0,0,24252,2,8],[0,0,0,8000,2,7],
    # rice - kharif - semi-urban
    [0,0,1,3100,1,7],[0,0,1,4600,1,8],
    [0,0,1,3900,1,7],[0,0,1,2900,1,8],
    [0,0,1,2700,1,7],[0,0,1,2100,1,8],
    # rice - rabi - urban
    [0,1,0,18480,2,11],[0,1,0,10100,2,12],
    [0,1,0,6900,2,11],[0,1,0,9800,2,12],
    # rice - rabi - semi-urban
    [0,1,1,3100,1,11],[0,1,1,2700,1,12],
    # wheat - rabi - urban
    [1,1,0,8000,2,11],[1,1,0,6400,2,12],
    [1,1,0,5200,2,1],[1,1,0,6900,2,11],
    [1,1,0,3400,2,12],[1,1,0,9800,2,11],
    # wheat - rabi - semi-urban
    [1,1,1,3400,1,12],[1,1,1,2400,1,1],
    [1,1,1,3100,1,11],[1,1,1,2700,1,12],
    # maize - kharif - urban
    [2,0,0,18480,2,7],[2,0,0,4378,2,6],
    [2,0,0,7200,2,7],[2,0,0,9800,2,6],
    # maize - kharif - semi-urban
    [2,0,1,3100,1,7],[2,0,1,4600,1,8],
    [2,0,1,2900,1,7],[2,0,1,2700,1,6],
    # cotton - kharif - urban
    [3,0,0,9800,2,7],[3,0,0,18480,2,6],
    [3,0,0,7200,2,7],[3,0,0,4600,2,8],
    # cotton - kharif - semi-urban
    [3,0,1,4600,1,7],[3,0,1,2800,1,8],
    # cotton - rural
    [3,0,2,1750,0,7],[3,0,2,2100,0,8],
    # sugarcane - kharif - urban
    [4,0,0,11800,2,6],[4,0,0,10100,2,7],
    [4,0,0,7200,2,8],[4,0,0,18480,2,6],
    # groundnut - kharif
    [5,0,1,3600,1,7],[5,0,1,1750,0,6],
    [5,0,0,9800,2,7],[5,0,1,4600,1,8],
    # soybean - kharif
    [6,0,1,2700,1,7],[6,0,1,3400,1,6],
    [6,0,0,5200,2,7],[6,0,1,2100,1,8],
]

Y_TRAIN = [
    # rice kharif urban
    820,650,1100,950,980,700,
    # rice kharif semi-urban
    380,420,360,310,290,250,
    # rice rabi urban
    580,460,420,500,
    # rice rabi semi-urban
    280,250,
    # wheat rabi urban
    720,580,490,610,460,680,
    # wheat rabi semi-urban
    320,240,290,260,
    # maize kharif urban
    560,380,430,480,
    # maize kharif semi-urban
    290,320,280,260,
    # cotton kharif urban
    480,520,460,410,
    # cotton semi-urban
    280,210,
    # cotton rural
    140,160,
    # sugarcane urban
    680,590,520,720,
    # groundnut
    310,180,420,350,
    # soybean
    260,290,380,230,
]

MODEL_PATH = "data/demand_model.pkl"

# ─── Train Model ───────────────────────────────────────
def train_demand_model():
    if np is None or GradientBoostingRegressor is None or cross_val_score is None:
        raise RuntimeError("Demand prediction ML dependencies are not installed.")

    X = np.array(X_TRAIN)
    y = np.array(Y_TRAIN)
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    scores = cross_val_score(
        model, X, y, cv=5, scoring="r2"
    )
    print(f"5-Fold CV R²: "
          f"{scores.mean():.4f} ± {scores.std():.4f}")
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    print(f"✅ Model saved → {MODEL_PATH}")
    return model

def get_demand_model():
    if np is None or joblib is None:
        return None
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_demand_model()

try:
    _model = get_demand_model()
except Exception as exc:
    print(f"Demand model unavailable: {exc}")
    _model = None

# ─── Predict Dynamic Threshold ─────────────────────────
def predict_dynamic_threshold(
    crop: str,
    region_type: str,
    population_density: int,
    market_size: str,
    month: int = None
) -> dict:
    """
    Predict dynamic demand threshold using
    Gradient Boosting Regressor.
    Replaces static hardcoded thresholds.
    """
    if _model is None:
        return {
            "crop": crop,
            "season": SEASON_MONTHS.get(month or datetime.datetime.now().month, "kharif"),
            "month": month or datetime.datetime.now().month,
            "region_type": region_type,
            "population_density": population_density,
            "market_size": market_size,
            "predicted_threshold_kg": 500,
            "threshold_type": "fallback-static",
            "model": "Static fallback"
        }

    if month is None:
        month = datetime.datetime.now().month

    season     = SEASON_MONTHS.get(month, "kharif")
    crop_enc   = CROP_MAP.get(crop.lower(), 7)
    season_enc = SEASON_MAP.get(season, 0)
    rtype_enc  = RTYPE_MAP.get(region_type, 1)
    msize_enc  = MSIZE_MAP.get(market_size, 1)

    features   = np.array([[
        crop_enc, season_enc, rtype_enc,
        population_density, msize_enc, month
    ]])

    predicted  = max(100.0,
                     round(float(_model.predict(features)[0])))

    return {
        "crop":                   crop,
        "season":                 season,
        "month":                  month,
        "region_type":            region_type,
        "population_density":     population_density,
        "market_size":            market_size,
        "predicted_threshold_kg": predicted,
        "threshold_type":         "ML-predicted (dynamic)",
        "model":                  "Gradient Boosting Regressor"
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