"""
Storage repository for mandi data.

MongoMandiStore is used when MongoDB is reachable. SqliteMandiStore is the local
fallback: a single file in backend/data, so months of daily price rows stay
fast to query (a JSON file would have to be rewritten on every pull).
Both expose the same async interface.
"""
import asyncio
import json
import sqlite3
import statistics
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from services.mandi import config

PRICE_FIELDS = (
    "date", "state", "district", "market", "market_key", "commodity", "commodity_raw",
    "variety", "grade", "min_price", "max_price", "modal_price", "unit", "source",
    "flags", "fetched_at",
)
NATURAL_KEY = ("date", "state", "district", "market", "commodity", "variety", "grade", "source")

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[2] / "data" / "mandi.sqlite3"


class MarketWeekAggregator:
    """
    Turns price rows streamed in market_key order into one median per
    (market, week). Only one market's rows are held in memory at a time.
    Within a market-day-variety-grade the daily feed wins over CEDA.
    """
    SOURCE_RANK = {"datagov": 0, "ceda": 1}

    def __init__(self):
        self.results = []
        self._market = None
        self._state = None
        self._picks = {}

    def add(self, row: dict) -> None:
        flags = row.get("flags") or []
        if isinstance(flags, str):
            flags = json.loads(flags or "[]")
        if set(flags) & {"min_gt_modal", "modal_gt_max", "nonpositive_price"}:
            return
        if row["market_key"] != self._market:
            self._flush()
            self._market, self._state = row["market_key"], row["state"]
        key = (row["date"], (row.get("variety") or "").lower(), (row.get("grade") or "").lower())
        best = self._picks.get(key)
        if best is None or self.SOURCE_RANK.get(row["source"], 9) < self.SOURCE_RANK.get(best["source"], 9):
            self._picks[key] = row

    def _flush(self) -> None:
        weeks = {}
        for row in self._picks.values():
            day = date.fromisoformat(row["date"])
            weeks.setdefault((day - timedelta(days=day.weekday())).isoformat(), []).append(row["modal_price"])
        for week, values in sorted(weeks.items()):
            self.results.append({
                "market_key": self._market, "state": self._state, "week_start": week,
                "price": statistics.median(values), "observations": len(values),
            })
        self._picks = {}

    def finish(self) -> list[dict]:
        self._flush()
        return self.results


class MandiStore:
    name = "abstract"

    async def upsert_prices(self, rows: list[dict]) -> dict: ...
    async def find_prices(self, commodity: str, date_from: str = None, date_to: str = None,
                          market_key: str = None, state: str = None) -> list[dict]: ...
    async def set_flags(self, flags_by_id: dict) -> None: ...
    async def price_stats(self) -> dict: ...
    async def duplicate_groups(self) -> int: ...
    async def upsert_arrivals(self, rows: list[dict]) -> dict: ...
    async def find_arrivals(self, commodity: str, date_from: str = None, date_to: str = None) -> list[dict]: ...
    async def replace_master(self, kind: str, docs: list[dict]) -> None: ...
    async def get_master(self, kind: str) -> list[dict]: ...
    async def add_ingest_report(self, doc: dict) -> None: ...
    async def recent_ingest_reports(self, source: str = None, limit: int = 10) -> list[dict]: ...
    async def weekly_market_medians(self, commodity: str, date_from: str) -> list[dict]: ...
    async def replace_signals(self, commodity: str, docs: list[dict]) -> None: ...
    async def find_signals(self, commodity: str = None, level: str = None) -> list[dict]: ...
    async def insert_alert_if_new(self, alert: dict, window_hours: int = 24) -> bool: ...
    async def find_alerts(self, since: str = None, commodity: str = None, limit: int = 200) -> list[dict]: ...


