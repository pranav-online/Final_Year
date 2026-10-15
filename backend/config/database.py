import time

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
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


# ─── Circuit breaker ───────────────────────────────────────
# Without it, every request made while MongoDB is down waited for the 5 s
# server-selection timeout before the local JSON fallback ran. After one
# connection failure, calls fail fast for MONGO_RETRY_SECONDS, then retry.
MONGO_RETRY_SECONDS = 120
_mongo_down_until = 0.0


def mongo_marked_down() -> bool:
    return time.monotonic() < _mongo_down_until


def _mark_down() -> None:
    global _mongo_down_until
    _mongo_down_until = time.monotonic() + MONGO_RETRY_SECONDS


def reset_mongo_breaker() -> None:
    global _mongo_down_until
    _mongo_down_until = 0.0


def _fail_fast() -> None:
    if mongo_marked_down():
        raise ServerSelectionTimeoutError("MongoDB marked unavailable; using the local fallback")


class _GuardedCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __getattr__(self, name):
        attr = getattr(self._cursor, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            result = attr(*args, **kwargs)
            # chainable cursor methods (sort, limit, skip) return the cursor itself
            return _GuardedCursor(result) if result is self._cursor else result
        return call

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self._cursor.__anext__()
        except ConnectionFailure:
            _mark_down()
            raise


class GuardedCollection:
    """Motor collection wrapper: only connection failures trip the breaker; other errors pass through."""

    def __init__(self, collection):
        self._collection = collection

    def find(self, *args, **kwargs):
        _fail_fast()
        return _GuardedCursor(self._collection.find(*args, **kwargs))

    def __getattr__(self, name):
        attr = getattr(self._collection, name)
        if not callable(attr):
            return attr

        async def call(*args, **kwargs):
            _fail_fast()
            try:
                return await attr(*args, **kwargs)
            except ConnectionFailure:
                _mark_down()
                raise
        return call


# Collections
users_collection = GuardedCollection(db["users"])
farmer_collection = GuardedCollection(db["farmer_data"])
broker_collection = GuardedCollection(db["broker_data"])
market_collection = GuardedCollection(db["market_data"])
market_alerts_collection = GuardedCollection(db["market_alerts"])
