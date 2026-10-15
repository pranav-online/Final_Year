try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency during startup
    pd = None

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency during startup
    np = None

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
except Exception:  # pragma: no cover - optional dependency during startup
    RandomForestClassifier = None
    train_test_split = None
    LabelEncoder = None

try:
    import joblib
except Exception:  # pragma: no cover - optional dependency during startup
    joblib = None

import os
import re
import urllib.request
from data.soil_data import get_soil_data, get_soil_data_source, get_rainfall
from services.weather_service import get_weather
from services.geospatial_service import (
    resolve_coordinates,
    get_soil_profile_for_coordinates,
    get_weather_for_coordinates,
)
from services.crop_eligibility import assess_crop_eligibility, CROP_AGRONOMIC_SPECS

# ─── Paths ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "../data/Crop_recommendation.csv")
MODEL_PATH = os.path.join(BASE_DIR, "../data/crop_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "../data/label_encoder.pkl")

# ─── Crop Info ──────────────────────────────────────────────
CROP_INFO = {
    "rice": "Best grown in monsoon. Needs waterlogged conditions.",
    "maize": "Versatile crop for moderate climates. Good for Kharif season.",
    "chickpea": "Cool, dry climate crop. Best for Rabi season.",
    "kidneybeans": "Needs warm temperature and moderate rainfall.",
    "pigeonpeas": "Drought resistant. Suitable for tropical climates.",
    "mothbeans": "Highly drought tolerant. Best for arid regions.",
    "mungbean": "Warm humid conditions. Good for Kharif season.",
    "blackgram": "Tropical and subtropical climate crop.",
    "lentil": "Cool dry conditions. Best for Rabi season.",
    "pomegranate": "Semi-arid conditions with hot summers.",
    "banana": "High humidity and warmth needed year round.",
    "mango": "Tropical climate with dry winters.",
    "grapes": "Warm dry climate with cool nights.",
    "watermelon": "Warm temperature and sandy loam soil.",
    "muskmelon": "Warm dry climate. Best for Zaid season.",
    "apple": "Cold winters and mild summers required.",
    "orange": "Subtropical climate preferred.",
    "papaya": "Warm humid conditions year round.",
    "coconut": "Tropical coastal areas.",
    "cotton": "Warm temperature and moderate rainfall.",
    "jute": "Warm humid conditions.",
    "coffee": "Tropical highlands with moderate rainfall."
}

REGION_STATE_ALIASES = {
    "andhra pradesh": ("andhra pradesh", "vijayawada", "visakhapatnam"),
    "arunachal pradesh": ("arunachal pradesh", "itanagar"),
    "assam": ("assam", "guwahati"),
    "bihar": ("bihar", "patna"),
    "chhattisgarh": ("chhattisgarh", "raipur"),
    "goa": ("goa", "panaji"),
    "gujarat": ("gujarat", "ahmedabad", "surat"),
    "haryana": ("haryana", "hisar"),
    "himachal pradesh": ("himachal pradesh", "shimla"),
    "jharkhand": ("jharkhand", "ranchi"),
    "karnataka": ("karnataka", "bangalore", "mysore"),
    "kerala": ("kerala", "kochi", "thiruvananthapuram"),
    "madhya pradesh": ("madhya pradesh", "bhopal", "indore"),
    "maharashtra": ("maharashtra", "pune", "nagpur", "mumbai"),
    "manipur": ("manipur", "imphal"),
    "meghalaya": ("meghalaya", "shillong"),
    "mizoram": ("mizoram", "aizawl"),
    "nagaland": ("nagaland", "kohima"),
    "odisha": ("odisha", "bhubaneswar"),
    "punjab": ("punjab", "ludhiana", "amritsar"),
    "rajasthan": ("rajasthan", "jaipur", "jodhpur"),
    "sikkim": ("sikkim", "gangtok"),
    "tamil nadu": ("tamil nadu", "chennai", "coimbatore", "madurai"),
    "telangana": ("telangana", "hyderabad", "warangal", "nizamabad", "karimnagar"),
    "tripura": ("tripura", "agartala"),
    "uttar pradesh": ("uttar pradesh", "lucknow", "varanasi"),
    "uttarakhand": ("uttarakhand", "dehradun"),
    "west bengal": ("west bengal", "kolkata"),
}

_REGIONAL_CROP_DATA = {
    "andhra pradesh": {
        "region": "Andhra Pradesh",
        "kharif": (
            ["Rice (paddy)", "Cotton", "Maize", "Pigeon pea", "Black gram", "Groundnut", "Sugarcane"],
            ["rice", "cotton", "maize"],
            ["groundnut", "sugarcane"],
        ),
        "rabi": (
            ["Chickpea", "Lentil", "Maize", "Rice (paddy)", "Groundnut"],
            ["chickpea", "lentil", "maize"],
            ["groundnut"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Maize", "Groundnut"],
            ["mungbean", "watermelon", "maize"],
            ["groundnut"],
        ),
    },
    "telangana": {
        "region": "Telangana",
        "kharif": (
            ["Rice (paddy)", "Cotton", "Maize", "Pigeon pea", "Green gram", "Soybean"],
            ["rice", "cotton", "maize"],
            ["soybean"],
        ),
        "rabi": (
            ["Chickpea", "Maize", "Lentil", "Sorghum", "Safflower"],
            ["chickpea", "maize", "lentil"],
            ["sorghum", "safflower"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize"],
            ["mungbean", "watermelon", "muskmelon"],
            [],
        ),
    },
    "punjab": {
        "region": "Punjab",
        "kharif": (
            [
                "Rice (paddy)", "Cotton", "Maize", "Sugarcane", "Fodder crops",
                "Pigeon pea", "Green gram", "Black gram",
            ],
            ["rice", "cotton", "maize"],
            ["sugarcane", "fodder crops"],
        ),
        "rabi": (
            ["Wheat", "Mustard", "Chickpea", "Lentil", "Potato"],
            ["chickpea", "lentil", "potato"],
            ["wheat", "mustard"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize", "Fodder crops"],
            ["mungbean", "watermelon", "muskmelon"],
            ["fodder crops"],
        ),
    },
    "maharashtra": {
        "region": "Maharashtra",
        "kharif": (
            ["Cotton", "Soybean", "Rice", "Maize", "Pigeon pea", "Green gram"],
            ["cotton", "rice", "maize"],
            ["soybean"],
        ),
        "rabi": (
            ["Chickpea", "Wheat", "Sorghum", "Lentil", "Onion", "Maize"],
            ["chickpea", "lentil", "maize"],
            ["wheat", "sorghum", "onion"],
        ),
        "zaid": (
            ["Watermelon", "Muskmelon", "Green gram", "Maize"],
            ["watermelon", "muskmelon", "mungbean"],
            [],
        ),
    },
    "tamil nadu": {
        "region": "Tamil Nadu",
        "kharif": (
            ["Rice (paddy)", "Maize", "Cotton", "Black gram", "Sugarcane", "Groundnut"],
            ["rice", "maize", "cotton"],
            ["sugarcane", "groundnut"],
        ),
        "rabi": (
            ["Rice (paddy)", "Black gram", "Chickpea", "Maize", "Groundnut"],
            ["rice", "blackgram", "chickpea"],
            ["groundnut"],
        ),
        "zaid": (
            ["Watermelon", "Muskmelon", "Green gram", "Maize"],
            ["watermelon", "muskmelon", "mungbean"],
            [],
        ),
    },
    "karnataka": {
        "region": "Karnataka",
        "kharif": (
            ["Maize", "Rice (paddy)", "Cotton", "Pigeon pea", "Finger millet", "Soybean"],
            ["maize", "rice", "cotton"],
            ["finger millet", "soybean"],
        ),
        "rabi": (
            ["Chickpea", "Lentil", "Maize", "Wheat", "Finger millet"],
            ["chickpea", "lentil", "maize"],
            ["wheat", "finger millet"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize"],
            ["mungbean", "watermelon", "muskmelon"],
            [],
        ),
    },
    "kerala": {
        "region": "Kerala",
        "kharif": (
            ["Rice (paddy)", "Black gram", "Banana", "Coconut", "Tapioca"],
            ["rice", "blackgram", "banana"],
            ["coconut", "tapioca"],
        ),
        "rabi": (
            ["Rice (paddy)", "Black gram", "Banana", "Coconut"],
            ["rice", "blackgram", "banana"],
            ["coconut"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Banana", "Coconut"],
            ["rice", "mungbean", "watermelon"],
            ["coconut"],
        ),
    },
    "uttar pradesh": {
        "region": "Uttar Pradesh",
        "kharif": (
            ["Rice (paddy)", "Maize", "Cotton", "Pigeon pea", "Green gram", "Sugarcane"],
            ["rice", "maize", "cotton"],
            ["sugarcane"],
        ),
        "rabi": (
            ["Wheat", "Chickpea", "Lentil", "Potato", "Pea"],
            ["chickpea", "lentil", "potato"],
            ["wheat", "pea"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize", "Cucumber"],
            ["mungbean", "watermelon", "muskmelon"],
            ["cucumber"],
        ),
    },
    "rajasthan": {
        "region": "Rajasthan",
        "kharif": (
            ["Pearl millet", "Maize", "Moth bean", "Green gram", "Cotton", "Cluster bean"],
            ["maize", "mothbeans", "mungbean"],
            ["pearl millet", "cluster bean"],
        ),
        "rabi": (
            ["Wheat", "Mustard", "Chickpea", "Lentil", "Barley"],
            ["chickpea", "lentil"],
            ["wheat", "mustard", "barley"],
        ),
        "zaid": (
            ["Watermelon", "Muskmelon", "Green gram", "Moth bean"],
            ["watermelon", "muskmelon", "mungbean"],
            [],
        ),
    },
    "west bengal": {
        "region": "West Bengal",
        "kharif": (
            ["Rice (paddy)", "Jute", "Maize", "Green gram", "Black gram"],
            ["rice", "jute", "maize"],
            [],
        ),
        "rabi": (
            ["Potato", "Lentil", "Chickpea", "Wheat", "Rice"],
            ["potato", "lentil", "chickpea"],
            ["wheat"],
        ),
        "zaid": (
            ["Boro rice", "Green gram", "Watermelon", "Maize"],
            ["rice", "mungbean", "watermelon"],
            [],
        ),
    },
    "gujarat": {
        "region": "Gujarat",
        "kharif": (
            ["Cotton", "Groundnut", "Pearl millet", "Maize", "Pigeon pea", "Rice"],
            ["cotton", "maize", "pigeonpeas"],
            ["groundnut", "pearl millet"],
        ),
        "rabi": (
            ["Wheat", "Chickpea", "Lentil", "Mustard", "Cumin", "Maize"],
            ["chickpea", "lentil", "maize"],
            ["wheat", "mustard", "cumin"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Sesame"],
            ["mungbean", "watermelon", "muskmelon"],
            ["sesame"],
        ),
    },
    "madhya pradesh": {
        "region": "Madhya Pradesh",
        "kharif": (
            ["Soybean", "Maize", "Rice", "Cotton", "Pigeon pea"],
            ["maize", "rice", "cotton"],
            ["soybean"],
        ),
        "rabi": (
            ["Wheat", "Chickpea", "Lentil", "Mustard", "Pea", "Maize"],
            ["chickpea", "lentil", "maize"],
            ["wheat", "mustard", "pea"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize"],
            ["mungbean", "watermelon", "muskmelon"],
            [],
        ),
    },
    "arunachal pradesh": {
        "region": "Arunachal Pradesh",
        "kharif": (
            ["Rice (paddy)", "Maize", "Millets", "Pulses", "Pigeon pea"],
            ["rice", "maize", "pigeonpeas"],
            ["Millets", "Pulses"],
        ),
        "rabi": (
            ["Maize", "Mustard", "Chickpea", "Potato"],
            ["maize", "chickpea", "potato"],
            ["Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Maize", "Green gram", "Vegetables"],
            ["rice", "maize", "mungbean"],
            ["Vegetables"],
        ),
    },
    "assam": {
        "region": "Assam",
        "kharif": (
            ["Rice (paddy)", "Jute", "Maize", "Pulses"],
            ["rice", "jute", "maize"],
            ["Pulses"],
        ),
        "rabi": (
            ["Lentil", "Chickpea", "Maize", "Potato", "Mustard"],
            ["lentil", "chickpea", "maize"],
            ["Potato", "Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Maize", "Vegetables"],
            ["rice", "mungbean", "maize"],
            ["Vegetables"],
        ),
    },
    "bihar": {
        "region": "Bihar",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Jute", "Sugarcane"],
            ["rice", "maize", "pigeonpeas"],
            ["sugarcane"],
        ),
        "rabi": (
            ["Wheat", "Chickpea", "Lentil", "Maize", "Potato"],
            ["chickpea", "lentil", "maize"],
            ["Wheat", "Potato"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Maize", "Vegetables"],
            ["mungbean", "watermelon", "maize"],
            ["Vegetables"],
        ),
    },
    "chhattisgarh": {
        "region": "Chhattisgarh",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Black gram"],
            ["rice", "maize", "pigeonpeas"],
            [],
        ),
        "rabi": (
            ["Chickpea", "Lentil", "Maize", "Wheat"],
            ["chickpea", "lentil", "maize"],
            ["Wheat"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Maize", "Vegetables"],
            ["mungbean", "watermelon", "maize"],
            ["Vegetables"],
        ),
    },
    "goa": {
        "region": "Goa",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pulses", "Black gram", "Coconut"],
            ["rice", "maize", "blackgram"],
            ["Pulses"],
        ),
        "rabi": (
            ["Rice (paddy)", "Black gram", "Green gram", "Vegetables"],
            ["rice", "blackgram", "mungbean"],
            ["Vegetables"],
        ),
        "zaid": (
            ["Rice (paddy)", "Watermelon", "Green gram", "Vegetables"],
            ["rice", "watermelon", "mungbean"],
            ["Vegetables"],
        ),
    },
    "haryana": {
        "region": "Haryana",
        "kharif": (
            ["Rice (paddy)", "Cotton", "Maize", "Pearl millet", "Pigeon pea"],
            ["rice", "cotton", "maize"],
            ["Pearl millet"],
        ),
        "rabi": (
            ["Wheat", "Mustard", "Chickpea", "Lentil", "Potato"],
            ["chickpea", "lentil", "potato"],
            ["Wheat", "Mustard"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Muskmelon", "Maize"],
            ["mungbean", "watermelon", "muskmelon"],
            [],
        ),
    },
    "himachal pradesh": {
        "region": "Himachal Pradesh",
        "kharif": (
            ["Maize", "Rice (paddy)", "Kidney bean", "Kidney beans", "Pulses"],
            ["maize", "rice", "kidneybeans"],
            ["Pulses"],
        ),
        "rabi": (
            ["Wheat", "Barley", "Chickpea", "Lentil", "Potato"],
            ["chickpea", "lentil", "potato"],
            ["Wheat", "Barley"],
        ),
        "zaid": (
            ["Maize", "Watermelon", "Muskmelon", "Vegetables"],
            ["maize", "watermelon", "muskmelon"],
            ["Vegetables"],
        ),
    },
    "jharkhand": {
        "region": "Jharkhand",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Black gram"],
            ["rice", "maize", "pigeonpeas"],
            [],
        ),
        "rabi": (
            ["Chickpea", "Lentil", "Mustard", "Maize", "Potato"],
            ["chickpea", "lentil", "maize"],
            ["Mustard", "Potato"],
        ),
        "zaid": (
            ["Green gram", "Watermelon", "Maize", "Vegetables"],
            ["mungbean", "watermelon", "maize"],
            ["Vegetables"],
        ),
    },
    "manipur": {
        "region": "Manipur",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Black gram"],
            ["rice", "maize", "pigeonpeas"],
            [],
        ),
        "rabi": (
            ["Rice (paddy)", "Lentil", "Black gram", "Mustard"],
            ["rice", "lentil", "blackgram"],
            ["Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Vegetables"],
            ["rice", "mungbean", "watermelon"],
            ["Vegetables"],
        ),
    },
    "meghalaya": {
        "region": "Meghalaya",
        "kharif": (
            ["Rice (paddy)", "Maize", "Potato", "Pulses", "Black gram"],
            ["rice", "maize", "blackgram"],
            ["Potato", "Pulses"],
        ),
        "rabi": (
            ["Potato", "Maize", "Lentil", "Mustard", "Chickpea"],
            ["maize", "lentil", "chickpea"],
            ["Potato", "Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Maize", "Green gram", "Vegetables"],
            ["rice", "maize", "mungbean"],
            ["Vegetables"],
        ),
    },
    "mizoram": {
        "region": "Mizoram",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Pulses"],
            ["rice", "maize", "pigeonpeas"],
            ["Pulses"],
        ),
        "rabi": (
            ["Rice (paddy)", "Lentil", "Black gram", "Mustard"],
            ["rice", "lentil", "blackgram"],
            ["Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Vegetables"],
            ["rice", "mungbean", "watermelon"],
            ["Vegetables"],
        ),
    },
    "nagaland": {
        "region": "Nagaland",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Millets"],
            ["rice", "maize", "pigeonpeas"],
            ["Millets"],
        ),
        "rabi": (
            ["Rice (paddy)", "Lentil", "Chickpea", "Maize"],
            ["rice", "lentil", "chickpea"],
            [],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Vegetables"],
            ["rice", "mungbean", "watermelon"],
            ["Vegetables"],
        ),
    },
    "odisha": {
        "region": "Odisha",
        "kharif": (
            ["Rice (paddy)", "Maize", "Pigeon pea", "Green gram", "Black gram"],
            ["rice", "maize", "pigeonpeas"],
            [],
        ),
        "rabi": (
            ["Rice (paddy)", "Black gram", "Lentil", "Chickpea", "Mustard"],
            ["rice", "blackgram", "lentil"],
            ["Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Maize"],
            ["rice", "mungbean", "watermelon"],
            [],
        ),
    },
    "sikkim": {
        "region": "Sikkim",
        "kharif": (
            ["Maize", "Rice (paddy)", "Kidney bean", "Kidney beans", "Millets"],
            ["maize", "rice", "kidneybeans"],
            ["Millets"],
        ),
        "rabi": (
            ["Potato", "Maize", "Chickpea", "Lentil"],
            ["maize", "chickpea", "lentil"],
            ["Potato"],
        ),
        "zaid": (
            ["Maize", "Watermelon", "Green gram", "Vegetables"],
            ["maize", "watermelon", "mungbean"],
            ["Vegetables"],
        ),
    },
    "tripura": {
        "region": "Tripura",
        "kharif": (
            ["Rice (paddy)", "Jute", "Maize", "Pigeon pea"],
            ["rice", "jute", "maize"],
            [],
        ),
        "rabi": (
            ["Rice (paddy)", "Lentil", "Black gram", "Mustard"],
            ["rice", "lentil", "blackgram"],
            ["Mustard"],
        ),
        "zaid": (
            ["Rice (paddy)", "Green gram", "Watermelon", "Maize"],
            ["rice", "mungbean", "watermelon"],
            [],
        ),
    },
    "uttarakhand": {
        "region": "Uttarakhand",
        "kharif": (
            ["Rice (paddy)", "Maize", "Kidney bean", "Kidney beans", "Finger millet"],
            ["rice", "maize", "kidneybeans"],
            ["Finger millet"],
        ),
        "rabi": (
            ["Wheat", "Chickpea", "Lentil", "Potato", "Barley"],
            ["chickpea", "lentil", "potato"],
            ["Wheat", "Barley"],
        ),
        "zaid": (
            ["Watermelon", "Muskmelon", "Maize", "Green gram"],
            ["watermelon", "muskmelon", "maize"],
            [],
        ),
    },
}

MODEL_CROP_LABELS = {
    "apple", "banana", "blackgram", "chickpea", "coconut", "coffee", "cotton",
    "grapes", "jute", "kidneybeans", "lentil", "maize", "mango", "mothbeans",
    "mungbean", "muskmelon", "orange", "papaya", "pigeonpeas", "pomegranate",
    "rice", "watermelon",
}

REGIONAL_CROP_MODEL_ALIASES = {
    "rice (paddy)": "rice",
    "boro rice": "rice",
    "pigeon pea": "pigeonpeas",
    "black gram": "blackgram",
    "green gram": "mungbean",
    "moth bean": "mothbeans",
    "kidney bean": "kidneybeans",
    "kidney beans": "kidneybeans",
}


def _to_model_crop_name(crop_name: str) -> str | None:
    normalized_name = crop_name.lower()
    model_name = REGIONAL_CROP_MODEL_ALIASES.get(normalized_name, normalized_name)
    return model_name if model_name in MODEL_CROP_LABELS else None


REGIONAL_SEASONAL_CROP_PROFILES = {
    (state, season): {
        "region": state_data["region"],
        "season": season,
        "common_crops": crops[0],
        "priority_crops": crops[1],
        "not_modelled_crops": [
            crop_name for crop_name in crops[0]
            if _to_model_crop_name(crop_name) is None
        ],
    }
    for state, state_data in _REGIONAL_CROP_DATA.items()
    for season, crops in state_data.items()
    if season != "region"
}


def get_regional_seasonal_crop_profile(location: str, season: str) -> dict | None:
    normalized_location = re.sub(
        r"[^a-z0-9]+", " ", location.lower()
    ).strip()
    region = next(
        (
            state for state, aliases in REGION_STATE_ALIASES.items()
            if any(
                f" {re.sub(r'[^a-z0-9]+', ' ', alias.lower()).strip()} "
                in f" {normalized_location} "
                for alias in aliases
            )
        ),
        None,
    )
    return REGIONAL_SEASONAL_CROP_PROFILES.get((region, season.lower()))


# ─── Download Dataset ───────────────────────────────────────
def download_dataset():
    if not os.path.exists(DATA_PATH):
        print("Downloading crop dataset...")
        url = "https://raw.githubusercontent.com/dsrscientist/dataset1/master/Crop_recommendation.csv"
        try:
            urllib.request.urlretrieve(url, DATA_PATH)
            print("Dataset downloaded!")
        except Exception as e:
            print(f"Download failed: {e}")

# ─── Train Model ────────────────────────────────────────────
def train_model():
    if pd is None or RandomForestClassifier is None or train_test_split is None or LabelEncoder is None:
        raise RuntimeError("Crop recommendation model dependencies are not installed.")

    print("Training crop recommendation model...")
    df = pd.read_csv(DATA_PATH)

    X = df[["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]]
    y = df["label"]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        max_depth=10
    )
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    print(f"Model trained! Accuracy: {accuracy * 100:.2f}%")

    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)
    print("Model saved!")

    return model, le

# ─── Load or Train ──────────────────────────────────────────
def get_crop_model():
    if joblib is None or np is None:
        return None, None

    download_dataset()
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
        model = joblib.load(MODEL_PATH)
        le = joblib.load(ENCODER_PATH)
        print("Crop model loaded from disk")
    else:
        model, le = train_model()
    return model, le

try:
    crop_model, label_encoder = get_crop_model()
except Exception as exc:
    print(f"Crop model unavailable: {exc}")
    crop_model = None
    label_encoder = None

# ─── Recommend Crop ─────────────────────────────────────────
# ─── Recommend Crop ─────────────────────────────────────────
async def recommend_crop(
    location: str | None = None,
    season: str = "kharif",
    latitude: float | None = None,
    longitude: float | None = None,
    irrigation: str | None = None,
    nitrogen: float | None = None,
    phosphorous: float | None = None,
    potassium: float | None = None,
    ph: float | None = None,
    temperature: float | None = None,
    humidity: float | None = None,
    rainfall: float | None = None,
) -> dict:
    try:
        geo_context = None
        soil_profile_data = None
        resolved_location_name = location or "Selected Farm Location"

        # 1. Coordinate-based Geospatial Resolution
        if latitude is not None and longitude is not None:
            geo_context = resolve_coordinates(latitude, longitude)
            resolved_location_name = geo_context.get("formatted_address") or f"{geo_context.get('district')}, {geo_context.get('state')}"
            soil_profile_data = get_soil_profile_for_coordinates(
                latitude, longitude, geo_context.get("district"), geo_context.get("state")
            )
            location_for_rules = geo_context.get("district") or geo_context.get("state") or resolved_location_name
        else:
            location_for_rules = location or "default"

        regional_profile = get_regional_seasonal_crop_profile(location_for_rules, season)

        if crop_model is None or label_encoder is None or np is None:
            return {
                "success": False,
                "error": "Crop recommendation model dependencies are unavailable."
            }

        # 2. Resolve Soil Data & Track Provenance
        if soil_profile_data:
            soil = {
                "soil_type": soil_profile_data["soil_classification"]["soil_type"],
                "N": next((p["value"] for p in soil_profile_data["properties"] if p["property"] == "nitrogen"), 50),
                "P": next((p["value"] for p in soil_profile_data["properties"] if p["property"] == "phosphorous"), 25),
                "K": next((p["value"] for p in soil_profile_data["properties"] if p["property"] == "potassium"), 30),
                "ph": next((p["value"] for p in soil_profile_data["properties"] if p["property"] == "ph"), 6.8),
            }
            soil_source = "isric-soilgrids-250m"
        else:
            soil = dict(get_soil_data(location_for_rules))
            soil_source = get_soil_data_source(location_for_rules)

        # Apply explicit user laboratory/sensor overrides
        soil_overrides = {
            "N": nitrogen,
            "P": phosphorous,
            "K": potassium,
            "ph": ph,
        }
        supplied_soil_values = {
            key: value for key, value in soil_overrides.items()
            if value is not None
        }
        soil.update(supplied_soil_values)

        if len(supplied_soil_values) == len(soil_overrides):
            data_quality = "verified-laboratory"
            soil_source = "user-provided-laboratory"
        elif supplied_soil_values:
            data_quality = "mixed-estimates"
            soil_source = "mixed-user-provided"
        else:
            data_quality = "geographic-grid-estimate"

        # 3. Resolve Seasonal Rainfall & Weather
        seasonal_rainfall = get_rainfall(season)
        resolved_rainfall = rainfall if rainfall is not None else seasonal_rainfall
        rainfall_source = "user-provided" if rainfall is not None else "seasonal-estimate"

        resolved_temperature = 28.0
        resolved_humidity = 65.0
        weather_source = "default-values"
        weather_error = None

        if latitude is not None and longitude is not None:
            coord_weather = get_weather_for_coordinates(latitude, longitude)
            if coord_weather.get("success"):
                resolved_temperature = coord_weather["temperature"]
                resolved_humidity = coord_weather["humidity"]
                weather_source = coord_weather["source"]
        elif temperature is None or humidity is None:
            weather_result = await get_weather(location_for_rules)
            if weather_result.get("success"):
                w = weather_result["weather"]
                resolved_temperature = float(w["temperature"])
                resolved_humidity = float(w["humidity"])
                weather_source = w.get("source", "openweathermap")
            else:
                weather_error = weather_result.get("error")

        if temperature is not None:
            resolved_temperature = temperature
            weather_source = "user-provided"
        if humidity is not None:
            resolved_humidity = humidity
            weather_source = "user-provided"

        # 4. Machine Learning Multi-Class Inference (Random Forest)
        feature_cols = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
        raw_vals = [[
            float(soil["N"]), float(soil["P"]), float(soil["K"]),
            float(resolved_temperature), float(resolved_humidity),
            float(soil["ph"]), float(resolved_rainfall)
        ]]
        if pd is not None:
            input_data = pd.DataFrame(raw_vals, columns=feature_cols)
        else:
            input_data = np.array(raw_vals)
        probabilities = crop_model.predict_proba(input_data)[0]

        # 5. Composite Agronomic Scoring & Explainability
        # Evaluate all crop classes and rank by combined suitability + ML score
        candidate_evaluations = []
        for idx, prob in enumerate(probabilities):
            crop_name = label_encoder.inverse_transform([idx])[0]
            ml_confidence = round(prob * 100, 2)

            eligibility = assess_crop_eligibility(
                crop=crop_name,
                season=season,
                temperature=resolved_temperature,
                rainfall=resolved_rainfall,
                soil_ph=soil["ph"],
                soil_type=soil["soil_type"],
                irrigation=irrigation,
            )

            # Composite suitability calculation:
            # Combines model confidence (0-100) with agronomic penalty reduction
            suitability_score = max(0, min(100, round(ml_confidence * 0.65 + (100 - eligibility["suitability_penalty"]) * 0.35, 1)))

            # If crop is also a recognized priority regional crop, add a small agronomic bonus
            is_priority = False
            if regional_profile and crop_name.lower() in [c.lower() for c in regional_profile.get("priority_crops", [])]:
                suitability_score = min(100, suitability_score + 8)
                is_priority = True
                eligibility["reasons"].insert(0, f"Recognized high-yield priority crop for {regional_profile['region']} ({season.capitalize()}).")

            candidate_evaluations.append({
                "crop": crop_name,
                "display_name": eligibility.get("display_name", crop_name.capitalize()),
                "ml_confidence": ml_confidence,
                "suitability_score": suitability_score,
                "water_demand": eligibility.get("water_demand", "medium"),
                "eligible": eligibility["eligible"],
                "reasons": eligibility["reasons"],
                "warnings": eligibility["warnings"],
                "description": CROP_INFO.get(crop_name.lower(), eligibility.get("description", "Suitable crop for current parameters.")),
                "is_priority_regional": is_priority,
            })

        # Rank candidates primarily by suitability score, then ML confidence
        candidate_evaluations.sort(key=lambda x: (x["eligible"], x["suitability_score"], x["ml_confidence"]), reverse=True)
        top_recommendations = candidate_evaluations[:3]

        # Data provenance notes and missing measurement warnings
        limitations = [
            "Soil properties reflect 250m geographic grid-cell predictions (ISRIC SoilGrids & Regional Survey), not an on-site laboratory test.",
            "Plant-available Phosphorus (P) and Potassium (K) are estimated from regional agricultural averages; test your field soil before chemical fertilizer application."
        ]
        if data_quality == "verified-laboratory":
            limitations = ["Laboratory soil test values supplied. Agronomic recommendation is high confidence."]

        return {
            "success": True,
            "location": resolved_location_name,
            "coordinates": {"latitude": latitude, "longitude": longitude} if (latitude and longitude) else None,
            "season": season,
            "irrigation": irrigation or "rainfed",
            "soil_type": soil["soil_type"],
            "data_quality": data_quality,
            "top_recommendation": top_recommendations[0]["crop"],
            "confidence": top_recommendations[0]["ml_confidence"],
            "suitability_score": top_recommendations[0]["suitability_score"],
            "recommendations": top_recommendations,
            "recommendation_method": "geospatial-soil-climate-model",
            "soil_profile": soil_profile_data,
            "soil_source": soil_source,
            "weather_source": weather_source,
            "weather_error": weather_error,
            "rainfall_source": rainfall_source,
            "weather_inputs": {
                "temperature": resolved_temperature,
                "humidity": resolved_humidity,
                "rainfall": resolved_rainfall,
            },
            "soil_summary": {
                "nitrogen": soil["N"],
                "phosphorous": soil["P"],
                "potassium": soil["K"],
                "ph": soil["ph"],
            },
            "limitations_and_warnings": limitations,
            "model_version": "RandomForest-v1.0 (100 trees, 10 depth, 22 classes)",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
