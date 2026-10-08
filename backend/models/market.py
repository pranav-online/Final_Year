from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class CropStatus(str, Enum):
    available = "available"
    sold = "sold"
    reserved = "reserved"

class CropListing(BaseModel):
    farmer_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    crop_name: str = Field(min_length=1)
    quantity_kg: float = Field(gt=0, allow_inf_nan=False)
    price_per_kg: float = Field(gt=0, allow_inf_nan=False)
    status: CropStatus = CropStatus.available
    contact: Optional[str] = None

class DemandQuery(BaseModel):
    region: str
    crop_name: Optional[str] = None