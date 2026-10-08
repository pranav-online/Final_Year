from fastapi import APIRouter, HTTPException
from models.market import CropListing, DemandQuery
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

# Farmer adds crop listing
@router.post("/listing/add")
async def add_listing(listing: CropListing):
    result = await add_crop_listing(listing)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get all available listings
@router.get("/listings")
async def get_listings():
    result = await get_all_listings()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# Aggregate available supply by region and crop
@router.get("/supply")
async def all_regional_supply():
    result = await get_all_regional_supply()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get supply for a specific region
@router.get("/supply/{region}")
async def regional_supply(region: str):
    result = await get_regional_supply(region)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Analyze demand and get alerts
@router.get("/demand/{region}")
async def demand_analysis(region: str, crop: str = None):
    result = await analyze_demand(region, crop)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Get full market summary for broker dashboard
@router.get("/summary")
async def market_summary():
    result = await get_market_summary()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.get("/thresholds")
async def demand_thresholds():
    return {
        "success": True,
        "thresholds": DEMAND_THRESHOLDS
    }
