from fastapi import APIRouter, Depends
from config.auth_deps import require_role
from services.region_service import (
    get_nearest_regions,
    get_distance_between,
    get_all_regions,
    get_region_info
)

router = APIRouter(dependencies=[Depends(require_role("broker"))])

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
