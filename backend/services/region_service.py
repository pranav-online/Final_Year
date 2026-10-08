"""
ALIP - Region Distance Intelligence Service
Calculates nearest regions for crop redistribution
using Haversine formula with Indian city coordinates
"""

import math
from typing import List, Dict

# ─── Indian Agricultural Region Database ───────────────
REGIONS = {
    "Hyderabad":   {"lat": 17.3850, "lng": 78.4867, "state": "Telangana",       "population_density": 18480, "region_type": "urban",      "primary_crops": ["rice","maize","cotton"],         "market_size": "large"},
    "Warangal":    {"lat": 17.9784, "lng": 79.5941, "state": "Telangana",       "population_density": 3100,  "region_type": "semi-urban", "primary_crops": ["rice","cotton","maize"],         "market_size": "medium"},
    "Vijayawada":  {"lat": 16.5062, "lng": 80.6480, "state": "Andhra Pradesh",  "population_density": 10100, "region_type": "urban",      "primary_crops": ["rice","sugarcane","cotton"],     "market_size": "large"},
    "Guntur":      {"lat": 16.3067, "lng": 80.4365, "state": "Andhra Pradesh",  "population_density": 4600,  "region_type": "semi-urban", "primary_crops": ["cotton","chilli","rice"],        "market_size": "medium"},
    "Nellore":     {"lat": 14.4426, "lng": 79.9865, "state": "Andhra Pradesh",  "population_density": 3050,  "region_type": "semi-urban", "primary_crops": ["rice","sugarcane"],              "market_size": "medium"},
    "Karimnagar":  {"lat": 18.4386, "lng": 79.1288, "state": "Telangana",       "population_density": 2900,  "region_type": "semi-urban", "primary_crops": ["rice","cotton","maize"],         "market_size": "medium"},
    "Nizamabad":   {"lat": 18.6725, "lng": 78.0941, "state": "Telangana",       "population_density": 2700,  "region_type": "semi-urban", "primary_crops": ["rice","maize","soybean"],        "market_size": "medium"},
    "Khammam":     {"lat": 17.2473, "lng": 80.1514, "state": "Telangana",       "population_density": 2100,  "region_type": "rural",      "primary_crops": ["rice","cotton","maize"],         "market_size": "small"},
    "Kurnool":     {"lat": 15.8281, "lng": 78.0373, "state": "Andhra Pradesh",  "population_density": 2800,  "region_type": "semi-urban", "primary_crops": ["cotton","groundnut","maize"],    "market_size": "medium"},
    "Tirupati":    {"lat": 13.6288, "lng": 79.4192, "state": "Andhra Pradesh",  "population_density": 3600,  "region_type": "semi-urban", "primary_crops": ["rice","groundnut","sugarcane"],  "market_size": "medium"},
    "Anantapur":   {"lat": 14.6819, "lng": 77.6006, "state": "Andhra Pradesh",  "population_density": 1750,  "region_type": "rural",      "primary_crops": ["groundnut","cotton","maize"],    "market_size": "small"},
    "Rajahmundry": {"lat": 17.0005, "lng": 81.8040, "state": "Andhra Pradesh",  "population_density": 3900,  "region_type": "semi-urban", "primary_crops": ["rice","sugarcane","coconut"],    "market_size": "medium"},
    "Nagpur":      {"lat": 21.1458, "lng": 79.0882, "state": "Maharashtra",     "population_density": 4700,  "region_type": "urban",      "primary_crops": ["cotton","soybean","orange"],     "market_size": "large"},
    "Pune":        {"lat": 18.5204, "lng": 73.8567, "state": "Maharashtra",     "population_density": 5600,  "region_type": "urban",      "primary_crops": ["sugarcane","wheat","grapes"],    "market_size": "large"},
    "Bangalore":   {"lat": 12.9716, "lng": 77.5946, "state": "Karnataka",       "population_density": 4378,  "region_type": "urban",      "primary_crops": ["ragi","maize","tomato"],         "market_size": "large"},
    "Chennai":     {"lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu",      "population_density": 26903, "region_type": "urban",      "primary_crops": ["rice","groundnut","sugarcane"],  "market_size": "large"},
    "Coimbatore":  {"lat": 11.0168, "lng": 76.9558, "state": "Tamil Nadu",      "population_density": 7200,  "region_type": "urban",      "primary_crops": ["cotton","maize","banana"],       "market_size": "large"},
    "Bhopal":      {"lat": 23.2599, "lng": 77.4126, "state": "Madhya Pradesh",  "population_density": 3400,  "region_type": "urban",      "primary_crops": ["wheat","soybean","rice"],        "market_size": "large"},
    "Indore":      {"lat": 22.7196, "lng": 75.8577, "state": "Madhya Pradesh",  "population_density": 5200,  "region_type": "urban",      "primary_crops": ["wheat","soybean","maize"],       "market_size": "large"},
    "Jaipur":      {"lat": 26.9124, "lng": 75.7873, "state": "Rajasthan",       "population_density": 6400,  "region_type": "urban",      "primary_crops": ["wheat","barley","mustard"],      "market_size": "large"},
    "Ludhiana":    {"lat": 30.9010, "lng": 75.8573, "state": "Punjab",          "population_density": 8000,  "region_type": "urban",      "primary_crops": ["wheat","rice","maize"],          "market_size": "large"},
    "Ahmedabad":   {"lat": 23.0225, "lng": 72.5714, "state": "Gujarat",         "population_density": 9800,  "region_type": "urban",      "primary_crops": ["cotton","groundnut","wheat"],    "market_size": "large"},
    "Kolkata":     {"lat": 22.5726, "lng": 88.3639, "state": "West Bengal",     "population_density": 24252, "region_type": "urban",      "primary_crops": ["rice","jute","vegetables"],      "market_size": "large"},
    "Mumbai":      {"lat": 19.0760, "lng": 72.8777, "state": "Maharashtra",     "population_density": 20667, "region_type": "urban",      "primary_crops": ["rice","vegetables","mango"],     "market_size": "large"},
    "Patna":       {"lat": 25.5941, "lng": 85.1376, "state": "Bihar",           "population_density": 1800,  "region_type": "urban",      "primary_crops": ["rice","wheat","maize"],          "market_size": "medium"},
    "Lucknow":     {"lat": 26.8467, "lng": 80.9462, "state": "Uttar Pradesh",   "population_density": 6900,  "region_type": "urban",      "primary_crops": ["wheat","rice","sugarcane"],      "market_size": "large"},
}

