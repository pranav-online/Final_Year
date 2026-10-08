import os
from typing import Any, Dict

import joblib
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

WEATHER_MODEL_PATH = "data/weather_model.pkl"


def get_weather_model():
    if os.path.exists(WEATHER_MODEL_PATH):
        model = joblib.load(WEATHER_MODEL_PATH)
        print("✅ Weather ML model loaded!")
        return model
    print("⚠️ Weather model not found — run train_weather_model.py")
    return None


weather_model = get_weather_model()

ADVISORY_MESSAGES = {
    "high_temp": {
        "message": "🌡️ High temperature alert! Irrigate crops early morning or late evening.",
        "severity": "high",
    },
    "low_temp": {
        "message": "🥶 Low temperature warning! Protect crops from frost damage.",
        "severity": "high",
    },
    "fungal_risk": {
        "message": "🍄 High fungal disease risk! Inspect crops and apply preventive fungicide.",
        "severity": "medium",
    },
    "high_wind": {
        "message": "💨 Strong winds! Avoid pesticide and fertilizer spraying today.",
        "severity": "medium",
    },
    "heavy_rain": {
        "message": "🌧️ Heavy rainfall! Avoid spraying operations. Check field drainage.",
        "severity": "high",
    },
    "moderate_rain": {
        "message": "🌦️ Moderate rainfall. Reduce irrigation today to conserve water.",
        "severity": "low",
    },
    "normal": {
        "message": "✅ Weather conditions are suitable for standard farming operations.",
        "severity": "low",
    },
}


def _normalize_location(location: str) -> str:
    return " ".join((location or "").strip().split()).lower()


def _demo_weather_for_location(location: str) -> Dict[str, Any]:
    city_key = _normalize_location(location)
    profiles = {
        "hyderabad": {"temperature": 31, "humidity": 68, "wind_speed": 12, "rainfall": 1.8, "condition": "partly cloudy", "location": "Hyderabad, IN"},
        "chennai": {"temperature": 32, "humidity": 70, "wind_speed": 15, "rainfall": 3.4, "condition": "misty", "location": "Chennai, IN"},
        "mumbai": {"temperature": 29, "humidity": 82, "wind_speed": 18, "rainfall": 8.6, "condition": "moderate rain", "location": "Mumbai, IN"},
        "delhi": {"temperature": 34, "humidity": 46, "wind_speed": 11, "rainfall": 0.2, "condition": "clear sky", "location": "Delhi, IN"},
        "bangalore": {"temperature": 27, "humidity": 60, "wind_speed": 9, "rainfall": 2.1, "condition": "scattered clouds", "location": "Bengaluru, IN"},
        "visakhapatnam": {"temperature": 30, "humidity": 74, "wind_speed": 14, "rainfall": 5.2, "condition": "light rain", "location": "Visakhapatnam, IN"},
        "coimbatore": {"temperature": 29, "humidity": 62, "wind_speed": 10, "rainfall": 1.4, "condition": "clear sky", "location": "Coimbatore, IN"},
    }

    if city_key in profiles:
        profile = profiles[city_key]
        return {
            "location": profile["location"],
            "temperature": profile["temperature"],
            "feels_like": profile["temperature"] + 1,
            "humidity": profile["humidity"],
            "wind_speed": profile["wind_speed"],
            "condition": profile["condition"],
            "rainfall": profile["rainfall"],
            "pressure": 1012,
            "visibility": 8.5,
            "source": "demo-fallback",
        }

    checksum = sum(ord(ch) for ch in city_key) % 100
    location_name = " ".join(part.capitalize() for part in city_key.split()) if city_key else "Your city"
    return {
        "location": location_name,
        "temperature": 24 + (checksum % 16),
        "feels_like": 25 + (checksum % 12),
        "humidity": 40 + (checksum % 39),
        "wind_speed": 8 + (checksum % 17),
        "condition": "partly cloudy" if checksum % 2 == 0 else "clear sky",
        "rainfall": round((checksum % 8) * 0.9, 1),
        "pressure": 1008 + (checksum % 12),
        "visibility": round(6 + (checksum % 5) * 0.8, 1),
        "source": "demo-fallback",
    }


def ml_advisory(temp, humidity, wind_speed, rainfall):
    if weather_model is None:
        return None
    try:
        features = np.array([[temp, humidity, wind_speed, rainfall]])
        prediction = weather_model.predict(features)[0]
        proba = weather_model.predict_proba(features)[0]
        confidence = round(max(proba) * 100, 2)
        advisory = ADVISORY_MESSAGES.get(prediction, ADVISORY_MESSAGES["normal"])
        return {
            "category": prediction,
            "message": advisory["message"],
            "severity": advisory["severity"],
            "confidence": confidence,
        }
    except Exception as exc:
        print(f"ML advisory error: {exc}")
        return None


def _build_advisories(weather_data: Dict[str, Any]) -> list:
    temp = float(weather_data["temperature"])
    humidity = float(weather_data["humidity"])
    wind_speed = float(weather_data["wind_speed"])
    rainfall = float(weather_data["rainfall"])

    ml_result = ml_advisory(temp, humidity, wind_speed, rainfall)
    advisories = []

    if ml_result:
        advisories.append({
            "source": "ML Model",
            "category": ml_result["category"],
            "message": ml_result["message"],
            "severity": ml_result["severity"],
            "confidence": ml_result["confidence"],
        })

    if not advisories:
        advisories.append({
            "source": "Rules",
            "category": "normal",
            "message": ADVISORY_MESSAGES["normal"]["message"],
            "severity": ADVISORY_MESSAGES["normal"]["severity"],
            "confidence": 85,
        })

    return advisories


async def get_weather(location: str) -> dict:
    query = (location or "").strip()
    if not query:
        return {"success": False, "error": "Please provide a city name."}

    if API_KEY:
        try:
            params = {"q": query, "appid": API_KEY, "units": "metric"}
            response = requests.get(BASE_URL, params=params, timeout=10)
            data = response.json()

            if response.status_code == 200:
                weather_data = {
                    "location": data["name"] + ", " + data["sys"]["country"],
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": round(data["wind"]["speed"] * 3.6, 3),
                    "condition": data["weather"][0]["description"],
                    "rainfall": data.get("rain", {}).get("1h", 0),
                    "pressure": data["main"]["pressure"],
                    "visibility": data.get("visibility", 0) / 1000,
                    "source": "openweathermap",
                }
                advisories = _build_advisories(weather_data)
                return {
                    "success": True,
                    "weather": weather_data,
                    "advisories": advisories,
                    "total_advisories": len(advisories),
                    "advisory_method": "OpenWeatherMap + Decision Tree Classifier",
                }

            if response.status_code in (401, 403):
                print("Weather API key invalid or missing; falling back to demo weather data.")
            elif response.status_code == 404:
                print(f"Location not found in OpenWeatherMap: {query}; using demo weather fallback.")
        except Exception as exc:
            print(f"Weather API request error for '{query}': {exc}")

    weather_data = _demo_weather_for_location(query)
    advisories = _build_advisories(weather_data)
    return {
        "success": True,
        "weather": weather_data,
        "advisories": advisories,
        "total_advisories": len(advisories),
        "advisory_method": "Demo fallback + Decision Tree Classifier",
    }
