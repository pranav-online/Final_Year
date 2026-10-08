from fastapi import APIRouter
from services.demand_ml_service import predict_dynamic_threshold
from services.region_service import get_region_info
from services.region_service import (
    get_nearest_regions,
    get_distance_between,
    get_all_regions,
    get_region_info
)

router = APIRouter()

# Get nearest regions for redistribution
@router.get("/regions/nearest/{region}/{crop}")
async def nearest_regions(region: str, crop: str,
                           max_km: float = 500.0):
    crop = crop.strip()
    region = region.strip()
    results = get_nearest_regions(
        region, crop,
        n=5,
        max_distance_km=max_km
    )
    if not results:
        return {
            "success": False,
            "message": f"Region '{region}' not found"
        }
    return {
        "success":        True,
        "source_region":  region,
        "crop":           crop,
        "recommendations": results,
        "total_found":    len(results)
    }

# Get distance between two regions
@router.get("/regions/distance/{region1}/{region2}")
async def region_distance(region1: str, region2: str):
    dist = get_distance_between(region1, region2)
    if dist < 0:
        return {
            "success": False,
            "message": "One or both regions not found"
        }
    return {
        "success":    True,
        "region1":    region1,
        "region2":    region2,
        "distance_km": dist
    }

# Get all available regions
@router.get("/regions/all")
async def all_regions():
    return {
        "success": True,
        "regions": get_all_regions(),
        "total":   len(get_all_regions())
    }

# Get single region info
@router.get("/regions/info/{region}")
async def region_info(region: str):
    info = get_region_info(region)
    if not info:
        return {
            "success": False,
            "message": f"Region '{region}' not found"
        }
    return {
        "success": True,
        "region":  region,
        "info":    info
    }
@router.get("/demand/threshold/{region}/{crop}")
async def dynamic_threshold(region: str, crop: str):
    region = region.strip()
    crop   = crop.strip()

    # Get region data
    info = get_region_info(region)
    if not info:
        return {"success": False,
                "message": f"Region '{region}' not found"}

    result = predict_dynamic_threshold(
        crop              = crop,
        region_type       = info.get("region_type","semi-urban"),
        population_density= info.get("population_density", 3000),
        market_size       = info.get("market_size", "medium")
    )
    return {"success": True, **result}
from services.demand_ml_service import (
    predict_dynamic_threshold,
    analyze_supply_trend
)
from fastapi import Body

@router.post("/demand/trend/{region}/{crop}")
async def supply_trend(
    region: str,
    crop: str,
    supply_history: list = Body(
        ...,
        example=[300, 450, 600, 800, 1100]
    )
):
    region = region.strip()
    crop   = crop.strip()

    # Get dynamic threshold first
    info = get_region_info(region)
    if not info:
        return {"success": False,
                "message": f"Region '{region}' not found"}

    threshold_result = predict_dynamic_threshold(
        crop               = crop,
        region_type        = info.get("region_type", "semi-urban"),
        population_density = info.get("population_density", 3000),
        market_size        = info.get("market_size", "medium")
    )
    threshold = threshold_result["predicted_threshold_kg"]

    # Analyze trend
    trend = analyze_supply_trend(supply_history, threshold)

    return {
        "success":          True,
        "region":           region,
        "crop":             crop,
        "dynamic_threshold":threshold,
        "trend_analysis":   trend
    }
from services.demand_ml_service import (
    predict_dynamic_threshold,
    analyze_supply_trend,
    estimate_price_impact
)

@router.get("/demand/price-impact/{region}/{crop}/{supply_kg}")
async def price_impact(
    region: str,
    crop: str,
    supply_kg: float
):
    region = region.strip()
    crop   = crop.strip()

    # Get dynamic threshold
    info = get_region_info(region)
    if not info:
        return {"success": False,
                "message": f"Region '{region}' not found"}

    threshold_result = predict_dynamic_threshold(
        crop               = crop,
        region_type        = info.get("region_type","semi-urban"),
        population_density = info.get("population_density",3000),
        market_size        = info.get("market_size","medium")
    )
    threshold = threshold_result["predicted_threshold_kg"]

    # Price impact
    impact = estimate_price_impact(crop, supply_kg, threshold)

    # Nearest regions for redistribution
    from services.region_service import get_nearest_regions
    nearby = get_nearest_regions(region, crop, n=3)

    return {
        "success":           True,
        "region":            region,
        "crop":              crop,
        "current_supply_kg": supply_kg,
        "dynamic_threshold": threshold,
        "price_impact":      impact,
        "redistribute_to":   nearby
    }