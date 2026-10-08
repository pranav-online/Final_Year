import json
import uuid
from pathlib import Path
from threading import Lock


STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "local_market_listings.json"
_lock = Lock()


def _load_listings() -> list[dict]:
    if not STORE_PATH.exists():
        return []

    with STORE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_listings(listings: list[dict]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(listings, file, indent=2)


def _matches_query(listing: dict, query: dict | None) -> bool:
    if not query:
        return True

    for key, expected in query.items():
        if listing.get(key) != expected:
            return False

    return True


async def insert_listing(doc: dict) -> str:
    with _lock:
        listings = _load_listings()
        listing_id = str(uuid.uuid4())
        local_doc = {
            **doc,
            "_id": listing_id,
            "status": str(doc["status"]),
            "created_at": doc["created_at"].isoformat(),
        }
        listings.append(local_doc)
        _save_listings(listings)
        return listing_id


async def find_listings(query: dict | None = None) -> list[dict]:
    with _lock:
        return [
            dict(listing)
            for listing in _load_listings()
            if _matches_query(listing, query)
        ]
