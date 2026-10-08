from fastapi import APIRouter, HTTPException, status
from models.user import UserRegister, UserLogin, UserResponse
from config.database import users_collection
from config.security import hash_password, verify_password, create_access_token
from services import local_auth_store
from bson import ObjectId
from pymongo.errors import PyMongoError
import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])


def database_unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Database connection unavailable. Check MongoDB Atlas network "
            "access, cluster status, and MONGODB_URL."
        ),
    )


def build_user_doc(user: UserRegister) -> dict:
    return {
        "full_name": user.full_name,
        "email": user.email,
        "password": hash_password(user.password),
        "role": user.role.value,
        "phone": user.phone,
        "location": user.location,
        "created_at": datetime.datetime.utcnow()
    }


def build_login_response(db_user: dict) -> dict:
    token = create_access_token(data={
        "sub": str(db_user["_id"]),
        "email": db_user["email"],
        "role": db_user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": db_user["role"],
        "full_name": db_user["full_name"]
    }


async def register_with_local_store(user: UserRegister) -> dict:
    existing_user = await local_auth_store.find_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_doc = build_user_doc(user)
    inserted_id = await local_auth_store.insert_user(user_doc)

    return {
        "message": "User registered successfully",
        "id": inserted_id,
        "role": user.role.value,
        "storage": "local"
    }


async def login_with_local_store(user: UserLogin) -> dict:
    db_user = await local_auth_store.find_user_by_email(user.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    response = build_login_response(db_user)
    response["storage"] = "local"
    return response

@router.post("/register")
async def register(user: UserRegister):
    if users_collection is None:
        return await register_with_local_store(user)

    try:
        # Check if email already exists
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user document
        user_doc = build_user_doc(user)

        # Insert into database
        result = await users_collection.insert_one(user_doc)

        return {
            "message": "User registered successfully",
            "id": str(result.inserted_id),
            "role": user.role
        }
    except HTTPException:
        raise
    except PyMongoError:
        return await register_with_local_store(user)

@router.post("/login")
async def login(user: UserLogin):
    if users_collection is None:
        return await login_with_local_store(user)

    try:
        # Find user by email
        db_user = await users_collection.find_one({"email": user.email})
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        return build_login_response(db_user)
    except HTTPException:
        raise
    except PyMongoError:
        return await login_with_local_store(user)
