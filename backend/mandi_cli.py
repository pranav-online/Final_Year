"""
Run mandi data jobs by hand (from the backend/ folder, with the venv active):

    python mandi_cli.py masters                 # Agmarknet commodity/state masters
    python mandi_cli.py prices [--commodity tomato onion]
    python mandi_cli.py arrivals                # national arrivals (Agmarknet dashboard)
    python mandi_cli.py backfill --from 2018-01-01 [--commodity onion] [--state Maharashtra]
    python mandi_cli.py ceda-probe              # does CEDA expose market-level arrivals?
    python mandi_cli.py signals                 # recompute signals and raise alerts now
    python mandi_cli.py train                   # backtest, train, promote only if the gate passes
    python mandi_cli.py forecast                # write P10/P50/P90 forecasts with the promoted model
    python mandi_cli.py health                  # same payload as GET /health/data
    python mandi_cli.py schedule                # run only the mandi scheduler (ingest, signals,
                                                # forecasts) without the API's PyTorch models; Ctrl+C to stop
"""
import argparse
import asyncio
import json
import logging
from datetime import date

from services.mandi import ingest
from services.mandi.analytics import data_health
from services.mandi.config import resolve_commodity
from services.mandi.store import get_store


def _commodities(names):
    if not names:
        return None
    ids = [resolve_commodity(n) for n in names]
    unknown = [n for n, cid in zip(names, ids) if cid is None]
    if unknown:
        raise SystemExit(f"Unknown commodity: {', '.join(unknown)}")
    return ids


async def main(args) -> dict:
    store = await get_store()
    if args.job == "masters":
        return await ingest.seed_masters(store)
    if args.job == "prices":
        return await ingest.ingest_prices(store, commodities=_commodities(args.commodity))
    if args.job == "arrivals":
        return await ingest.ingest_arrivals(store)
    if args.job == "backfill":
        return await ingest.backfill_ceda(
            store, commodities=_commodities(args.commodity), states=args.state or None,
            from_date=date.fromisoformat(args.from_date),
            to_date=date.fromisoformat(args.to_date) if args.to_date else None,
        )
    if args.job == "ceda-probe":
        return await ingest.probe_ceda_arrivals()
    if args.job == "signals":
        from services.mandi import insights
        return await insights.refresh(store)
    if args.job == "train":
        from services.mandi import forecast
        result = await forecast.train_and_evaluate(store)
        await forecast.run_forecasts(store)
        return result
    if args.job == "forecast":
        from services.mandi import forecast
        return await forecast.run_forecasts(store)
    if args.job == "schedule":
        return await run_scheduler_forever()
    return await data_health(store)


async def run_scheduler_forever() -> dict:
    from services.mandi.scheduler import scheduler_status, shutdown_scheduler, start_scheduler

    if start_scheduler() is None:
        return {"started": False,
                "reason": "SCHEDULER_ENABLED is off, or another process (e.g. the API server) holds the lock"}
    logging.getLogger("alip").info("scheduler running: %s", scheduler_status()["jobs"])
    try:
        await asyncio.Event().wait()
    finally:
        shutdown_scheduler()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALIP mandi data jobs")
    parser.add_argument("job", choices=["masters", "prices", "arrivals", "backfill", "ceda-probe", "signals", "train", "forecast", "health", "schedule"])
    parser.add_argument("--commodity", nargs="*", help="limit to these commodities")
    parser.add_argument("--state", nargs="*", help="backfill states (default: the app's home states)")
    parser.add_argument("--from", dest="from_date", default="2018-01-01")
    parser.add_argument("--to", dest="to_date")
    # Progress goes to stderr so stdout stays pure JSON.
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("alip").setLevel(logging.INFO)
    result = asyncio.run(main(parser.parse_args()))
    print(json.dumps(result, indent=2, default=str))
