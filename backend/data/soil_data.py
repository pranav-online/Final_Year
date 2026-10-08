# Region-wise soil data for Indian states
# N = Nitrogen, P = Phosphorous, K = Potassium, pH = Soil pH
import re

SOIL_DATA = {
    # Telangana
    "telangana": {
        "soil_type": "Red Soil",
        "N": 40, "P": 20, "K": 20, "ph": 6.5
    },
    "hyderabad": {
        "soil_type": "Red Soil",
        "N": 38, "P": 18, "K": 22, "ph": 6.4
    },
    "warangal": {
        "soil_type": "Red Sandy Soil",
        "N": 35, "P": 15, "K": 18, "ph": 6.3
    },
    "nizamabad": {
        "soil_type": "Black Soil",
        "N": 55, "P": 28, "K": 35, "ph": 7.2
    },
    "karimnagar": {
        "soil_type": "Red Soil",
        "N": 42, "P": 22, "K": 25, "ph": 6.6
    },

    # Andhra Pradesh
    "andhra pradesh": {
        "soil_type": "Red Soil",
        "N": 45, "P": 25, "K": 30, "ph": 6.8
    },
    "vijayawada": {
        "soil_type": "Alluvial Soil",
        "N": 65, "P": 35, "K": 40, "ph": 7.0
    },
    "visakhapatnam": {
        "soil_type": "Red Loam",
        "N": 48, "P": 24, "K": 28, "ph": 6.5
    },

    # Punjab
    "punjab": {
        "soil_type": "Alluvial Soil",
        "N": 90, "P": 42, "K": 43, "ph": 7.0
    },
    "ludhiana": {
        "soil_type": "Alluvial Soil",
        "N": 88, "P": 40, "K": 45, "ph": 7.1
    },
    "amritsar": {
        "soil_type": "Alluvial Soil",
        "N": 92, "P": 44, "K": 42, "ph": 6.9
    },

    # Maharashtra
    "maharashtra": {
        "soil_type": "Black Soil",
        "N": 60, "P": 30, "K": 40, "ph": 7.5
    },
    "pune": {
        "soil_type": "Black Soil",
        "N": 58, "P": 28, "K": 38, "ph": 7.3
    },
    "nagpur": {
        "soil_type": "Black Soil",
        "N": 62, "P": 32, "K": 42, "ph": 7.6
    },
    "mumbai": {
        "soil_type": "Laterite Soil",
        "N": 35, "P": 18, "K": 25, "ph": 6.0
    },

    # Tamil Nadu
    "tamil nadu": {
        "soil_type": "Red Loam",
        "N": 50, "P": 25, "K": 30, "ph": 6.5
    },
    "chennai": {
        "soil_type": "Sandy Loam",
        "N": 42, "P": 20, "K": 28, "ph": 6.2
    },
    "coimbatore": {
        "soil_type": "Red Soil",
        "N": 48, "P": 24, "K": 32, "ph": 6.4
    },
    "madurai": {
        "soil_type": "Black Soil",
        "N": 55, "P": 27, "K": 35, "ph": 7.0
    },

    # Karnataka
    "karnataka": {
        "soil_type": "Red Soil",
        "N": 45, "P": 22, "K": 28, "ph": 6.3
    },
    "bangalore": {
        "soil_type": "Red Loam",
        "N": 44, "P": 21, "K": 27, "ph": 6.2
    },
    "mysore": {
        "soil_type": "Red Sandy Soil",
        "N": 40, "P": 19, "K": 24, "ph": 6.0
    },

    # Kerala
    "kerala": {
        "soil_type": "Laterite Soil",
        "N": 30, "P": 15, "K": 25, "ph": 5.5
    },
    "kochi": {
        "soil_type": "Laterite Soil",
        "N": 28, "P": 14, "K": 23, "ph": 5.4
    },
    "thiruvananthapuram": {
        "soil_type": "Laterite Soil",
        "N": 32, "P": 16, "K": 26, "ph": 5.6
    },

    # Uttar Pradesh
    "uttar pradesh": {
        "soil_type": "Alluvial Soil",
        "N": 80, "P": 38, "K": 40, "ph": 7.2
    },
    "lucknow": {
        "soil_type": "Alluvial Soil",
        "N": 82, "P": 39, "K": 41, "ph": 7.1
    },
    "varanasi": {
        "soil_type": "Alluvial Soil",
        "N": 78, "P": 36, "K": 38, "ph": 7.3
    },

    # Rajasthan
    "rajasthan": {
        "soil_type": "Desert Soil",
        "N": 25, "P": 12, "K": 15, "ph": 8.0
    },
    "jaipur": {
        "soil_type": "Desert Sandy Soil",
        "N": 22, "P": 10, "K": 13, "ph": 8.2
    },
    "jodhpur": {
        "soil_type": "Arid Soil",
        "N": 20, "P": 8, "K": 12, "ph": 8.4
    },

    # West Bengal
    "west bengal": {
        "soil_type": "Alluvial Soil",
        "N": 85, "P": 40, "K": 42, "ph": 6.8
    },
    "kolkata": {
        "soil_type": "Alluvial Soil",
        "N": 83, "P": 38, "K": 40, "ph": 6.7
    },

    # Gujarat
    "gujarat": {
        "soil_type": "Black Soil",
        "N": 58, "P": 29, "K": 38, "ph": 7.4
    },
    "ahmedabad": {
        "soil_type": "Black Soil",
        "N": 56, "P": 27, "K": 36, "ph": 7.3
    },
    "surat": {
        "soil_type": "Alluvial Soil",
        "N": 70, "P": 33, "K": 40, "ph": 7.0
    },

    # Madhya Pradesh
    "madhya pradesh": {
        "soil_type": "Black Soil",
        "N": 62, "P": 31, "K": 40, "ph": 7.5
    },
    "bhopal": {
        "soil_type": "Black Soil",
        "N": 60, "P": 30, "K": 39, "ph": 7.4
    },
    "indore": {
        "soil_type": "Black Soil",
        "N": 64, "P": 32, "K": 41, "ph": 7.6
    },

    # Default fallback
    "default": {
        "soil_type": "Mixed Soil",
        "N": 50, "P": 25, "K": 30, "ph": 6.8
    }
}

