from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

try:
    client = MongoClient(os.getenv("MONGODB_URL"))
    db = client[os.getenv("DATABASE_NAME")]
    print("✅ Connected to MongoDB:", db.name)
    
    # Get existing collections
    existing_collections = db.list_collection_names()
    
    # Create collections only if they don't exist
    collections = ["users", "farmer_data", "broker_data", "market_data"]
    
    for collection in collections:
        if collection not in existing_collections:
            db.create_collection(collection)
            print(f"✅ Created collection: {collection}")
        else:
            print(f"ℹ️ Collection already exists: {collection}")
    
    print("\n✅ All done! Database is ready.")

except Exception as e:
    print("❌ Connection failed:", e)