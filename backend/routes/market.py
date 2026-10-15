from fastapi import APIRouter, Depends, HTTPException
from config.auth_deps import get_current_user, require_role
from models.market import CropListing
from services.market_service import (
    add_crop_listing,
    get_all_listings,
    get_all_regional_supply,
    get_regional_supply,
    analyze_demand,
    get_market_summary
)
from services.demand_analysis import DEMAND_THRESHOLDS

router = APIRouter(prefix="/market", tags=["Broker Market"])
broker_only = [Depends(require_role("broker"))]

# Farmer adds crop listing (any signed-in user; the /listing page is shared)
@router.post("/listing/add", dependencies=[Depends(get_current_user)])
async def add_listing(listing: CropListing):
    result = await add_crop_listing(listing)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get all available listings
@router.get("/listings", dependencies=broker_only)
async def get_listings():
    result = await get_all_listings()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# Aggregate available supply by region and crop
@router.get("/supply", dependencies=broker_only)
async def all_regional_supply():
    result = await get_all_regional_supply()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get supply for a specific region
@router.get("/supply/{region}", dependencies=broker_only)
async def regional_supply(region: str):
    result = await get_regional_supply(region)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Analyze demand and get alerts
@router.get("/demand/{region}", dependencies=broker_only)
async def demand_analysis(region: str, crop: str = None):
    result = await analyze_demand(region, crop)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get full market summary for broker dashboard
@router.get("/summary", dependencies=broker_only)
async def market_summary():
    result = await get_market_summary()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.get("/thresholds", dependencies=broker_only)
async def demand_thresholds():
    return {
        "success": True,
        "thresholds": DEMAND_THRESHOLDS
    }
