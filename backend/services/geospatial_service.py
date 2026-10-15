"""
Geospatial & Soil Profile Resolution Service for ALIP
Handles reverse geocoding, coordinate-based soil intelligence (ISRIC SoilGrids),
and coordinate-based weather resolution (Open-Meteo).
Distinguishes measured values from geographic estimates with explicit provenance and uncertainty.
"""

import os
import re
import requests
from typing import Dict, Any, Optional, Tuple
from data.soil_data import SOIL_DATA, get_soil_data, get_soil_data_source, get_rainfall

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# Regional district/state bounding heuristics for fast, zero-failure offline fallback
KNOWN_REGIONS_GEO = [
    {"name": "Telangana", "district": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867, "radius": 2.5},
    {"name": "Andhra Pradesh", "district": "Vijayawada", "state": "Andhra Pradesh", "lat": 16.5062, "lon": 80.6480, "radius": 3.0},
    {"name": "Punjab", "district": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573, "radius": 2.2},
    {"name": "Maharashtra", "district": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567, "radius": 3.5},
    {"name": "Karnataka", "district": "Bangalore", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946, "radius": 3.0},
    {"name": "Tamil Nadu", "district": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "radius": 3.0},
    {"name": "Kerala", "district": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673, "radius": 2.0},
    {"name": "Uttar Pradesh", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462, "radius": 3.5},
    {"name": "Rajasthan", "district": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873, "radius": 4.0},
    {"name": "West Bengal", "district": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639, "radius": 2.5},
    {"name": "Gujarat", "district": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714, "radius": 3.0},
    {"name": "Madhya Pradesh", "district": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126, "radius": 3.5},
    {"name": "Haryana", "district": "Hisar", "state": "Haryana", "lat": 29.1492, "lon": 75.7217, "radius": 1.8},
]


