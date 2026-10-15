import os

from dotenv import load_dotenv

load_dotenv()

# ─── Commodity scope ───────────────────────────────────────
# Canonical id -> names used by each source. Perishability tiers follow the
# master report's urgency multipliers (Tier 1 x2.0, Tier 2 x1.3, Tier 3 x1.0).
COMMODITIES = {
    "tomato":    {"name": "Tomato",    "datagov": ["Tomato"],        "agmarknet": "Tomato",    "tier": 1, "aliases": ["tomatoes", "tamatar"]},
    "banana":    {"name": "Banana",    "datagov": ["Banana"],        "agmarknet": "Banana",    "tier": 1, "aliases": ["bananas", "kela"]},
    "onion":     {"name": "Onion",     "datagov": ["Onion"],         "agmarknet": "Onion",     "tier": 2, "aliases": ["onions", "pyaz", "pyaaz"]},
    "potato":    {"name": "Potato",    "datagov": ["Potato"],        "agmarknet": "Potato",    "tier": 2, "aliases": ["potatoes", "aloo", "alu"]},
    "maize":     {"name": "Maize",     "datagov": ["Maize"],         "agmarknet": "Maize",     "tier": 2, "aliases": ["corn", "makka", "makkai"]},
    "paddy":     {"name": "Paddy",     "datagov": ["Paddy(Common)"], "agmarknet": "Paddy(Common)", "tier": 3, "aliases": ["paddy(dhan)(common)", "dhan"]},
    "rice":      {"name": "Rice",      "datagov": ["Rice"],          "agmarknet": "Rice",      "tier": 3, "aliases": ["chawal"]},
    "wheat":     {"name": "Wheat",     "datagov": ["Wheat"],         "agmarknet": "Wheat",     "tier": 3, "aliases": ["gehun", "gehu"]},
    "cotton":    {"name": "Cotton",    "datagov": ["Cotton"],        "agmarknet": "Cotton",    "tier": 3, "aliases": ["kapas"]},
    "groundnut": {"name": "Groundnut", "datagov": ["Groundnut"],     "agmarknet": "Groundnut", "tier": 3, "aliases": ["peanut", "peanuts", "moongphali"]},
}

TIER_MULTIPLIER = {1: 2.0, 2: 1.3, 3: 1.0}

# Spelling variants seen across sources -> one canonical key
# (data.gov.in uses "Keralam"; the app's region table uses "Kerala").
STATE_ALIASES = {
    "keralam": "kerala",
    "orissa": "odisha",
    "pondicherry": "puducherry",
    "chattisgarh": "chhattisgarh",
    "nct of delhi": "delhi",
}


def state_key(name: str) -> str:
    key = " ".join(str(name or "").lower().split())
    return STATE_ALIASES.get(key, key)


# States used for the one-time CEDA history backfill (the app's home regions).
BACKFILL_STATES = ["Andhra Pradesh", "Telangana", "Maharashtra", "Karnataka", "Tamil Nadu"]


def _alias_index() -> dict:
    index = {}
    for cid, meta in COMMODITIES.items():
        names = [cid, meta["name"], meta["agmarknet"], *meta["datagov"], *meta["aliases"]]
        for name in names:
            index[" ".join(name.lower().split())] = cid
    return index


_ALIASES = _alias_index()


def resolve_commodity(name: str):
    """Map a free-text or source commodity name to a canonical id, or None."""
    if not name:
        return None
    return _ALIASES.get(" ".join(str(name).lower().split()))


def scoped_commodities() -> list[str]:
    """Commodity ids to ingest. MANDI_COMMODITIES=tomato,onion narrows the scope."""
    raw = os.getenv("MANDI_COMMODITIES", "").strip()
    if not raw:
        return list(COMMODITIES)
    ids = [resolve_commodity(part) for part in raw.split(",")]
    return [cid for cid in ids if cid]


# ─── data.gov.in ───────────────────────────────────────────
DATAGOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATAGOV_URL = f"https://api.data.gov.in/resource/{DATAGOV_RESOURCE_ID}"
# Public sample key published on data.gov.in. It caps every page at 10 rows,
# so a registered personal key (DATA_GOV_API_KEY) is strongly recommended.
DATAGOV_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"


def datagov_api_key() -> str:
    return os.getenv("DATA_GOV_API_KEY", "").strip() or DATAGOV_SAMPLE_KEY


def using_sample_key() -> bool:
    return datagov_api_key() == DATAGOV_SAMPLE_KEY


def datagov_page_size() -> int:
    default = 10 if using_sample_key() else 1000
    return int(os.getenv("DATA_GOV_PAGE_SIZE", default))


# ─── Agmarknet 2.0 (undocumented public JSON API) ──────────
AGMARKNET_BASE = "https://api.agmarknet.gov.in/v1"

# ─── CEDA, Ashoka University (history backfill) ────────────
CEDA_BASE = "https://api.ceda.ashoka.edu.in/v1"


def ceda_api_key() -> str:
    return os.getenv("CEDA_API_KEY", "").strip()


# ─── Storage / scheduling ──────────────────────────────────
def store_mode() -> str:
    """auto (MongoDB if reachable, else SQLite), mongo, or sqlite."""
    return os.getenv("MANDI_STORE", "auto").strip().lower()


def scheduler_enabled() -> bool:
    return os.getenv("SCHEDULER_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}


SCHEDULER_TIMEZONE = "Asia/Kolkata"
