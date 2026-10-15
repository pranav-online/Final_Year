"""
Mandi (agricultural market) price and arrival data pipeline.

config    - commodity scope, source names, aliases, API keys
normalize - cleaning / validation of raw source rows
sources   - HTTP clients for data.gov.in, Agmarknet 2.0 and CEDA
store     - storage repository (MongoDB, with a SQLite fallback)
ingest    - ingestion jobs (daily prices, national arrivals, masters, backfill)
analytics - read-side helpers (weekly price history, market lists)
scheduler - APScheduler wiring for the recurring jobs
"""
