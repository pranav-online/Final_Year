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
async def recommend_crop(
    location: str,
    season: str,
    nitrogen: float | None = None,
    phosphorous: float | None = None,
    potassium: float | None = None,
    ph: float | None = None,
    temperature: float | None = None,
    humidity: float | None = None,
    rainfall: float | None = None,
) -> dict:
    try:
        regional_profile = get_regional_seasonal_crop_profile(location, season)
        if regional_profile is None and (
            crop_model is None or label_encoder is None or np is None
        ):
            return {
                "success": False,
                "error": "Crop recommendation model dependencies are unavailable."
            }

        # Get soil data for location
        soil = dict(get_soil_data(location))
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
            soil_source = "user-provided"
        elif supplied_soil_values:
            soil_source = "mixed-user-provided"
        else:
            soil_source = get_soil_data_source(location)

        # Get rainfall for season
        seasonal_rainfall = get_rainfall(season)

        # Use live weather when available; otherwise fall back to defaults.
        resolved_temperature = None if regional_profile else 28.0
        resolved_humidity = None if regional_profile else 65.0
        weather_source = "default-values"
        weather_error = None

        if not regional_profile and (temperature is None or humidity is None):
            weather_result = await get_weather(location)
            if weather_result.get("success"):
                weather = weather_result["weather"]
                resolved_temperature = float(weather["temperature"])
                resolved_humidity = float(weather["humidity"])
                weather_source = weather.get("source", "openweathermap")
            else:
                weather_error = weather_result.get("error")

        if temperature is not None:
            resolved_temperature = temperature
        if humidity is not None:
            resolved_humidity = humidity
        if regional_profile:
            weather_source = "not-used-for-regional-guidance"
        elif temperature is not None and humidity is not None:
            weather_source = "user-provided"
        elif temperature is not None or humidity is not None:
            weather_source = "mixed-user-provided"

        resolved_rainfall = rainfall if rainfall is not None else seasonal_rainfall
        rainfall_source = (
            "user-provided" if rainfall is not None else "seasonal estimate"
        )

        if regional_profile:
            recommendations = [
                {
                    "crop": crop_name,
                    "confidence": None,
                    "recommendation_type": "regional-seasonal",
                    "description": CROP_INFO.get(
                        crop_name,
                        "Common regional crop; check local district and field suitability."
                    ),
                }
                for crop_name in regional_profile["priority_crops"]
            ]
        else:
            input_data = np.array([[
                soil["N"], soil["P"], soil["K"],
                resolved_temperature, resolved_humidity,
                soil["ph"], resolved_rainfall
            ]])
            probabilities = crop_model.predict_proba(input_data)[0]
            top_indices = np.argsort(probabilities)[::-1][:3]
            recommendations = []
            for idx in top_indices:
                crop_name = label_encoder.inverse_transform([idx])[0]
                confidence = round(probabilities[idx] * 100, 2)
                recommendations.append({
                    "crop": crop_name,
                    "confidence": confidence,
                    "recommendation_type": "model-ranked",
                    "description": CROP_INFO.get(
                        crop_name.lower(),
                        "Suitable for your conditions."
                    )
                })

        return {
            "success": True,
            "location": location,
            "season": season,
            "soil_type": soil["soil_type"],
            "top_recommendation": recommendations[0]["crop"],
            "confidence": recommendations[0]["confidence"],
            "recommendations": recommendations,
            "recommendation_method": (
                "regional-seasonal-guidance" if regional_profile else "soil-climate-model"
            ),
            "regional_seasonal_guidance": (
                {
                    "region": regional_profile["region"],
                    "season": regional_profile["season"],
                    "common_crops": regional_profile["common_crops"],
                    "not_modelled_crops": regional_profile["not_modelled_crops"],
                    "recommendation_order_note": (
                        "These are common regional-seasonal options, not a farm-specific "
                        "ranking. Choose based on district, irrigation, soil test, and local "
                        "agronomy advice."
                    ),
                }
                if regional_profile else None
            ),
            "soil_source": soil_source,
            "weather_source": weather_source,
            "weather_error": weather_error,
            "rainfall_source": rainfall_source,
            "weather_inputs": {
                "temperature": resolved_temperature,
                "humidity": resolved_humidity,
                "rainfall": resolved_rainfall
            },
            "soil_summary": {
                "nitrogen": soil["N"],
                "phosphorous": soil["P"],
                "potassium": soil["K"],
                "ph": soil["ph"]
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
