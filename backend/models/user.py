from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    farmer = "farmer"
    broker = "broker"

# Register request model
class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str
    role: UserRole
    phone: Optional[str] = None
    location: Optional[str] = None

# Login request model
class UserLogin(BaseModel):
    email: str
    password: str

# Response model (never expose password)
class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    phone: Optional[str] = None
    location: Optional[str] = None