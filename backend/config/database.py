from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "alip_local")

client = AsyncIOMotorClient(
    MONGODB_URL,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
)
db = client[DATABASE_NAME]


async def ping_database():
    await client.admin.command("ping")

# Collections
users_collection = db["users"]
farmer_collection = db["farmer_data"]
broker_collection = db["broker_data"]
market_collection = db["market_data"]
market_alerts_collection = db["market_alerts"]