def _window_start(window_hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat(timespec="seconds")


# ─── SQLite fallback ───────────────────────────────────────
class SqliteMandiStore(MandiStore):
    name = "sqlite"

    def __init__(self, path=DEFAULT_SQLITE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self):
        with self._lock, self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS prices (
                    id TEXT PRIMARY KEY, date TEXT NOT NULL, state TEXT, district TEXT,
                    market TEXT, market_key TEXT, commodity TEXT NOT NULL, commodity_raw TEXT,
                    variety TEXT, grade TEXT, min_price REAL, max_price REAL, modal_price REAL,
                    unit TEXT, source TEXT, flags TEXT, fetched_at TEXT, raw TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_prices_commodity_date ON prices(commodity, date);
                CREATE INDEX IF NOT EXISTS ix_prices_series ON prices(market_key, commodity, date);
                CREATE TABLE IF NOT EXISTS arrivals (
                    id TEXT PRIMARY KEY, date TEXT NOT NULL, commodity TEXT NOT NULL,
                    level TEXT, doc TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_arrivals_commodity_date ON arrivals(commodity, date);
                CREATE TABLE IF NOT EXISTS masters (
                    kind TEXT NOT NULL, id TEXT NOT NULL, doc TEXT, PRIMARY KEY (kind, id)
                );
                CREATE TABLE IF NOT EXISTS ingest_reports (
                    run_id TEXT PRIMARY KEY, source TEXT, started_at TEXT, doc TEXT
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY, commodity TEXT NOT NULL, level TEXT, doc TEXT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY, dedupe_key TEXT, commodity TEXT, created_at TEXT, doc TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_alerts_dedupe ON alerts(dedupe_key, created_at);
                CREATE INDEX IF NOT EXISTS ix_alerts_created ON alerts(created_at);
            """)

    async def _run(self, fn, *args):
        return await asyncio.to_thread(self._locked, fn, *args)

    def _locked(self, fn, *args):
        with self._lock:
            return fn(*args)

    def _existing_ids(self, table: str, ids: list[str]) -> set:
        found = set()
        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            marks = ",".join("?" * len(chunk))
            found.update(r[0] for r in self._conn.execute(
                f"SELECT id FROM {table} WHERE id IN ({marks})", chunk))
        return found

    # prices
    def _upsert_prices(self, rows):
        existing = self._existing_ids("prices", [r["_id"] for r in rows])
        with self._conn:
            self._conn.executemany(
                """INSERT INTO prices (id, date, state, district, market, market_key, commodity,
                       commodity_raw, variety, grade, min_price, max_price, modal_price, unit,
                       source, flags, fetched_at, raw)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                       min_price=excluded.min_price, max_price=excluded.max_price,
                       modal_price=excluded.modal_price, flags=excluded.flags,
                       fetched_at=excluded.fetched_at, raw=excluded.raw""",
                [(
                    r["_id"], r["date"], r["state"], r["district"], r["market"], r["market_key"],
                    r["commodity"], r["commodity_raw"], r["variety"], r["grade"], r["min_price"],
                    r["max_price"], r["modal_price"], r["unit"], r["source"],
                    json.dumps(r.get("flags") or []), r["fetched_at"], json.dumps(r.get("raw")),
                ) for r in rows],
            )
        inserted = sum(1 for r in rows if r["_id"] not in existing)
        return {"inserted": inserted, "updated": len(rows) - inserted}

    async def upsert_prices(self, rows):
        if not rows:
            return {"inserted": 0, "updated": 0}
        return await self._run(self._upsert_prices, rows)

    def _find_prices(self, commodity, date_from, date_to, market_key, state):
        sql = f"SELECT id, {', '.join(PRICE_FIELDS)} FROM prices WHERE commodity = ?"
        args = [commodity]
        if date_from:
            sql += " AND date >= ?"; args.append(date_from)
        if date_to:
            sql += " AND date <= ?"; args.append(date_to)
        if market_key:
            sql += " AND market_key = ?"; args.append(market_key)
        if state:
            sql += " AND lower(state) = ?"; args.append(state.strip().lower())
        sql += " ORDER BY date"
        rows = []
        for r in self._conn.execute(sql, args):
            row = dict(r)
            row["_id"] = row.pop("id")
            row["flags"] = json.loads(row["flags"] or "[]")
            rows.append(row)
        return rows

    async def find_prices(self, commodity, date_from=None, date_to=None, market_key=None, state=None):
        return await self._run(self._find_prices, commodity, date_from, date_to, market_key, state)

    def _set_flags(self, flags_by_id):
        with self._conn:
            self._conn.executemany(
                "UPDATE prices SET flags = ? WHERE id = ?",
                [(json.dumps(flags), row_id) for row_id, flags in flags_by_id.items()],
            )

    async def set_flags(self, flags_by_id):
        if flags_by_id:
            await self._run(self._set_flags, flags_by_id)

    def _price_stats(self):
        by_source = {}
        for r in self._conn.execute(
                "SELECT source, COUNT(*) n, MIN(date) first, MAX(date) last FROM prices GROUP BY source"):
            by_source[r["source"]] = {"rows": r["n"], "earliest_date": r["first"], "latest_date": r["last"]}
        totals = self._conn.execute(
            "SELECT COUNT(*) n, COUNT(DISTINCT market_key) m, "
            "COUNT(DISTINCT market_key || '#' || commodity) s FROM prices").fetchone()
        flagged = self._conn.execute(
            "SELECT COUNT(*) FROM prices WHERE flags NOT IN ('[]', '')").fetchone()[0]
        per_commodity = {
            r["commodity"]: {"rows": r["n"], "markets": r["m"], "latest_date": r["last"]}
            for r in self._conn.execute(
                "SELECT commodity, COUNT(*) n, COUNT(DISTINCT market_key) m, MAX(date) last "
                "FROM prices GROUP BY commodity")
        }
        return {"rows": totals["n"], "markets": totals["m"], "series": totals["s"],
                "flagged_rows": flagged, "by_source": by_source, "by_commodity": per_commodity}

    async def price_stats(self):
        return await self._run(self._price_stats)

    def _duplicate_groups(self):
        cols = ", ".join(f"lower(trim({c}))" for c in NATURAL_KEY)
        return self._conn.execute(
            f"SELECT COUNT(*) FROM (SELECT 1 FROM prices GROUP BY {cols} HAVING COUNT(*) > 1)"
        ).fetchone()[0]

    async def duplicate_groups(self):
        return await self._run(self._duplicate_groups)

    # arrivals
    def _upsert_arrivals(self, rows):
        existing = self._existing_ids("arrivals", [r["_id"] for r in rows])
        with self._conn:
            self._conn.executemany(
                "INSERT INTO arrivals (id, date, commodity, level, doc) VALUES (?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET doc = excluded.doc",
                [(r["_id"], r["date"], r["commodity"], r.get("level"), json.dumps(r)) for r in rows],
            )
        inserted = sum(1 for r in rows if r["_id"] not in existing)
        return {"inserted": inserted, "updated": len(rows) - inserted}

    async def upsert_arrivals(self, rows):
        if not rows:
            return {"inserted": 0, "updated": 0}
        return await self._run(self._upsert_arrivals, rows)

    def _find_arrivals(self, commodity, date_from, date_to):
        sql, args = "SELECT doc FROM arrivals WHERE commodity = ?", [commodity]
        if date_from:
            sql += " AND date >= ?"; args.append(date_from)
        if date_to:
            sql += " AND date <= ?"; args.append(date_to)
        return [json.loads(r[0]) for r in self._conn.execute(sql + " ORDER BY date", args)]

    async def find_arrivals(self, commodity, date_from=None, date_to=None):
        return await self._run(self._find_arrivals, commodity, date_from, date_to)

    # masters and reports
    def _replace_master(self, kind, docs):
        with self._conn:
            self._conn.execute("DELETE FROM masters WHERE kind = ?", (kind,))
            self._conn.executemany(
                "INSERT INTO masters (kind, id, doc) VALUES (?,?,?)",
                [(kind, str(d["_id"]), json.dumps(d)) for d in docs],
            )

    async def replace_master(self, kind, docs):
        await self._run(self._replace_master, kind, docs)

    async def get_master(self, kind):
        return await self._run(lambda: [
            json.loads(r[0]) for r in self._conn.execute("SELECT doc FROM masters WHERE kind = ?", (kind,))
        ])

    def _add_ingest_report(self, doc):
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO ingest_reports (run_id, source, started_at, doc) VALUES (?,?,?,?)",
                (doc["run_id"], doc["source"], doc["started_at"], json.dumps(doc)),
            )

    async def add_ingest_report(self, doc):
        await self._run(self._add_ingest_report, doc)

    def _recent_ingest_reports(self, source, limit):
        sql, args = "SELECT doc FROM ingest_reports", []
        if source:
            sql += " WHERE source = ?"; args.append(source)
        sql += " ORDER BY started_at DESC LIMIT ?"; args.append(limit)
        return [json.loads(r[0]) for r in self._conn.execute(sql, args)]

    async def recent_ingest_reports(self, source=None, limit=10):
        return await self._run(self._recent_ingest_reports, source, limit)

    # signals and alerts
    def _weekly_market_medians(self, commodity, date_from):
        agg = MarketWeekAggregator()
        cursor = self._conn.execute(
            "SELECT market_key, state, date, variety, grade, source, modal_price, flags FROM prices "
            "WHERE commodity = ? AND date >= ? ORDER BY market_key, date", (commodity, date_from))
        for r in cursor:
            agg.add(dict(r))
        return agg.finish()

    async def weekly_market_medians(self, commodity, date_from):
        return await self._run(self._weekly_market_medians, commodity, date_from)

    def _replace_signals(self, commodity, docs):
        with self._conn:
            self._conn.execute("DELETE FROM signals WHERE commodity = ?", (commodity,))
            self._conn.executemany(
                "INSERT INTO signals (id, commodity, level, doc) VALUES (?,?,?,?)",
                [(d["_id"], d["commodity"], d["level"], json.dumps(d)) for d in docs],
            )

    async def replace_signals(self, commodity, docs):
        await self._run(self._replace_signals, commodity, docs)

    def _find_signals(self, commodity, level):
        sql, args = "SELECT doc FROM signals WHERE 1=1", []
        if commodity:
            sql += " AND commodity = ?"; args.append(commodity)
        if level:
            sql += " AND level = ?"; args.append(level)
        return [json.loads(r[0]) for r in self._conn.execute(sql, args)]

    async def find_signals(self, commodity=None, level=None):
        return await self._run(self._find_signals, commodity, level)

    def _insert_alert_if_new(self, alert, window_hours):
        recent = self._conn.execute(
            "SELECT 1 FROM alerts WHERE dedupe_key = ? AND created_at >= ? LIMIT 1",
            (alert["dedupe_key"], _window_start(window_hours))).fetchone()
        if recent:
            return False
        with self._conn:
            self._conn.execute(
                "INSERT INTO alerts (id, dedupe_key, commodity, created_at, doc) VALUES (?,?,?,?,?)",
                (alert["_id"], alert["dedupe_key"], alert["commodity"], alert["created_at"], json.dumps(alert)))
        return True

    async def insert_alert_if_new(self, alert, window_hours=24):
        return await self._run(self._insert_alert_if_new, alert, window_hours)

    def _find_alerts(self, since, commodity, limit):
        sql, args = "SELECT doc FROM alerts WHERE 1=1", []
        if since:
            sql += " AND created_at >= ?"; args.append(since)
        if commodity:
            sql += " AND commodity = ?"; args.append(commodity)
        sql += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
        return [json.loads(r[0]) for r in self._conn.execute(sql, args)]

    async def find_alerts(self, since=None, commodity=None, limit=200):
        return await self._run(self._find_alerts, since, commodity, limit)

    def close(self):
        self._conn.close()


# ─── MongoDB ───────────────────────────────────────────────
class MongoMandiStore(MandiStore):
    name = "mongodb"

    def __init__(self, db):
        self.prices = db["mandi_prices"]
        self.arrivals = db["mandi_arrivals"]
        self.masters = db["mandi_masters"]
        self.reports = db["mandi_ingest_reports"]
        self.signals = db["mandi_signals"]
        self.alerts = db["mandi_alerts"]
        self._indexed = False

    async def _ensure_indexes(self):
        if self._indexed:
            return
        await self.prices.create_index([("commodity", 1), ("date", 1)])
        await self.prices.create_index([("market_key", 1), ("commodity", 1), ("date", 1)])
        await self.arrivals.create_index([("commodity", 1), ("date", 1)])
        await self.reports.create_index([("source", 1), ("started_at", -1)])
        await self.alerts.create_index([("dedupe_key", 1), ("created_at", -1)])
        self._indexed = True

    async def _upsert(self, collection, rows):
        if not rows:
            return {"inserted": 0, "updated": 0}
        await self._ensure_indexes()
        ids = [r["_id"] for r in rows]
        existing = set()
        for start in range(0, len(ids), 1000):
            cursor = collection.find({"_id": {"$in": ids[start:start + 1000]}}, {"_id": 1})
            existing.update([doc["_id"] async for doc in cursor])
        # Concurrent single upserts in batches; the natural-key _id makes them idempotent.
        for start in range(0, len(rows), 200):
            await asyncio.gather(*(
                collection.replace_one({"_id": r["_id"]}, r, upsert=True)
                for r in rows[start:start + 200]
            ))
        inserted = sum(1 for r in rows if r["_id"] not in existing)
        return {"inserted": inserted, "updated": len(rows) - inserted}

    async def upsert_prices(self, rows):
        return await self._upsert(self.prices, rows)

    async def find_prices(self, commodity, date_from=None, date_to=None, market_key=None, state=None):
        query = {"commodity": commodity}
        date_range = {}
        if date_from:
            date_range["$gte"] = date_from
        if date_to:
            date_range["$lte"] = date_to
        if date_range:
            query["date"] = date_range
        if market_key:
            query["market_key"] = market_key
        if state:
            query["state"] = {"$regex": f"^{state.strip()}$", "$options": "i"}
        cursor = self.prices.find(query, {"raw": 0}).sort("date", 1)
        return [doc async for doc in cursor]

    async def set_flags(self, flags_by_id):
        items = list(flags_by_id.items())
        for start in range(0, len(items), 200):
            await asyncio.gather(*(
                self.prices.update_one({"_id": rid}, {"$set": {"flags": flags}})
                for rid, flags in items[start:start + 200]
            ))

    async def price_stats(self):
        by_source = {}
        async for g in self.prices.aggregate([{"$group": {
                "_id": "$source", "n": {"$sum": 1}, "first": {"$min": "$date"}, "last": {"$max": "$date"}}}]):
            by_source[g["_id"]] = {"rows": g["n"], "earliest_date": g["first"], "latest_date": g["last"]}
        per_commodity = {}
        async for g in self.prices.aggregate([{"$group": {
                "_id": "$commodity", "n": {"$sum": 1}, "markets": {"$addToSet": "$market_key"},
                "last": {"$max": "$date"}}}]):
            per_commodity[g["_id"]] = {"rows": g["n"], "markets": len(g["markets"]), "latest_date": g["last"]}
        markets = await self.prices.distinct("market_key")
        series = len([g async for g in self.prices.aggregate([
            {"$group": {"_id": {"m": "$market_key", "c": "$commodity"}}}])])
        flagged = await self.prices.count_documents({"flags.0": {"$exists": True}})
        return {"rows": sum(s["rows"] for s in by_source.values()), "markets": len(markets),
                "series": series, "flagged_rows": flagged, "by_source": by_source,
                "by_commodity": per_commodity}

    async def duplicate_groups(self):
        # Names are already trimmed by normalize.clean_text, so case-folding is enough.
        group_id = {field: {"$toLower": f"${field}"} for field in NATURAL_KEY}
        cursor = self.prices.aggregate([
            {"$group": {"_id": group_id, "n": {"$sum": 1}}},
            {"$match": {"n": {"$gt": 1}}},
        ])
        return len([doc async for doc in cursor])

    async def upsert_arrivals(self, rows):
        return await self._upsert(self.arrivals, rows)

    async def find_arrivals(self, commodity, date_from=None, date_to=None):
        query = {"commodity": commodity}
        if date_from or date_to:
            query["date"] = {k: v for k, v in (("$gte", date_from), ("$lte", date_to)) if v}
        return [doc async for doc in self.arrivals.find(query).sort("date", 1)]

    async def replace_master(self, kind, docs):
        await self.masters.delete_many({"kind": kind})
        if docs:
            await self.masters.insert_many([
                {**d, "_id": f"{kind}:{d['_id']}", "source_id": d["_id"], "kind": kind} for d in docs
            ])

    async def get_master(self, kind):
        docs = [doc async for doc in self.masters.find({"kind": kind})]
        for doc in docs:
            doc["_id"] = doc.pop("source_id")
            doc.pop("kind", None)
        return docs

    async def add_ingest_report(self, doc):
        await self._ensure_indexes()
        await self.reports.replace_one({"_id": doc["run_id"]}, {**doc, "_id": doc["run_id"]}, upsert=True)

    async def recent_ingest_reports(self, source=None, limit=10):
        query = {"source": source} if source else {}
        cursor = self.reports.find(query, {"_id": 0}).sort("started_at", -1).limit(limit)
        return [doc async for doc in cursor]

    async def weekly_market_medians(self, commodity, date_from):
        agg = MarketWeekAggregator()
        cursor = self.prices.find(
            {"commodity": commodity, "date": {"$gte": date_from}},
            {"market_key": 1, "state": 1, "date": 1, "variety": 1, "grade": 1,
             "source": 1, "modal_price": 1, "flags": 1},
        ).sort([("market_key", 1), ("date", 1)])
        async for row in cursor:
            agg.add(row)
        return agg.finish()

    async def replace_signals(self, commodity, docs):
        await self.signals.delete_many({"commodity": commodity})
        if docs:
            await self.signals.insert_many([dict(d) for d in docs])

    async def find_signals(self, commodity=None, level=None):
        query = {k: v for k, v in (("commodity", commodity), ("level", level)) if v}
        return [doc async for doc in self.signals.find(query)]

    async def insert_alert_if_new(self, alert, window_hours=24):
        recent = await self.alerts.find_one({
            "dedupe_key": alert["dedupe_key"], "created_at": {"$gte": _window_start(window_hours)}})
        if recent:
            return False
        await self.alerts.insert_one(dict(alert))
        return True

    async def find_alerts(self, since=None, commodity=None, limit=200):
        query = {}
        if since:
            query["created_at"] = {"$gte": since}
        if commodity:
            query["commodity"] = commodity
        cursor = self.alerts.find(query).sort("created_at", -1).limit(limit)
        return [doc async for doc in cursor]


# ─── Store selection ───────────────────────────────────────
_store: MandiStore = None
_store_lock = asyncio.Lock()


async def _mongo_reachable() -> bool:
    from config.database import ping_database

    try:
        await ping_database()
        return True
    except Exception:
        return False


async def get_store() -> MandiStore:
    """
    Pick the backend once per process (MANDI_STORE=auto|mongo|sqlite) and keep it,
    so a flapping MongoDB connection never splits one day's rows across two stores.
    """
    global _store
    if _store is not None:
        return _store
    async with _store_lock:
        if _store is None:
            mode = config.store_mode()
            if mode == "mongo" or (mode == "auto" and await _mongo_reachable()):
                from config.database import db
                _store = MongoMandiStore(db)
            else:
                _store = SqliteMandiStore()
    return _store


def set_store(store: MandiStore) -> None:
    """Override the active store (used by tests and the CLI)."""
    global _store
    _store = store
