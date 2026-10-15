"""
Agronomic Eligibility, Water Constraint, and Explainability Service for ALIP
Validates crops against seasonal, irrigation, thermal, and edaphic constraints.
Provides transparent suitability scores and human-readable agronomic explanations.
"""

from typing import Dict, List, Any, Optional

CROP_AGRONOMIC_SPECS = {
    "rice": {
        "display_name": "Rice (Paddy)",
        "seasons": ["kharif", "zaid"],
        "water_demand": "high",
        "min_water_mm": 150.0,
        "ideal_temp_range": (20.0, 38.0),
        "ideal_ph_range": (5.5, 7.5),
        "soil_types": ["Alluvial Soil", "Clayey Soil", "Red Soil"],
        "description": "Best grown in monsoon or with assured flooding/canal irrigation. Requires waterlogged soil conditions during tillering.",
        "best_irrigation": ["canal", "flooding", "borewell"],
    },
    "maize": {
        "display_name": "Maize (Corn)",
        "seasons": ["kharif", "rabi", "zaid"],
        "water_demand": "medium",
        "min_water_mm": 60.0,
        "ideal_temp_range": (18.0, 35.0),
        "ideal_ph_range": (5.8, 7.5),
        "soil_types": ["Alluvial Soil", "Red Soil", "Black Soil", "Loam"],
        "description": "Versatile cereal crop with moderate water demand. Sensitive to prolonged waterlogging; requires well-drained fertile soil.",
        "best_irrigation": ["rainfed", "canal", "drip", "borewell"],
    },
    "chickpea": {
        "display_name": "Chickpea (Gram)",
        "seasons": ["rabi"],
        "water_demand": "low",
        "min_water_mm": 35.0,
        "ideal_temp_range": (12.0, 28.0),
        "ideal_ph_range": (6.0, 8.0),
        "soil_types": ["Black Soil", "Alluvial Soil", "Loam"],
        "description": "Cool-season legume. Fixes atmospheric nitrogen. Thrives in dry winter weather; sensitive to heavy monsoon rainfall.",
        "best_irrigation": ["rainfed", "sprinkler", "borewell"],
    },
    "kidneybeans": {
        "display_name": "Kidney Beans (Rajma)",
        "seasons": ["kharif", "rabi"],
        "water_demand": "medium",
        "min_water_mm": 65.0,
        "ideal_temp_range": (15.0, 30.0),
        "ideal_ph_range": (5.5, 6.8),
        "soil_types": ["Loam", "Red Soil", "Alluvial Soil"],
        "description": "Requires mild temperatures and moderate moisture. Highly susceptible to waterlogging and soil alkalinity.",
        "best_irrigation": ["canal", "borewell", "drip"],
    },
    "pigeonpeas": {
        "display_name": "Pigeon Peas (Arhar / Tur)",
        "seasons": ["kharif"],
        "water_demand": "low-medium",
        "min_water_mm": 50.0,
        "ideal_temp_range": (20.0, 38.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Red Soil", "Black Soil", "Alluvial Soil"],
        "description": "Deep-rooted drought-hardy pulse. Highly suitable for semi-arid rainfed conditions and intercropping.",
        "best_irrigation": ["rainfed", "protective", "drip"],
    },
    "mothbeans": {
        "display_name": "Moth Bean",
        "seasons": ["kharif", "zaid"],
        "water_demand": "very-low",
        "min_water_mm": 25.0,
        "ideal_temp_range": (24.0, 42.0),
        "ideal_ph_range": (6.5, 8.5),
        "soil_types": ["Desert Soil", "Sandy Loam", "Arid Soil"],
        "description": "Extremely drought-resilient legume. Thrives in high summer temperatures and arid sandy tracts.",
        "best_irrigation": ["rainfed", "minimal"],
    },
    "mungbean": {
        "display_name": "Green Gram (Mung Bean)",
        "seasons": ["kharif", "zaid"],
        "water_demand": "low-medium",
        "min_water_mm": 40.0,
        "ideal_temp_range": (25.0, 38.0),
        "ideal_ph_range": (6.2, 7.5),
        "soil_types": ["Red Soil", "Alluvial Soil", "Sandy Loam"],
        "description": "Short-duration crop (60-70 days). Excellent catch crop in Zaid summer or Kharif early monsoon.",
        "best_irrigation": ["rainfed", "borewell", "sprinkler"],
    },
    "blackgram": {
        "display_name": "Black Gram (Urad)",
        "seasons": ["kharif", "rabi"],
        "water_demand": "medium",
        "min_water_mm": 50.0,
        "ideal_temp_range": (22.0, 35.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Black Soil", "Red Soil", "Alluvial Soil"],
        "description": "Prefers warm and humid tropical climate. Performs well in moisture-retentive black soils.",
        "best_irrigation": ["rainfed", "canal", "borewell"],
    },
    "lentil": {
        "display_name": "Lentil (Masoor)",
        "seasons": ["rabi"],
        "water_demand": "low",
        "min_water_mm": 30.0,
        "ideal_temp_range": (10.0, 26.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Alluvial Soil", "Clay Loam", "Black Soil"],
        "description": "Cool-season legume with excellent cold tolerance. Best planted after monsoon harvest in winter.",
        "best_irrigation": ["rainfed", "sprinkler"],
    },
    "pomegranate": {
        "display_name": "Pomegranate",
        "seasons": ["kharif", "rabi", "zaid"],
        "water_demand": "low-medium",
        "min_water_mm": 40.0,
        "ideal_temp_range": (20.0, 38.0),
        "ideal_ph_range": (6.5, 8.0),
        "soil_types": ["Red Loam", "Black Soil", "Sandy Loam"],
        "description": "Commercial fruit crop suited for semi-arid and subtropical regions. Responsive to drip fertigation.",
        "best_irrigation": ["drip", "borewell"],
    },
    "banana": {
        "display_name": "Banana",
        "seasons": ["kharif", "zaid", "rabi"],
        "water_demand": "high",
        "min_water_mm": 140.0,
        "ideal_temp_range": (20.0, 36.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Alluvial Soil", "Clay Loam", "Red Soil"],
        "description": "Heavy feeder requiring continuous soil moisture, high humidity, and protection from strong winds.",
        "best_irrigation": ["drip", "canal", "flood"],
    },
    "mango": {
        "display_name": "Mango",
        "seasons": ["kharif", "zaid", "rabi"],
        "water_demand": "medium",
        "min_water_mm": 70.0,
        "ideal_temp_range": (22.0, 40.0),
        "ideal_ph_range": (5.5, 7.5),
        "soil_types": ["Alluvial Soil", "Red Loam", "Laterite Soil"],
        "description": "Tropical perennial fruit crop requiring dry winter period for flowering and warm dry weather for fruit development.",
        "best_irrigation": ["drip", "protective"],
    },
    "grapes": {
        "display_name": "Grapes",
        "seasons": ["rabi", "zaid"],
        "water_demand": "medium",
        "min_water_mm": 50.0,
        "ideal_temp_range": (15.0, 35.0),
        "ideal_ph_range": (6.5, 8.0),
        "soil_types": ["Sandy Loam", "Red Loam", "Black Soil"],
        "description": "High-value horticultural crop. Requires warm dry climate with cool nights and well-drained soil.",
        "best_irrigation": ["drip"],
    },
    "watermelon": {
        "display_name": "Watermelon",
        "seasons": ["zaid"],
        "water_demand": "medium",
        "min_water_mm": 40.0,
        "ideal_temp_range": (24.0, 38.0),
        "ideal_ph_range": (6.0, 7.0),
        "soil_types": ["Sandy Loam", "Alluvial Soil", "Red Sandy Soil"],
        "description": "Warm-season cucurbit best sown in summer (Zaid). Requires abundant sunshine and well-drained sandy soil.",
        "best_irrigation": ["drip", "canal", "borewell"],
    },
    "muskmelon": {
        "display_name": "Muskmelon",
        "seasons": ["zaid"],
        "water_demand": "medium",
        "min_water_mm": 35.0,
        "ideal_temp_range": (25.0, 38.0),
        "ideal_ph_range": (6.0, 7.2),
        "soil_types": ["Sandy Loam", "Alluvial Soil"],
        "description": "Dry and sunny summer climate ensures high sugar content. Vulnerable to humid fungal rot.",
        "best_irrigation": ["drip", "borewell"],
    },
    "apple": {
        "display_name": "Apple",
        "seasons": ["rabi"],
        "water_demand": "medium",
        "min_water_mm": 80.0,
        "ideal_temp_range": (5.0, 22.0),
        "ideal_ph_range": (5.5, 6.5),
        "soil_types": ["Loam", "Clay Loam"],
        "description": "Temperate fruit crop requiring winter chilling hours (< 7°C) and mild summers. Suitable for hilly highlands.",
        "best_irrigation": ["drip", "canal"],
    },
    "orange": {
        "display_name": "Orange (Citrus)",
        "seasons": ["kharif", "rabi"],
        "water_demand": "medium",
        "min_water_mm": 80.0,
        "ideal_temp_range": (15.0, 35.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Black Soil", "Alluvial Soil", "Red Loam"],
        "description": "Subtropical citrus crop. Sensitive to waterlogging and severe frost. Prefers well-aerated light to medium soils.",
        "best_irrigation": ["drip", "micro-sprinkler"],
    },
    "papaya": {
        "display_name": "Papaya",
        "seasons": ["kharif", "zaid", "rabi"],
        "water_demand": "medium",
        "min_water_mm": 90.0,
        "ideal_temp_range": (22.0, 36.0),
        "ideal_ph_range": (6.0, 7.0),
        "soil_types": ["Sandy Loam", "Alluvial Soil", "Red Loam"],
        "description": "Fast-growing fruit tree. Extremely sensitive to root rot under standing water; requires elevated beds.",
        "best_irrigation": ["drip", "ring"],
    },
    "coconut": {
        "display_name": "Coconut",
        "seasons": ["kharif", "rabi", "zaid"],
        "water_demand": "high",
        "min_water_mm": 120.0,
        "ideal_temp_range": (20.0, 35.0),
        "ideal_ph_range": (5.2, 8.0),
        "soil_types": ["Laterite Soil", "Alluvial Soil", "Coastal Sandy"],
        "description": "Tropical coastal perennial requiring high humidity and steady subsoil water table.",
        "best_irrigation": ["basin", "drip"],
    },
    "cotton": {
        "display_name": "Cotton",
        "seasons": ["kharif"],
        "water_demand": "medium",
        "min_water_mm": 60.0,
        "ideal_temp_range": (21.0, 36.0),
        "ideal_ph_range": (6.0, 8.0),
        "soil_types": ["Black Soil", "Alluvial Soil", "Red Soil"],
        "description": "Major commercial cash crop. Thrives in deep moisture-retentive black soils (Regur) of the Deccan plateau.",
        "best_irrigation": ["rainfed", "canal", "drip", "borewell"],
    },
    "jute": {
        "display_name": "Jute",
        "seasons": ["kharif"],
        "water_demand": "high",
        "min_water_mm": 130.0,
        "ideal_temp_range": (24.0, 37.0),
        "ideal_ph_range": (6.0, 7.5),
        "soil_types": ["Alluvial Soil", "Clay Loam"],
        "description": "Warm and humid monsoon crop. Requires standing water retting facilities and fertile alluvial plains.",
        "best_irrigation": ["rainfed", "canal"],
    },
    "coffee": {
        "display_name": "Coffee",
        "seasons": ["kharif", "rabi"],
        "water_demand": "medium-high",
        "min_water_mm": 120.0,
        "ideal_temp_range": (15.0, 28.0),
        "ideal_ph_range": (5.0, 6.5),
        "soil_types": ["Laterite Soil", "Red Loam"],
        "description": "Shade-loving plantation crop of tropical highlands. Requires well-drained acidic humus-rich soil.",
        "best_irrigation": ["sprinkler", "protective"],
    },
}


def assess_crop_eligibility(
    crop: str,
    season: str,
    temperature: float,
    rainfall: float,
    soil_ph: float,
    soil_type: str,
    irrigation: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates hard constraints, eligibility, suitability reasons, and agronomic risks.
    """
    spec = CROP_AGRONOMIC_SPECS.get(crop.lower())
    if not spec:
        return {
            "eligible": True,
            "suitability_penalty": 0,
            "reasons": ["Compatible with general agricultural practices."],
            "warnings": [],
        }

    reasons: List[str] = []
    warnings: List[str] = []
    penalty = 0

    norm_season = season.lower()
    norm_irrigation = (irrigation or "rainfed").lower()

    # 1. Seasonal Compatibility
    if norm_season in spec["seasons"]:
        reasons.append(f"Strong match for the {season.capitalize()} planting calendar.")
    else:
        penalty += 25
        warnings.append(
            f"Off-season: {spec['display_name']} is traditionally grown in {', '.join([s.capitalize() for s in spec['seasons']])}."
        )

    # 2. Water & Irrigation Feasibility
    is_assured_irrigation = norm_irrigation in ["canal", "borewell", "drip", "flooding"]
    if spec["water_demand"] == "high":
        if is_assured_irrigation or rainfall >= spec["min_water_mm"]:
            reasons.append(
                f"Water demand ({spec['water_demand'].capitalize()}) is supported by {norm_irrigation.capitalize()} irrigation."
            )
        else:
            penalty += 35
            warnings.append(
                f"High water deficit: Rainfall ({rainfall:.0f} mm) is below required {spec['min_water_mm']:.0f} mm without assured irrigation."
            )
    else:
        if rainfall >= spec["min_water_mm"] or is_assured_irrigation:
            reasons.append(f"Moisture availability matches crop water requirement ({spec['water_demand']}).")

    # 3. Thermal Compatibility
    min_t, max_t = spec["ideal_temp_range"]
    if min_t <= temperature <= max_t:
        reasons.append(f"Ambient temperature ({temperature:.1f}°C) is in the optimal growth range ({min_t}-{max_t}°C).")
    elif abs(temperature - min_t) <= 4 or abs(temperature - max_t) <= 4:
        penalty += 10
        warnings.append(f"Marginal thermal range: Current {temperature:.1f}°C vs optimal {min_t}-{max_t}°C.")
    else:
        penalty += 25
        warnings.append(f"Suboptimal thermal conditions for {spec['display_name']}.")

    # 4. Soil pH Compatibility
    min_ph, max_ph = spec["ideal_ph_range"]
    if min_ph <= soil_ph <= max_ph:
        reasons.append(f"Soil pH ({soil_ph:.1f}) is within ideal root absorption range ({min_ph}-{max_ph}).")
    else:
        penalty += 10
        warnings.append(f"pH level ({soil_ph:.1f}) deviates from preferred {min_ph}-{max_ph}.")

    # 5. Soil Type Compatibility
    if any(st.lower() in soil_type.lower() for st in spec["soil_types"]):
        reasons.append(f"Thrives in local {soil_type} profile.")

    eligible = penalty < 50
    return {
        "eligible": eligible,
        "suitability_penalty": penalty,
        "reasons": reasons,
        "warnings": warnings,
        "water_demand": spec["water_demand"],
        "display_name": spec["display_name"],
        "description": spec["description"],
    }
