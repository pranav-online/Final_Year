import math
from datetime import datetime


DEMAND_THRESHOLDS = {
    "rice": 500,
    "maize": 400,
    "cotton": 300,
    "tomato": 200,
    "onion": 250,
    "wheat": 600,
    "sugarcane": 800,
    "default": 300,
}


REGION_COORDINATES = {
    "hyderabad": (17.3850, 78.4867),
    "warangal": (17.9689, 79.5941),
    "nizamabad": (18.6725, 78.0941),
    "karimnagar": (18.4386, 79.1288),
    "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185),
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "bangalore": (12.9716, 77.5946),
    "mysore": (12.2958, 76.6394),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "mumbai": (19.0760, 72.8777),
    "ludhiana": (30.9010, 75.8573),
    "amritsar": (31.6340, 74.8723),
    "lucknow": (26.8467, 80.9462),
    "varanasi": (25.3176, 82.9739),
    "kochi": (9.9312, 76.2673),
    "thiruvananthapuram": (8.5241, 76.9366),
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "surat": (21.1702, 72.8311),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
}


STATE_TO_REFERENCE_REGION = {
    "telangana": "hyderabad",
    "andhra pradesh": "vijayawada",
    "tamil nadu": "chennai",
    "karnataka": "bangalore",
    "maharashtra": "pune",
    "punjab": "ludhiana",
    "uttar pradesh": "lucknow",
    "kerala": "kochi",
    "rajasthan": "jaipur",
    "west bengal": "kolkata",
    "gujarat": "ahmedabad",
    "madhya pradesh": "bhopal",
}


def normalize_key(value: str) -> str:
    return (value or "").strip().lower()


def display_name(value: str) -> str:
    return normalize_key(value).title()


def canonical_region(region: str) -> str:
    key = normalize_key(region)
    return STATE_TO_REFERENCE_REGION.get(key, key)


def get_demand_threshold(crop: str) -> int:
    return DEMAND_THRESHOLDS.get(normalize_key(crop), DEMAND_THRESHOLDS["default"])


def classify_supply(quantity: float, threshold: float) -> str:
    if quantity > threshold * 1.5:
        return "oversupply"
    if quantity < threshold * 0.5:
        return "undersupply"
    return "balanced"


def haversine_km(source_region: str, target_region: str):
    source_key = canonical_region(source_region)
    target_key = canonical_region(target_region)
    source = REGION_COORDINATES.get(source_key)
    target = REGION_COORDINATES.get(target_key)
    if not source or not target:
        return None

    lat1, lon1 = source
    lat2, lon2 = target
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius_km * c, 2)


def empty_supply_index():
    return {}


def add_supply(regional_data: dict, region: str, crop: str, quantity: float):
    region_key = normalize_key(region)
    crop_key = normalize_key(crop)
    if not region_key or not crop_key:
        return

    regional_data.setdefault(region_key, {})
    regional_data[region_key][crop_key] = (
        regional_data[region_key].get(crop_key, 0) + float(quantity or 0)
    )


def _candidate_regions(regional_data: dict) -> list:
    regions = set(REGION_COORDINATES.keys())
    regions.update(regional_data.keys())
    return sorted(regions)


