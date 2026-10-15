import os
import json
import datetime
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

# ─── Environment & API Keys ────────────────────────────────────────
# OpenWeatherMap API Key or WeatherAPI.com Key
API_KEY = os.getenv("WEATHER_API_KEY")
OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

# Gemini AI configuration for smart agronomic plan generation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

WEATHER_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "weather_model.pkl")


def get_weather_model():
    if os.path.exists(WEATHER_MODEL_PATH):
        try:
            model = joblib.load(WEATHER_MODEL_PATH)
            print("✅ Weather ML model loaded!")
            return model
        except Exception as e:
            print(f"⚠️ Error loading weather model: {e}")
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


def _generate_7day_forecast_fallback(base_weather: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate realistic 7-day forecast series matching the regional climate."""
    t0 = float(base_weather.get("temperature", 28))
    h0 = float(base_weather.get("humidity", 65))
    w0 = float(base_weather.get("wind_speed", 12))
    r0 = float(base_weather.get("rainfall", 0))

    days = []
    today = datetime.date.today()

    patterns = [
        {"d_temp": 0, "d_hum": 0, "d_wind": 0, "rain": r0, "cond": base_weather.get("condition", "Partly Cloudy")},
        {"d_temp": 1.2, "d_hum": -4, "d_wind": -2, "rain": max(0, r0 * 0.4), "cond": "Sunny / Clear Sky"},
        {"d_temp": -0.8, "d_hum": 8, "d_wind": 3, "rain": r0 + 2.5 if r0 > 0 else 1.8, "cond": "Scattered Showers" if r0 > 0 else "Partly Cloudy"},
        {"d_temp": -1.5, "d_hum": 12, "d_wind": 4, "rain": max(0, r0 + 4.2), "cond": "Moderate Rain" if r0 > 0 else "Cloudy"},
        {"d_temp": 0.5, "d_hum": -6, "d_wind": -1, "rain": 0.2, "cond": "Passing Clouds"},
        {"d_temp": 1.8, "d_hum": -10, "d_wind": -3, "rain": 0.0, "cond": "Bright Sunshine"},
        {"d_temp": 1.0, "d_hum": -5, "d_wind": 1, "rain": 0.0, "cond": "Clear & Warm"},
    ]

    for i, p in enumerate(patterns):
        cur_date = today + datetime.timedelta(days=i)
        day_temp = round(t0 + p["d_temp"], 1)
        day_hum = min(98, max(30, round(h0 + p["d_hum"])))
        day_wind = max(4, round(w0 + p["d_wind"], 1))
        day_rain = round(p["rain"], 1)

        rain_prob = 0
        if day_rain > 5:
            rain_prob = 85
        elif day_rain > 1:
            rain_prob = 60
        elif day_rain > 0:
            rain_prob = 35
        elif day_hum > 75:
            rain_prob = 25
        else:
            rain_prob = 10

        day_name = "Today" if i == 0 else "Tomorrow" if i == 1 else cur_date.strftime("%A")

        days.append({
            "day_index": i + 1,
            "date": cur_date.strftime("%b %d"),
            "day_name": f"Day {i + 1} ({day_name})",
            "temperature": day_temp,
            "min_temp": round(day_temp - 5, 1),
            "max_temp": round(day_temp + 3, 1),
            "humidity": day_hum,
            "wind_speed": day_wind,
            "rainfall": day_rain,
            "rain_probability": rain_prob,
            "condition": p["cond"],
        })

    return days


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
        "guntur": {"temperature": 33, "humidity": 65, "wind_speed": 11, "rainfall": 0.8, "condition": "partly cloudy", "location": "Guntur, IN"},
        "warangal": {"temperature": 32, "humidity": 62, "wind_speed": 10, "rainfall": 1.2, "condition": "clear sky", "location": "Warangal, IN"},
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


# ─── 1-Week Disease & Weather Action Plan Generator ─────────────────
def _generate_rule_based_weekly_plan(
    weather_data: Dict[str, Any],
    forecast: List[Dict[str, Any]],
    disease: Optional[str],
    severity: Optional[str]
) -> Dict[str, Any]:
    """Generates an intelligent agronomic 7-day disease management plan."""
    disease_name = (disease or "General Crop Health / Preventative Management").strip()
    sev = (severity or "medium").lower()

    # Find optimal spray days (low wind < 15km/h, low rain < 1mm, humidity < 80%)
    spray_days = []
    caution_days = []
    avoid_days = []

    for f in forecast:
        day_idx = f["day_index"]
        if f["rainfall"] > 2.0 or f["wind_speed"] > 18 or f["rain_probability"] > 60:
            avoid_days.append(f"Day {day_idx}")
        elif f["rainfall"] > 0.5 or f["wind_speed"] > 13 or f["humidity"] > 80:
            caution_days.append(f"Day {day_idx}")
        else:
            spray_days.append(f"Day {day_idx}")

    best_spray = ", ".join(spray_days[:2]) if spray_days else "Early morning on Day 1 (if rain holds)"

    daily_actions = []
    action_templates = [
        {
            "focus": "Immediate Intervention & First Spray",
            "title": "Initial Targeted Treatment & Pruning",
            "desc": f"Apply primary fungicide/bactericide for {disease_name}. Spray between 6:00 AM - 8:30 AM before temperatures rise. Disinfect pruning tools with 70% alcohol.",
            "precautions": "Ensure complete canopy coverage; do not spray if wind exceeds 15 km/h."
        },
        {
            "focus": "Soil Drainage & Moisture Audit",
            "title": "Field Drainage & Root Zone Inspection",
            "desc": "Check furrow drainage to prevent waterlogging around roots. High soil moisture exacerbates fungal spread.",
            "precautions": "Avoid overhead sprinkler irrigation; switch exclusively to drip or furrow watering."
        },
        {
            "focus": "Canopy Aeration & Leaf Removal",
            "title": "Sanitation & Infected Foliage Pruning",
            "desc": "Remove and safely burn or bag necrotic leaves from the lower 20% of the plant canopy to improve airflow.",
            "precautions": "Do not compost infected plant debris near active fields."
        },
        {
            "focus": "Biological / Organic Barrier",
            "title": "Secondary Bio-Agent or Neem Barrier",
            "desc": "Apply Trichoderma viride or 0.5% Cold-Pressed Neem Oil to create a protective biological shield against spore germination.",
            "precautions": "Ensure foliage is dry before applying organic oils to avoid leaf scorch."
        },
        {
            "focus": "Disease Boundary & Progress Scouting",
            "title": "Mid-Week Disease Scouting & Audit",
            "desc": f"Inspect 15-20 random plants across the field. Check new leaf flushes to verify if {disease_name} lesion expansion has halted.",
            "precautions": "Walk fields during dry afternoon hours to minimize accidental mechanical transmission of spores."
        },
        {
            "focus": "Foliar Nutrition & Plant Immunity",
            "title": "Immunity Booster & Micronutrient Spray",
            "desc": "Spray Potassium Phosphite or balanced micronutrients (Zinc + Boron) to stimulate plant systemic acquired resistance (SAR).",
            "precautions": "Do not mix micronutrients with high-alkaline copper fungicides."
        },
        {
            "focus": "Weekly Assessment & Maintenance",
            "title": "7-Day Recovery Audit & Next Steps",
            "desc": f"Conduct final week-1 recovery audit. If {disease_name} symptoms persist above 10% threshold, prepare a secondary rotation chemical.",
            "precautions": "Rotate chemical active ingredients (FRAC group) to avoid pathogen resistance."
        },
    ]

    for i, f in enumerate(forecast):
        t = action_templates[i % len(action_templates)]
        day_rain = f["rainfall"]
        day_wind = f["wind_speed"]
        day_hum = f["humidity"]

        if day_rain > 2.0 or day_wind > 18 or f["rain_probability"] > 60:
            spray_status = "avoid"
            spray_label = "❌ Avoid Spraying (Rain / High Wind)"
            custom_desc = f"Rain ({day_rain}mm) or wind ({day_wind} km/h) will cause chemical wash-off and drift. Focus today on: {t['title']} (indoor/drainage work)."
        elif day_rain > 0.5 or day_wind > 13 or day_hum > 80:
            spray_status = "caution"
            spray_label = "⚠️ Spray with Sticker / Early AM Only"
            custom_desc = f"Moderate moisture/wind ({day_wind} km/h). {t['desc']} Add a non-ionic wetting sticker if light rain is possible."
        else:
            spray_status = "optimal"
            spray_label = "✅ Optimal Spray Window"
            custom_desc = f"Excellent weather conditions ({f['temperature']}°C, wind {day_wind} km/h). {t['desc']}"

        daily_actions.append({
            "day_number": f["day_index"],
            "day_name": f["day_name"],
            "date": f["date"],
            "temperature": f["temperature"],
            "condition": f["condition"],
            "humidity": day_hum,
            "wind_speed": day_wind,
            "rainfall": day_rain,
            "rain_probability": f["rain_probability"],
            "spray_status": spray_status,
            "spray_label": spray_label,
            "key_focus": t["focus"],
            "action_title": t["title"],
            "action_description": custom_desc,
            "precautions": t["precautions"],
        })

    summary_msg = (
        f"7-day action plan for {disease_name} (Severity: {sev.upper()}). "
        f"Optimal application windows: {best_spray}. "
        f"Avoid outdoor spraying on {', '.join(avoid_days) if avoid_days else 'days with unexpected rainfall'}."
    )

    return {
        "disease_context": disease_name,
        "disease_severity": sev,
        "plan_summary": summary_msg,
        "best_spray_windows": best_spray,
        "irrigation_advice": "Irrigate in the early morning at root level only; strictly avoid evening overhead watering.",
        "critical_watch_days": avoid_days if avoid_days else ["Day 3", "Day 4"],
        "days": daily_actions,
        "source": "ALIP Agronomic Expert Engine",
    }


def _generate_gemini_weekly_plan(
    weather_data: Dict[str, Any],
    forecast: List[Dict[str, Any]],
    disease: str,
    severity: str
) -> Optional[Dict[str, Any]]:
    """Uses Gemini to generate an ultra-customized 7-day action plan combining weather and plant pathology."""
    if not GEMINI_API_KEY:
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        forecast_summary = "\n".join([
            f"- Day {f['day_index']} ({f['date']}, {f['condition']}): Temp {f['temperature']}°C, Humidity {f['humidity']}%, Wind {f['wind_speed']} km/h, Rain {f['rainfall']}mm (Prob: {f['rain_probability']}%)"
            for f in forecast
        ])

        prompt = f"""You are an expert agronomist and plant pathologist.
A farmer has detected: '{disease}' with severity: '{severity}'.
Location: {weather_data.get('location', 'Farm')}
Current Weather: {weather_data.get('temperature')}°C, {weather_data.get('humidity')}% humidity, {weather_data.get('condition')}

7-Day Forecast:
{forecast_summary}

Generate a concise, highly practical, day-by-day 7-day action plan for the farmer to cure and manage this disease according to the daily weather forecast.

Respond strictly in valid JSON format with this exact JSON structure:
{{
  "plan_summary": "1-2 sentence overall weekly strategy",
  "best_spray_windows": "e.g. Day 1 (Morning) and Day 5 (Late Afternoon)",
  "irrigation_advice": "specific watering recommendation",
  "critical_watch_days": ["Day X", "Day Y"],
  "days": [
    {{
      "day_number": 1,
      "spray_status": "optimal" | "caution" | "avoid",
      "spray_label": "e.g. ✅ Optimal Spray Window",
      "key_focus": "short focus tag (e.g. Fungicide Spray)",
      "action_title": "Clear action title",
      "action_description": "2-3 practical sentences of exact farming tasks for this day based on weather",
      "precautions": "Specific warning for this day"
    }}
  ]
}}
"""
        response = None
        for model_name in [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    break
            except Exception as ex:
                print(f"Gemini {model_name} plan generation error: {ex}")

        if response and response.text:
            text = response.text.strip()
            # Clean markdown JSON fences if returned
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            
            # Merge weather metrics into the days
            for idx, d in enumerate(data.get("days", [])):
                if idx < len(forecast):
                    f = forecast[idx]
                    d["day_name"] = f["day_name"]
                    d["date"] = f["date"]
                    d["temperature"] = f["temperature"]
                    d["condition"] = f["condition"]
                    d["humidity"] = f["humidity"]
                    d["wind_speed"] = f["wind_speed"]
                    d["rainfall"] = f["rainfall"]
                    d["rain_probability"] = f["rain_probability"]

            data["disease_context"] = disease
            data["disease_severity"] = severity
            data["source"] = "Gemini AI Agricultural Expert"
            return data

    except Exception as e:
        print(f"Failed to generate Gemini weekly plan: {e}")

    return None


async def get_weather(
    location: str,
    disease: Optional[str] = None,
    severity: Optional[str] = None
) -> dict:
    query = (location or "").strip()
    if not query:
        return {"success": False, "error": "Please provide a city name."}

    weather_data = None
    forecast_7days = []

    api_key = os.getenv("WEATHER_API_KEY") or API_KEY

    # 1. Try Live Weather API if key is provided
    if api_key:
        try:
            params = {"q": query, "appid": api_key, "units": "metric"}
            response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=8)
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

                # Try fetching 5-day forecast
                try:
                    f_resp = requests.get(OPENWEATHER_FORECAST_URL, params=params, timeout=8)
                    if f_resp.status_code == 200:
                        f_data = f_resp.json()
                        # Group by day
                        daily_map = {}
                        for item in f_data.get("list", []):
                            dt_txt = item.get("dt_txt", "").split(" ")[0]
                            if dt_txt not in daily_map:
                                daily_map[dt_txt] = []
                            daily_map[dt_txt].append(item)

                        today = datetime.date.today()
                        for i, (dt_str, items) in enumerate(list(daily_map.items())[:7]):
                            temps = [it["main"]["temp"] for it in items]
                            hums = [it["main"]["humidity"] for it in items]
                            winds = [it["wind"]["speed"] * 3.6 for it in items]
                            rain_sum = sum(it.get("rain", {}).get("3h", 0) for it in items)
                            cond = items[len(items) // 2]["weather"][0]["description"]

                            cur_date = today + datetime.timedelta(days=i)
                            day_name = "Today" if i == 0 else "Tomorrow" if i == 1 else cur_date.strftime("%A")

                            forecast_7days.append({
                                "day_index": i + 1,
                                "date": cur_date.strftime("%b %d"),
                                "day_name": f"Day {i + 1} ({day_name})",
                                "temperature": round(sum(temps) / len(temps), 1),
                                "min_temp": round(min(temps), 1),
                                "max_temp": round(max(temps), 1),
                                "humidity": round(sum(hums) / len(hums)),
                                "wind_speed": round(sum(winds) / len(winds), 1),
                                "rainfall": round(rain_sum, 1),
                                "rain_probability": round(min(100, rain_sum * 15 + (max(hums) - 50))),
                                "condition": cond,
                            })
                except Exception as fe:
                    print(f"OpenWeatherMap forecast error: {fe}")

            elif response.status_code in (401, 403):
                print("Weather API key invalid or unauthorized; using fallback.")
            elif response.status_code == 404:
                print(f"Location not found on OpenWeatherMap: {query}; using fallback.")
        except Exception as exc:
            print(f"Weather API request error for '{query}': {exc}")

    # 2. Fallback to demo profile if API was unavailable
    if not weather_data:
        weather_data = _demo_weather_for_location(query)

    if not forecast_7days:
        forecast_7days = _generate_7day_forecast_fallback(weather_data)

    # 3. Generate ML Advisories
    advisories = _build_advisories(weather_data)

    # 4. Generate 1-Week Disease & Weather Action Plan
    weekly_plan = None
    if disease:
        weekly_plan = _generate_gemini_weekly_plan(weather_data, forecast_7days, disease, severity or "medium")
    
    if not weekly_plan:
        weekly_plan = _generate_rule_based_weekly_plan(weather_data, forecast_7days, disease, severity or "medium")

    return {
        "success": True,
        "weather": weather_data,
        "forecast": forecast_7days,
        "advisories": advisories,
        "total_advisories": len(advisories),
        "weekly_plan": weekly_plan,
        "advisory_method": "OpenWeatherMap + Decision Tree + 7-Day Disease Action Plan",
    }