# Season wise rainfall data (mm)
SEASON_RAINFALL = {
    "kharif": 200.0,   # June - November (monsoon)
    "rabi": 50.0,      # November - April (winter)
    "zaid": 30.0,      # April - June (summer)
    "annual": 100.0    # General
}

STATE_SOIL_KEYS = {
    "telangana",
    "andhra pradesh",
    "punjab",
    "maharashtra",
    "tamil nadu",
    "karnataka",
    "kerala",
    "uttar pradesh",
    "rajasthan",
    "west bengal",
    "gujarat",
    "madhya pradesh",
}


def _get_soil_data_key(location: str) -> str | None:
    normalized_location = re.sub(r"[^a-z0-9]+", " ", location.lower()).strip()
    padded_location = f" {normalized_location} "
    matches = []
    for key in SOIL_DATA:
        if key == "default":
            continue
        normalized_key = re.sub(r"[^a-z0-9]+", " ", key.lower()).strip()
        if f" {normalized_key} " in padded_location:
            matches.append(key)

    specific_matches = [key for key in matches if key not in STATE_SOIL_KEYS]
    candidates = specific_matches or matches
    return max(candidates, key=len) if candidates else None


def get_soil_data(location: str) -> dict:
    key = _get_soil_data_key(location)
    return SOIL_DATA[key] if key else SOIL_DATA["default"]


def get_soil_data_source(location: str) -> str:
    return "regional estimate" if _get_soil_data_key(location) else "general estimate"

def get_rainfall(season: str) -> float:
    return SEASON_RAINFALL.get(season.lower(), 100.0)