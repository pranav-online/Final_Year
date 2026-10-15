"""
Recurring ingestion jobs (APScheduler 3.x, inside the FastAPI process).

Every uvicorn worker that starts the scheduler fires every job, so run with
SCHEDULER_ENABLED=1 on exactly one worker (or one process) and 0 elsewhere.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from services.mandi import config, ingest, insights
from services.mandi.store import get_store

log = logging.getLogger("alip.mandi.scheduler")

_scheduler: AsyncIOScheduler = None

JOBS = {
    "ingest_prices": ingest.ingest_prices,
    "ingest_arrivals": ingest.ingest_arrivals,
    "seed_masters": ingest.seed_masters,
}


async def run_job(name: str) -> None:
    try:
        report = await JOBS[name]()
        log.info("mandi job %s finished: %s", name, report.get("status"))
        if name in {"ingest_prices", "ingest_arrivals"}:
            await insights.refresh()  # new data -> recompute signals, raise alerts
    except Exception:  # a failed job must never take the API down
        log.exception("mandi job %s crashed", name)


async def startup_catch_up() -> None:
    """Seed masters if missing, and pull prices if today's feed has not been captured yet."""
    store = await get_store()
    if not await store.get_master("agmarknet_commodity"):
        await run_job("seed_masters")
    reports = await store.recent_ingest_reports("datagov", 10)
    today_utc = datetime.now(timezone.utc).date().isoformat()  # started_at is stored in UTC
    scope = set(config.scoped_commodities())
    if not any(r.get("status") in {"ok", "warning"}
               and r.get("started_at", "").startswith(today_utc)
               and scope <= set(r.get("commodities") or [])
               for r in reports):
        await run_job("ingest_prices")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(
        timezone=config.SCHEDULER_TIMEZONE,
        job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 3600},
    )
    # data.gov.in only holds the current day: it is wiped overnight and refills
    # during the day (only 14 rows were present at 06:50 IST when observed live).
    # A day missed by the evening pulls is lost for good, so pull several times
    # from mid-afternoon to late night; upserts make the repeats harmless.
    for hour, minute in ((14, 30), (17, 30), (20, 30), (23, 30)):
        scheduler.add_job(run_job, CronTrigger(hour=hour, minute=minute), args=["ingest_prices"],
                          id=f"ingest_prices_{hour:02d}{minute:02d}")
    scheduler.add_job(run_job, CronTrigger(hour=16, minute=30), args=["ingest_arrivals"], id="ingest_arrivals_1630")
    scheduler.add_job(run_job, CronTrigger(day_of_week="sun", hour=3, minute=0), args=["seed_masters"], id="seed_masters_weekly")
    first_run = datetime.now(ZoneInfo(config.SCHEDULER_TIMEZONE)) + timedelta(seconds=60)
    scheduler.add_job(startup_catch_up, DateTrigger(run_date=first_run), id="startup_catch_up")
    return scheduler


def _configure_logging() -> None:
    """Make job progress visible in the uvicorn console (INFO for the alip.* loggers)."""
    logger = logging.getLogger("alip")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # avoid double lines when the root logger also has a handler


LOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "scheduler.lock"
_lock_handle = None


def acquire_singleton_lock(path: Path = LOCK_PATH):
    """
    Non-blocking OS file lock. `uvicorn --workers N` gives every worker the same
    environment, so only the worker holding this lock may run the scheduler.
    The OS releases it automatically when the process exits.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def start_scheduler():
    global _scheduler, _lock_handle
    if not config.scheduler_enabled() or _scheduler is not None:
        return _scheduler
    _configure_logging()
    _lock_handle = acquire_singleton_lock()
    if _lock_handle is None:
        log.info("mandi scheduler not started: another process holds %s", LOCK_PATH)
        return None
    _scheduler = build_scheduler()
    _scheduler.start()
    log.info("mandi scheduler started with %d jobs", len(_scheduler.get_jobs()))
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler, _lock_handle
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _lock_handle is not None:
        _lock_handle.close()
        _lock_handle = None


def scheduler_status() -> dict:
    if _scheduler is None:
        return {"enabled": config.scheduler_enabled(), "running": False, "jobs": []}
    return {
        "enabled": True,
        "running": _scheduler.running,
        "jobs": [
            {"id": job.id, "next_run": job.next_run_time.isoformat() if job.next_run_time else None}
            for job in _scheduler.get_jobs()
        ],
    }