def find_redistribution_options(
    regional_data: dict,
    source_region: str,
    crop: str,
    alert_type: str,
    max_results: int = 3,
    expected_demand_by_region: dict = None,
) -> list:
    source_key = normalize_key(source_region)
    crop_key = normalize_key(crop)
    expected_demand_by_region = expected_demand_by_region or {}
    threshold = expected_demand_by_region.get(source_key, get_demand_threshold(crop_key))
    source_qty = regional_data.get(source_key, {}).get(crop_key, 0)
    options = []

    for region in _candidate_regions(regional_data):
        region_key = normalize_key(region)
        if (
            region_key == source_key
            or canonical_region(region_key) == canonical_region(source_key)
        ):
            continue

        current_qty = regional_data.get(region_key, {}).get(crop_key, 0)
        region_threshold = expected_demand_by_region.get(
            region_key, get_demand_threshold(crop_key)
        )
        region_status = classify_supply(current_qty, region_threshold)

        if alert_type == "oversupply" and region_status == "undersupply":
            transferable_qty = max(
                0,
                min(source_qty - threshold, region_threshold - current_qty),
            )
            direction = "send_to"
        elif alert_type == "undersupply" and region_status == "oversupply":
            transferable_qty = max(
                0,
                min(threshold - source_qty, current_qty - region_threshold),
            )
            direction = "source_from"
        else:
            continue

        if transferable_qty <= 0:
            continue

        options.append({
            "region": display_name(region_key),
            "current_quantity_kg": round(current_qty, 2),
            "expected_demand_kg": region_threshold,
            "threshold_kg": region_threshold,
            "status": region_status,
            "distance_km": haversine_km(source_key, region_key),
            "suggested_quantity_kg": round(transferable_qty, 2),
            "direction": direction,
        })

    options.sort(
        key=lambda item: (
            item["distance_km"] is None,
            item["distance_km"] if item["distance_km"] is not None else 10**9,
            -item["suggested_quantity_kg"],
        )
    )
    return options[:max_results]


def build_action(crop: str, alert_type: str, options: list) -> str:
    crop_name = display_name(crop)
    if options:
        best = options[0]
        distance = (
            f" about {best['distance_km']} km away"
            if best["distance_km"] is not None
            else ""
        )
        if alert_type == "oversupply":
            return (
                f"Redirect up to {best['suggested_quantity_kg']} kg of "
                f"{crop_name} to {best['region']}{distance}."
            )
        return (
            f"Source up to {best['suggested_quantity_kg']} kg of "
            f"{crop_name} from {best['region']}{distance}."
        )

    if alert_type == "oversupply":
        return f"Redirect {crop_name} to nearby undersupplied regions after broker review."
    if alert_type == "undersupply":
        return f"Source {crop_name} from nearby oversupplied regions after broker review."
    return "No action needed."


def build_market_signal(
    region: str,
    crop: str,
    quantity: float,
    regional_data: dict,
    threshold: float = None,
    expected_demand_by_region: dict = None,
) -> dict:
    region_key = normalize_key(region)
    crop_key = normalize_key(crop)
    threshold = threshold or get_demand_threshold(crop_key)
    quantity = round(float(quantity or 0), 2)
    signal_type = classify_supply(quantity, threshold)
    options = find_redistribution_options(
        regional_data,
        region_key,
        crop_key,
        signal_type,
        expected_demand_by_region=expected_demand_by_region,
    )

    severity = "low"
    title = f"Balanced Supply - {display_name(crop_key)}"
    if signal_type == "oversupply":
        severity = "high"
        title = f"Oversupply Alert - {display_name(crop_key)}"
    elif signal_type == "undersupply":
        severity = "medium"
        title = f"Low Supply Alert - {display_name(crop_key)}"

    supply_ratio = round(quantity / threshold, 2) if threshold else 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    if signal_type == "balanced":
        message = (
            f"{display_name(crop_key)} supply is balanced in "
            f"{display_name(region_key)} at {quantity} kg."
        )
    elif signal_type == "oversupply":
        message = (
            f"Oversupply of {display_name(crop_key)} in {display_name(region_key)}: "
            f"{quantity} kg available against estimated demand of {threshold} kg."
        )
    else:
        message = (
            f"Low supply of {display_name(crop_key)} in {display_name(region_key)}: "
            f"{quantity} kg available against estimated demand of {threshold} kg."
        )

    return {
        "id": f"{region_key}_{crop_key}_{signal_type}",
        "type": signal_type if signal_type != "balanced" else "normal",
        "severity": severity,
        "region": region_key,
        "crop": crop_key,
        "quantity": quantity,
        "threshold": threshold,
        "expected_demand_kg": threshold,
        "supply_ratio": supply_ratio,
        "supply_demand_ratio": supply_ratio,
        "title": title,
        "message": message,
        "action": build_action(crop_key, signal_type, options),
        "redistribution_options": options,
        "time": now,
    }
