"""Cleaning and validation of raw mandi rows into one common schema.

Common price row (prices in Rs/quintal):
    _id          natural key: date|state|district|market|commodity|variety|grade|source
    date         ISO date of the arrival / report (YYYY-MM-DD)
    state, district, market   cleaned display names
    market_key   lower-cased "state|district|market", stable series identifier
    commodity    canonical id from config.COMMODITIES
    commodity_raw, variety, grade
    min_price, max_price, modal_price, unit
    source       datagov | ceda
    flags        list of data-quality flags (rows are kept, never silently dropped)
    fetched_at   ISO UTC timestamp of the pull
    raw          the original source record
"""
from datetime import datetime, timezone

from services.mandi.config import resolve_commodity

UNIT = "Rs/quintal"

FLAG_MIN_GT_MODAL = "min_gt_modal"
FLAG_MODAL_GT_MAX = "modal_gt_max"
FLAG_NONPOSITIVE = "nonpositive_price"
FLAG_OUTLIER = "outlier"

# Flags that make a row unusable for analytics (outlier rows are still usable
# but are shown as suspect).
BLOCKING_FLAGS = {FLAG_MIN_GT_MODAL, FLAG_MODAL_GT_MAX, FLAG_NONPOSITIVE}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value) -> str:
    """Trim and collapse internal whitespace ("APMC Nasik " -> "APMC Nasik")."""
    return " ".join(str(value or "").split())


def key_text(value) -> str:
    return clean_text(value).lower()


def parse_date(value):
    """Accept dd/mm/yyyy, dd-mm-yyyy or yyyy-mm-dd (optionally with time); return ISO date."""
    text = clean_text(value)[:10]
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def to_price(value):
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number


def market_key(state: str, district: str, market: str) -> str:
    return "|".join(key_text(part) for part in (state, district, market))


def row_id(row: dict) -> str:
    parts = (
        row["date"], row["state"], row["district"], row["market"],
        row["commodity"], row["variety"], row["grade"], row["source"],
    )
    return "|".join(key_text(part) for part in parts)


def quality_flags(min_price, max_price, modal_price) -> list[str]:
    flags = []
    if any(p is not None and p <= 0 for p in (min_price, max_price, modal_price)):
        flags.append(FLAG_NONPOSITIVE)
    if min_price is not None and modal_price is not None and min_price > modal_price:
        flags.append(FLAG_MIN_GT_MODAL)
    if max_price is not None and modal_price is not None and modal_price > max_price:
        flags.append(FLAG_MODAL_GT_MAX)
    return flags


def build_price_row(*, date, state, district, market, commodity_raw, variety, grade,
                    min_price, max_price, modal_price, source, raw, fetched_at=None):
    """
    Return (row, problem). `problem` is a short reason when the record cannot be
    stored at all (no date, unknown commodity, no modal price); otherwise None.
    """
    iso_date = parse_date(date)
    commodity = resolve_commodity(commodity_raw)
    modal = to_price(modal_price)

    if iso_date is None:
        return None, "unparseable_date"
    if commodity is None:
        return None, "unmapped_commodity"
    if modal is None:
        return None, "missing_modal_price"

    row = {
        "date": iso_date,
        "state": clean_text(state),
        "district": clean_text(district),
        "market": clean_text(market),
        "commodity": commodity,
        "commodity_raw": clean_text(commodity_raw),
        "variety": clean_text(variety) or "Other",
        "grade": clean_text(grade) or "FAQ",
        "min_price": to_price(min_price),
        "max_price": to_price(max_price),
        "modal_price": modal,
        "unit": UNIT,
        "source": source,
        "fetched_at": fetched_at or utc_now_iso(),
        "raw": raw,
    }
    row["market_key"] = market_key(row["state"], row["district"], row["market"])
    row["flags"] = quality_flags(row["min_price"], row["max_price"], row["modal_price"])
    row["_id"] = row_id(row)
    return row, None


def normalize_datagov_record(record: dict, fetched_at: str = None):
    return build_price_row(
        date=record.get("arrival_date"),
        state=record.get("state"),
        district=record.get("district"),
        market=record.get("market"),
        commodity_raw=record.get("commodity"),
        variety=record.get("variety"),
        grade=record.get("grade"),
        min_price=record.get("min_price"),
        max_price=record.get("max_price"),
        modal_price=record.get("modal_price"),
        source="datagov",
        raw=record,
        fetched_at=fetched_at,
    )


def is_usable(row: dict) -> bool:
    return not (set(row.get("flags") or []) & BLOCKING_FLAGS)