# ─── Haversine Distance Formula ────────────────────────
def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Great-circle distance between two points (km).
    Uses Haversine formula.
    """
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lng2 - lng1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)

# ─── Demand Score ──────────────────────────────────────
def _demand_score(region_data: Dict, crop: str) -> float:
    """
    Revised scoring — reduces urban bonus
    so distance matters more
    """
    score = 0.0

    # Population density — reduced weights
    pd = region_data["population_density"]
    if pd > 10000:   score += 1.5   # was 3.0
    elif pd > 5000:  score += 1.0   # was 2.0
    elif pd > 2000:  score += 0.5   # was 1.0

    # Market size — reduced weights
    ms = region_data["market_size"]
    if ms == "large":   score += 1.0  # was 2.0
    elif ms == "medium":score += 0.5  # was 1.0

    # Crop penalty — if they grow it locally
    if crop.lower() in [c.lower()
                        for c in region_data["primary_crops"]]:
        score -= 0.5

    # Region type bonus — reduced
    rt = region_data["region_type"]
    if rt == "urban":      score += 0.5  # was 1.5
    elif rt == "semi-urban":score += 0.3  # was 0.5

    return max(0.0, score)


def _suitability(distance_km: float,
                  demand_score: float) -> str:
    """
    Suitability based purely on distance
    demand_score is only tiebreaker
    """
    if distance_km < 150:
        return "Highly Recommended"
    elif distance_km < 250:
        return "Recommended"
    elif distance_km < 350:
        return "Feasible"
    else:
        return "Possible"

# ─── Public API ────────────────────────────────────────
def get_nearest_regions(source_region: str, crop: str,
                         n: int = 5,
                         max_distance_km: float = 500.0) -> List[Dict]:
    """Find nearest regions to receive redistributed supply."""
    if source_region not in REGIONS:
        return []
    src = REGIONS[source_region]
    nearby = []
    for name, data in REGIONS.items():
        if name == source_region:
            continue
        dist = haversine_distance(src["lat"], src["lng"],
                                   data["lat"], data["lng"])
        if dist <= max_distance_km:
            ds = _demand_score(data, crop)
            nearby.append({
                "region":       name,
                "state":        data["state"],
                "distance_km":  dist,
                "region_type":  data["region_type"],
                "market_size":  data["market_size"],
                "demand_score": round(ds, 2),
                "suitability":  _suitability(dist, ds)
            })
    nearby.sort(key=lambda x: x["distance_km"] / (x["demand_score"] + 1))
    return nearby[:n]

def get_all_regions() -> List[str]:
    return list(REGIONS.keys())

def _find_region(name: str) -> str:
    """Case-insensitive region name lookup."""
    # Exact match first
    if name in REGIONS:
        return name
    # Case-insensitive match
    for key in REGIONS:
        if key.lower() == name.lower():
            return key
    return None

def get_distance_between(r1: str, r2: str) -> float:
    """Get distance in km between two regions."""
    key1 = _find_region(r1)
    key2 = _find_region(r2)
    if not key1 or not key2:
        return -1.0
    a, b = REGIONS[key1], REGIONS[key2]
    return haversine_distance(
        a["lat"], a["lng"],
        b["lat"], b["lng"]
    )

def get_region_info(region: str) -> Dict:
    """Get full information for a region."""
    key = _find_region(region)
    return REGIONS.get(key, {}) if key else {}

def get_nearest_regions(source_region: str, crop: str,
                         n: int = 5,
                         max_distance_km: float = 500.0) -> List[Dict]:
    """Find nearest regions to receive redistributed supply."""
    key = _find_region(source_region)
    if not key:
        return []
    src = REGIONS[key]
    nearby = []
    for name, data in REGIONS.items():
        if name == key:
            continue
        dist = haversine_distance(
            src["lat"], src["lng"],
            data["lat"], data["lng"]
        )
        if dist <= max_distance_km:
            ds = _demand_score(data, crop)
            nearby.append({
                "region":       name,
                "state":        data["state"],
                "distance_km":  dist,
                "region_type":  data["region_type"],
                "market_size":  data["market_size"],
                "demand_score": round(ds, 2),
                "suitability":  _suitability(dist, ds)
            })
    nearby.sort(
    key=lambda x: x["distance_km"] - (x["demand_score"] * 5)
)
    return nearby[:n]