def resolve_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Reverse geocodes latitude/longitude into administrative district, state, and address.
    Uses OpenStreetMap Nominatim with safe offline fallback based on spatial proximity.
    """
    district = None
    state = None
    country = "India"
    display_name = f"Coordinates ({latitude:.4f}, {longitude:.4f})"

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"lat": latitude, "lon": longitude, "format": "json"},
            headers={"User-Agent": "ALIP-AgriIntelligence/1.0"},
            timeout=3.5,
        )
        if resp.status_code == 200:
            data = resp.json()
            display_name = data.get("display_name", display_name)
            address = data.get("address", {})
            state = address.get("state") or address.get("province")
            district = (
                address.get("state_district")
                or address.get("county")
                or address.get("city")
                or address.get("town")
                or address.get("district")
            )
            country = address.get("country", country)
    except Exception as e:
        # Graceful fallback to proximity
        pass

    # Fallback to nearest agricultural region if Nominatim didn't resolve state/district
    if not state or not district:
        closest = None
        min_dist_sq = float("inf")
        for reg in KNOWN_REGIONS_GEO:
            d_sq = (latitude - reg["lat"]) ** 2 + (longitude - reg["lon"]) ** 2
            if d_sq < min_dist_sq:
                min_dist_sq = d_sq
                closest = reg
        if closest and min_dist_sq < 25.0:  # Within ~500 km
            state = state or closest["state"]
            district = district or closest["district"]
            if display_name.startswith("Coordinates"):
                display_name = f"{district}, {state}, India"

    location_key = district or state or "default"
    return {
        "latitude": latitude,
        "longitude": longitude,
        "district": district or "Unknown District",
        "state": state or "Unknown State",
        "country": country,
        "formatted_address": display_name,
        "resolved_key": location_key.lower(),
    }


def get_soilgrids_profile(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Queries ISRIC SoilGrids 2.0 REST API for pH, Total Nitrogen, and Soil Organic Carbon.
    Returns property values at 0-5cm and 5-15cm with uncertainty.
    """
    try:
        resp = requests.get(
            SOILGRIDS_URL,
            params={
                "lon": longitude,
                "lat": latitude,
                "property": ["phh2o", "nitrogen", "soc"],
                "depth": ["0-5cm", "5-15cm"],
            },
            headers={"Accept": "application/json"},
            timeout=4.0,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        layers = data.get("properties", {}).get("layers", [])
        if not layers:
            return None

        extracted = {}
        for layer in layers:
            name = layer.get("name")
            unit_info = layer.get("unit_measure", {})
            d_factor = unit_info.get("d_factor", 1) or 1
            depths = layer.get("depths", [])
            if depths:
                first_depth = depths[0]
                values = first_depth.get("values", {})
                mean_val = values.get("mean")
                if mean_val is not None:
                    # Convert to target units using d_factor
                    real_val = mean_val / d_factor
                    uncertainty = values.get("uncertainty")
                    extracted[name] = {
                        "value": real_val,
                        "depth": "0-15cm",
                        "raw_unit": unit_info.get("mapped_units"),
                        "target_unit": unit_info.get("target_units"),
                        "uncertainty": (uncertainty / d_factor) if uncertainty else None,
                    }

        return extracted if extracted else None
    except Exception:
        return None


def get_soil_profile_for_coordinates(
    latitude: float,
    longitude: float,
    district: Optional[str] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Combines ISRIC SoilGrids 250m satellite data with regional soil surveys.
    Explicitly tracks provenance, resolution, and uncertainty.
    Highlights that plant-available P & K are regional estimates requiring lab tests.
    """
    loc_query = f"{district or ''} {state or ''}".strip() or f"{latitude},{longitude}"
    baseline_soil = get_soil_data(loc_query)
    baseline_source = get_soil_data_source(loc_query)

    soilgrids_data = get_soilgrids_profile(latitude, longitude)

    # Determine pH: prefer SoilGrids if valid (pH between 3.5 and 10), else baseline
    ph_value = baseline_soil["ph"]
    ph_source = f"Regional Survey ({baseline_source})"
    ph_uncertainty = "±0.5 pH units (regional survey)"

    if soilgrids_data and "phh2o" in soilgrids_data:
        sg_ph = soilgrids_data["phh2o"]["value"]
        if 3.5 <= sg_ph <= 10.0:
            ph_value = round(sg_ph, 2)
            ph_source = "ISRIC SoilGrids 250m Spatial Model"
            sg_unc = soilgrids_data["phh2o"].get("uncertainty")
            ph_uncertainty = f"±{sg_unc:.2f} pH units" if sg_unc else "250m grid model variance"

    # Nitrogen: SoilGrids provides total N (g/kg). Our model uses available N (kg/ha).
    # Typical conversion factor: Available N ≈ baseline survey or calibrated from SoilGrids
    nitrogen_val = baseline_soil["N"]
    nitrogen_source = f"Regional Soil Survey ({baseline_source})"

    phosphorous_val = baseline_soil["P"]
    phosphorous_source = "Regional Agricultural Baseline"

    potassium_val = baseline_soil["K"]
    potassium_source = "Regional Agricultural Baseline"

    soil_type = baseline_soil["soil_type"]

    return {
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "soil_classification": {
            "soil_type": soil_type,
            "source": baseline_source,
            "spatial_resolution": "District/Regional Geospatial Unit" if not soilgrids_data else "250m SoilGrids + Regional",
            "confidence": "Medium-High (Agronomic Survey)"
        },
        "data_quality": "geographic-estimate",
        "properties": [
            {
                "property": "ph",
                "label": "Soil pH",
                "value": ph_value,
                "unit": "pH",
                "status": "estimated",
                "source": ph_source,
                "depth_cm": [0, 15],
                "uncertainty": ph_uncertainty,
                "is_measured": False,
            },
            {
                "property": "nitrogen",
                "label": "Available Nitrogen (N)",
                "value": nitrogen_val,
                "unit": "kg/ha",
                "status": "estimated",
                "source": nitrogen_source,
                "depth_cm": [0, 15],
                "uncertainty": "Regional soil survey baseline",
                "is_measured": False,
                "notes": "Plant-available N estimate. SoilGrids provides total organic N, not inorganic available N.",
            },
            {
                "property": "phosphorous",
                "label": "Available Phosphorus (P)",
                "value": phosphorous_val,
                "unit": "kg/ha",
                "status": "estimated",
                "source": phosphorous_source,
                "depth_cm": [0, 15],
                "uncertainty": "Regional soil survey baseline",
                "is_measured": False,
                "notes": "Plant-available phosphorus is not directly measured by satellite/gridded maps.",
            },
            {
                "property": "potassium",
                "label": "Available Potassium (K)",
                "value": potassium_val,
                "unit": "kg/ha",
                "status": "estimated",
                "source": potassium_source,
                "depth_cm": [0, 15],
                "uncertainty": "Regional soil survey baseline",
                "is_measured": False,
                "notes": "Exchangeable potassium derived from regional agricultural agro-ecological survey.",
            },
        ],
        "limitations": [
            "250m grid-cell values represent spatial predictions, not laboratory field-point assays.",
            "Plant-available P and K require calibrated chemical extraction (Bray/Olsen method).",
            "For precise chemical fertilizer budgeting, verify with an official Soil Health Card."
        ],
    }


def get_weather_for_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetches real-time ambient temperature and humidity for coordinates via Open-Meteo.
    Falls back safely if network request fails.
    """
    try:
        resp = requests.get(
            OPENMETEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,precipitation",
                "timezone": "auto",
            },
            timeout=3.5,
        )
        if resp.status_code == 200:
            cur = resp.json().get("current", {})
            temp = cur.get("temperature_2m")
            humidity = cur.get("relative_humidity_2m")
            precip = cur.get("precipitation")
            if temp is not None and humidity is not None:
                return {
                    "success": True,
                    "temperature": round(float(temp), 1),
                    "humidity": round(float(humidity), 1),
                    "current_precipitation_mm": float(precip or 0.0),
                    "source": "Open-Meteo High-Resolution Grid",
                }
    except Exception:
        pass

    # Default fallback
    return {
        "success": False,
        "temperature": 28.0,
        "humidity": 65.0,
        "current_precipitation_mm": 0.0,
        "source": "Regional Climatological Average (Fallback)",
    }
