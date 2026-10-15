# Broker Demand Analysis: Indian Agri Broker Needs, Comparable Products, Dashboard Design and Reference Architecture

Research date: 2026-10-15. 16 tool calls (searches and fetches). The notes cover the six key questions. Architecture recommendations are mostly design inferences built from cited platform constraints. They are marked as inferences, not as sourced facts.

## Q1. What does an Indian agri broker or commission agent do day to day, what risks do they face, and what information do they lack?

### Takeaway
Arhtiyas act as transaction intermediaries in the mandi. They clean, weigh and sell produce, route payments, and collect a 2–4% commission. They are also informal lenders whose credit ties farmers to them. Their decisions depend on local arrivals and buyer demand, and their biggest risks are sudden price crashes caused by gluts in perishables (tomato, onion, potato). A broker tool that adds value would therefore help with timing and mandi choice (arrival surges, cross-mandi spreads net of transport) and with sourcing (which farmers have which crop). It would not replace the broker's relationship role.

### Cited Findings
- The arhtiya's main role in Indian APMC mandis is to facilitate transactions between farmers and buyers. They also act as moneylenders, which creates interlinked credit and output markets. The more influential party in an interlinked transaction captures more of the benefit. — [Ideas for India (Kumar et al. summary)](https://www.ideasforindia.in/topics/agriculture/addressing-the-economic-trade-offs-of-interlinkages-in-contemporary-agrarian-markets)
- The commission agent "sorts, cleans, weighs and sells the produce the farmers bring to the mandis". In Punjab, the APMC Act makes buyers pay the commission, but farmer payments often flow through the agent. — [Business Standard via PressReader](https://www.pressreader.com/india/business-standard/20201008/281818581293354)
- A farmer who takes an advance is bound to sell the crop to the same agent. Commission runs 2–4% depending on crop and client. This evidence comes from Pakistan's Punjab, where the system is structurally similar to the Indian one. — [PIDE study](https://pide.org.pk/research/the-role-of-arthi-in-agriculture-marketing-an-exploiter-or-facilitator-of-farmers/); [IGC Haq et al. 2013](https://www.theigc.org/wp-content/uploads/2014/09/Haq-Et-Al-2013-Working-Paper.pdf)
- Agents provide inputs on credit in the sowing season and act as sellers at harvest. — [PIDE working paper](https://file.pide.org.pk/uploads/par-vol2i10-12-role-of-the-middle-man-and-neglected-aspects.pdf)
- In Harda (MP), kacha arhatiyas were removed from the grain mandi in the early 1980s. In fruit and vegetable markets, though, they still control the sabzi mandi through credit advanced to both sellers and buyers. — [CASI UPenn](https://casi.sas.upenn.edu/node/247)
- Margin structure: RBI Working Paper 08/2024 finds that farmers receive about 33% of the consumer rupee for tomato, 36% for onion and 37% for potato. Wholesalers and retailers take the rest. For dairy the farmer share is about 70%. — [Business Standard](https://www.business-standard.com/amp/markets/capital-market-news/rbi-study-shows-tomato-onion-and-potato-farmers-get-only-a-third-of-retail-price-that-consumer-pays-124100400307_1.html); [RBI WPS 8/2024 PDF](https://website.rbi.org.in/documents/87730/30842423/WPS+No.+8%2C+2024+-+Vegetables+Inflation+in+India.pdf)
- The same RBI paper finds a significant negative relation between monthly availability, or the availability-to-usage ratio, and TOP prices. SARIMAX models that include supply "balance-sheet" variables forecast better. In short, arrivals and supply data predict price. — [Drishti IAS summary of RBI paper](https://www.drishtiias.com/daily-updates/daily-news-analysis/middlemen-gain-as-farmers-earn-less-in-agri-produce-rbi/print_manually)
- In FPO channels in Kurnool (AP), the producer's share of the consumer rupee was 88.96% in the shortest channel, higher than for non-FPO farmers, because transaction costs and margins were lower. — [SASAPJAS study](https://sasapjas.org/abstract/study-on-farmers-access-to-markets-through-fpos-in-kurnool-district-of-andhra-pradesh)
- In a Wardha banana channel running through commission agents, wholesalers and retailers, producers got 42.40% of the consumer rupee. — [AgEcon Search](https://ageconsearch.umn.edu/record/367613/files/Sonu4192023AJAEES103369.pdf)
- Price-crash risk examples:
  - MP onions in June 2025 sold at or below Rs 1/kg against a production cost of Rs 12–15/kg. — [Global Agriculture](https://www.global-agriculture.com/india-region/onion-mandi-prices-crash-in-madhya-pradesh-farmers-unable-to-recover-even-transportation-costs/)
  - Indore-region onions fell to Rs 5–8/kg after unseasonal rain. — [Free Press Journal](https://www.freepressjournal.in/amp/bhopal/mps-unseasonal-rainfall-wrecks-onion-crops-mandi-prices-drop-to-58kg-farmers-demand-relief)
  - Chhindwara tomatoes fell from more than Rs 200/kg to about Rs 2/kg (January 2025). Officials blamed "surplus supply and low demand". — [ETV Bharat](https://etvbharat.com/en/!state/tomato-and-cauliflower-prices-crash-in-madhya-pradesh-enn25010402109)
  - Karnataka in November 2025 saw tomato prices rise as rain cut supply while onion prices fell, so the risk can run in both directions at the same time. — [Deccan Herald](https://www.deccanherald.com/india/karnataka/tomato-prices-skyrocket-as-excess-rains-hit-supply-onion-prices-crash-3815362)
  - AP tomatoes went from Rs 218/kg wholesale to Rs 11/kg after farmers planted heavily following a spike. This report is undated. — [FreshPlaza](https://www.freshplaza.com/north-america/article/9554432/indian-tomato-farmers-faced-with-losses-as-glut-crashes-prices/)

### Inferences
- The broker's real decisions break down as follows. The first two depend most directly on arrivals data.
  1. Which commodity to deal in this week (demand vs supply).
  2. Which mandi to sell in (price spread minus transport and commission).
  3. When to buy and sell (forecast direction and volatility).
  4. How much to hold (perishability, storage and credit cost).
  5. Which farmers to source from (crop, quantity, distance, quality, existing credit ties).
  6. Counterparty and payment risk.
- Information the broker lacks today:
  - Forward-looking supply, meaning upcoming arrivals and the harvest pipeline from farmers who have not yet come to the mandi.
  - Cross-mandi prices net of transport.
  - Early warning of gluts.
  - A structured view of farmer listings beyond their personal network.
- Perishables (TOP, other vegetables) need short-horizon signals of 1–7 days. Storables (onion in storage, grains, pulses) can use 2–4 week horizons and hold/sell signals.
- Stocking advice must account for the perishability class. For tomatoes, "hold" is rarely viable without cold storage.

### Gaps
- I found no 2025–26 primary survey of Indian arhtiyas' daily decision workflow. The workflow above is synthesised from academic and journalistic descriptions.
- NABARD, World Bank and ICRIER reports on intermediaries were not retrieved. Searches returned other price-spread studies instead.
- I found no quantified data on how much transport costs per tonne-km eat into broker margins.

## Q2. Which products and services serve brokers, traders and FPO buyers, and which features do users value?

### Takeaway
The market splits into four groups:
- Government price-information and trading rails (Agmarknet 2.0, eNAM, UPAg).
- B2B marketplaces and supply chains (Ninjacart, AgriBazaar, DeHaat, Kisan Network).
- Post-harvest warehousing and finance (Arya.ag).
- Many simple mandi-bhav apps.

The common features are daily prices by state, district and market, multi-mandi comparison, price and bid alerts (SMS or push), multilingual UI, and historical graphs. Forecasts with uncertainty and demand-supply gap views are rarely offered to small brokers, which is the opening for this project.

### Cited Findings
- **eNAM**
  - Scale: 1,522 mandis by 30 June 2025, with 1.79 crore farmers and 2.67 lakh traders registered. — [Indian Cooperative](https://www.indiancooperative.com/co-op-news-snippets/over-1-79-crore-farmers-registered-on-e-nam/amp)
  - By March 2026: 1,656 mandis in 23 states and 4 UTs. — [PIB document Apr 2026](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/apr/doc2026413845801.pdf)
  - Features: a single trading licence across mandis, an online payment facility for traders, and a mobile app with prices for nearby eNAM and non-eNAM mandis, lot tracking, and SMS alerts on final bid and payment. — [Lok Sabha reply, Mar 2025](https://sfacindia.com/UploadFile/Statistics/LS%20Qus%20No.%20U11382%20dt.%2020.03.2025.pdf); [Drishti IAS Oct 2025](https://www.drishtiias.com/daily-updates/daily-news-analysis/expansion-of-national-agriculture-market-e-nam/print_manually)
  - Commodity grading parameters are set by the Directorate of Marketing & Inspection. — [Drishti IAS](https://www.drishtiias.com/daily-updates/daily-news-analysis/expansion-of-national-agriculture-market-e-nam/print_manually)
  - Critique: about 20% of APMCs are integrated, and Karnataka, Maharashtra and TN run parallel state platforms. This comes from a study-material site, so treat it with caution. — [anantamias](https://anantamias.com/national-agricultural-market-e-nam/)
- **Agmarknet 2.0**
  - The portal was upgraded to 2.0 in November 2025, with about 4,367 mandis linked for real-time prices. An Agmarknet 2.0 mobile app was also launched. — [Global Agriculture](https://www.global-agriculture.com/india-region/agmarknet-and-e-nam-empower-farmers-with-real-time-mandi-price-information/)
  - The Ministry directs users to the Agmarknet 2.0 Dashboard or the UPAg portal for daily price and arrival reports. — [india.gov.in](https://www.india.gov.in/category/agriculture-rural-environment/subcategory/agricultural-produce/details/prices-arrival-reports-agmarknet)
  - Agmarknet covers about 300 commodities and 2,000 varieties, with daily prices and arrivals. — [Arthapedia (IES)](https://ies.gov.in/arthapedia/concept/agricultural-marketing-information-network-agmarknet)
  - UPAg aggregates prices, production, area, yield and trade, mainly for policymakers. — [Manorama Yearbook](https://www.manoramayearbook.in/current-affairs/india/2023/09/18/unified-portal-for-agricultural-statistics-upag.html)
- **Ninjacart:** B2B fresh-produce supply chain linking farmers with retailers and restaurants. Listed features are real-time demand-supply matching, AI-driven inventory and logistics, and farm-gate quality grading. It reportedly moved into agri-fintech and lending in 2025. This comes from a secondary blog. — [Decentro blog](https://decentro.tech/blog/agritech-startups/)
- **DeHaat:** Full-stack platform covering inputs, advisory and market access. It serves micro-entrepreneurs and institutional buyers. — [Decentro blog](https://decentro.tech/blog/agritech-startups/)
- **Arya.ag**
  - Post-harvest platform: warehousing, warehouse-receipt finance, and market linkage. It does not trade itself. It connects farmers, FPOs and small aggregators with mills, traders and corporates. — [Bitscale profile](https://bitscale.ai/directory/aryaag)
  - It acquired the AI agri-data firm Prakshep in June 2022 for crop monitoring, quality assaying and surveillance. — [Krishi Jagran](https://krishijagran.com/industry-news/aryaag-acquires-autonomous-ai-agritech-player-prakshep/?amp=1)
  - A Series D round of Rs 725 crore was reported for January 2026. This comes from a secondary source. — [agrijob.in](https://www.agrijob.in/?p=3045)
- **AgriBazaar:** Calls itself India's first and largest private electronic mandi. It operates in 25+ states with auctions, warehousing, secured payments, quality testing and price discovery for buyers ranging from MNCs to small firms. — [Wellfound](https://wellfound.com/company/agribazaar-1); [Affle case study](https://enterprise.affle.com/casestudies/commodity-trading-platform/)
- **Kisan Network:** A YC-backed marketplace where farmers post crop photos and availability, and buyers browse listings and pay at delivery. It took a 5–15% commission. Its current status is unclear: one profile says active, another says closed. — [TechCrunch 2016](https://techcrunch.com/2016/03/09/y-combinator-backed-kisan-network-is-transforming-the-rural-indian-agricultural-market); [YC blog](https://www.ycombinator.com/blog/kisan-network-yc-w16-is-an-online-marketplace-for-indian-agriculture/)
- **Mandi-bhav apps**
  - APMC Gujarat Mandi Bhav: notifications when new rates post, comparison across yards, Gujarati/Hindi/English. — [marlvel listing](https://marlvel.ai/api/llm/apps/finance/apmc-gujarat-mandi-bhav)
  - NaPanta: free price alerts. — [NaPanta](https://www.napanta.com/agri-commodity-prices/odisha/mango/26-Jun-2026/)
  - Gramseva: offline access, daily sync, historical graphs. — [HortiDaily](https://www.hortidaily.com/article/9183432/checking-vegetable-prices-on-your-mobile-phone/)
  - ACROP: refreshes Agmarknet data every 6 hours on working days for 4,170–4,331 markets. Some markets report with a 1-day delay. — [acrop.app](https://acrop.app/mandi)

### Inferences
- Table-stakes features that users expect from any app:
  - Daily min, max and modal price by mandi.
  - Favourites and watchlists.
  - Multi-mandi comparison.
  - Push or SMS alerts.
  - Vernacular UI.
  - Historical chart.
  - Offline-tolerant reads.
- Differentiators for a broker module:
  - Arrival-surge alerts, which serve as a leading indicator of crashes per the RBI availability finding.
  - Net-of-transport best-mandi ranking.
  - Forecast with an uncertainty band.
  - Demand-supply gap linked to the app's own farmer listings, which gives a supply pipeline that Agmarknet lacks.
  - Buy/hold/sell guidance that accounts for perishability.
- "Demand" is hard to observe directly from public data. Proxies are price momentum relative to arrivals (rising price with steady or high arrivals means strong demand), buyer requests on the platform, and seasonal norms.

### Gaps
- I found no reliable Kalgudi feature information.
- I found no user-research or ratings data ranking which features traders value most. The value ranking above is inferred from feature prevalence.
- Ninjacart and DeHaat feature claims come from secondary blogs, not from the companies' own sites.
- I could not confirm NCDEX-linked retail tools for small brokers in 2026.

## Q3. What actionable outputs should a broker demand dashboard show, and how should uncertainty be communicated?

### Takeaway
Lead with decisions, not charts:
- A ranked "where to sell" list net of costs.
- A buy/hold/sell signal with a plain-language reason and a confidence label.
- Alerts for arrival surges and price spikes.
- Matched farmer listings.
- Expected margin as a range.

For forecasts, use a fan chart or shaded band with a median line. Recent evidence finds that non-experts understand fan charts best and that a median line helps.

### Cited Findings
- A 2026 Bank of England working paper by McMahon et al. tested fan charts, dot plots, box plots, speedometers and ranges. Fan charts were the format participants most readily understood, and they conveyed both the central expectation and the uncertainty. In a second stage with 1,600 UK participants, fan charts reduced loss of trust after forecast errors. The public consistently underestimates uncertainty, and fan charts help correct this. — [Bank of England WP 2026](https://www.bankofengland.co.uk/working-paper/2026/anchors-aweigh-the-effect-of-communicating-forecast-uncertainty)
- An eye-tracking study comparing boxplots, fan plots and spaghetti plots found that adding a median line reduced fixations, meaning easier reading. More expert participants made more accurate decisions. — [Geoscience Communication 2023](https://gc.copernicus.org/articles/6/111/2023/gc-6-111-2023.pdf)
- Across 138 experts and non-experts, decisions did not differ consistently by representation, but how much uncertainty people perceived did vary by format. Non-experts inferred less uncertainty than experts. — [Univ. Reading manuscript](https://reading-clone.eprints-hosting.org/85132/1/accepted_manuscript.pdf)
- The literature has no consistent single recommendation, and communication should be tailored to the audience. — [EGUsphere preprint 2022](https://egusphere.copernicus.org/preprints/2022/egusphere-2022-929/egusphere-2022-929-manuscript-version5.pdf)
- Arrivals are a key price driver: higher availability relative to usage means lower price. — [RBI WPS 8/2024](https://website.rbi.org.in/documents/87730/30842423/WPS+No.+8%2C+2024+-+Vegetables+Inflation+in+India.pdf)
- Example: Azadpur tomato prices fell about 50%, from Rs 5,883 to Rs 2,969 per quintal, on increased arrivals. The date is unclear. — [Global Agriculture](https://www.global-agriculture.com/india-region/farmers-struggle-with-fluctuating-prices-a-look-at-onion-potato-and-tomato-markets/)

### Inferences (proposed dashboard elements, in priority order)
1. **Today's action cards**, one per watched commodity.
   - Signal: BUY, HOLD or SELL.
   - Plain reason, for example: "Arrivals at Azadpur 2.1x the 4-week average; price likely to fall 8–15% this week."
   - Confidence chip: High, Medium or Low, mapped from interval width and backtest accuracy.
   - Signal rule sketch:
     - P(price in 7 days > today + holding cost) > 0.6 gives HOLD/BUY.
     - Below 0.4 gives SELL.
     - Otherwise "No clear signal".
     - For perishables, cap the hold horizon by shelf life.
2. **Best mandi to sell in.** Rank mandis within a radius by `net = modal_price − transport_cost(distance × Rs/qtl-km) − commission% − market fee%`. Show the net Rs/qtl and the distance. Let the user edit the per-km rate.
3. **Demand–supply gap heatmap** (commodity × region or mandi). Colour by arrival anomaly (z-score vs the same week in prior years or a rolling 28-day window) and price momentum. Show a choropleth or district markers with react-leaflet, plus a table fallback.
4. **Forecast chart.** Show history line, median forecast, 50% and 80% shaded bands (fan), and a "today" divider. Hover text should say, for example: "8 in 10 times, price should land between Rs 1,800–2,300".
5. **Alerts feed.** Cover price spike or crash (|Δ| > k·σ, or >X% day-on-day), arrival surge (>2× rolling median), forecast-crossing of a user's target price, and new farmer listings matching demand.
6. **Matched farmer listings.** Rank listings by commodity in high demand, distance, quantity, quality grade and availability date. Each listing gets a "Contact" or "Make offer" action.
7. **Expected margin** shown as a range (P10–P90), not a point. Formula: buy price → forecast sell price minus transport, commission, spoilage % and storage.
8. **Data-freshness badge**, for example "Prices as of 14 Oct, 18:00; 3 mandis not reported". This matters because Agmarknet has reporting lags of up to 1 day.

Uncertainty communication rules for non-technical users:
- Use ranges in Rs with "8 in 10 chance" wording, not "80% PI".
- Use a traffic-light confidence chip.
- Always show the median line.
- Hide the forecast when the model is worse than the naive baseline for that series. Show "Not enough data" instead of a false signal.
- Provide Hindi and regional-language labels.

### Gaps
- I found no India-specific usability study on how mandi traders read forecast charts.
- Transport cost norms (Rs per quintal-km) by region were not found. They should be made a configurable parameter.

## Q4. What reference architecture fits a single FastAPI service with MongoDB (and a JSON-file fallback) and a React frontend?

### Takeaway
Run one FastAPI process with an in-process APScheduler (3.x AsyncIOScheduler, started in lifespan) for ingestion, feature computation and nightly retraining. Use MongoDB time-series collections for daily prices and arrivals (granularity "hours", metaField = {commodity, state, district, market}) and normal collections for forecasts, alerts, model registry and listings. Put a repository abstraction in front so a JSON-file store can stand in when Mongo is down. Expose REST endpoints with simple TTL caching. For freshness, use polling or SSE into the existing notifications route; WebSockets are not needed.

### Cited Findings
- **Data source**
  - The data.gov.in resource "Current Daily Price of Various Commodities from Various Markets (Mandi)" provides daily wholesale min, max and modal prices from Agmarknet. Search snippets of the catalogue page state "The API for this resource does not exist... click 'Request API'". The page returned 403 to my fetch, so I could not confirm its current status. — [data.gov.in resource](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)
  - Third-party tools describe resource ID `9ef84268-d588-465a-a308-a864a43d0070`, queried at `api.data.gov.in/resource/<id>` with an API key. Fields are state, district, market, commodity, variety, grade, arrival_date, min_price, max_price and modal_price. This contradicts the catalogue note, so the team should test it live. — [PolicyLayer tool description](https://policylayer.com/tools/io-github-pipeworx-io-data-gov-in/resource-data); [datagovindia PyPI](https://pypi.org/project/datagovindia/0.4)
  - The Agmarknet MCP server falls back to sample data when the live API or key is unavailable. — [Glama](https://glama.ai/mcp/servers/Krishna-Baldwa/agmarket-mcp)
  - Ashoka CEDA hosts a cleaned Agmarknet price and arrival dataset, which is useful for historical backfill. — [CEDA Agmarknet README](https://agmarknet.ceda.ashoka.edu.in/README.html)
- **MongoDB time-series collections**
  - `timeField` is required. `metaField` partitions data into buckets and cannot be redefined later.
  - `granularity` options are seconds, minutes and hours, with maximum bucket spans of 1 hour, 24 hours and 30 days respectively. Choose the value closest to the interval between measurements for the same metaField value. — [MongoDB docs](https://mongodb.com/docs/v5.0/core/timeseries-collections); [Considerations](https://mongodb.com/docs/manual/core/timeseries/timeseries-considerations)
  - The metaField should be stable, rarely change, and hold identifiers used in filters. Avoid arrays as metaField. High-cardinality or frequently changing metaField values create sparse buckets. — [MongoDB considerations](https://mongodb.com/docs/manual/core/timeseries/timeseries-considerations)
  - Timestamps outside 1970–2038 skip optimisations. A secondary index on timeField restores query performance. — [MongoDB docs](https://mongodb.com/docs/v5.0/core/timeseries-collections)
- **APScheduler and FastAPI**
  - The common pattern starts an AsyncIOScheduler in the FastAPI lifespan context. With N gunicorn/uvicorn workers, every job fires N times. Fixes are a single process, a DB lock, or a separate scheduler process. — [fixdevs](https://fixdevs.com/blog/apscheduler-not-working/); [codingstairs](https://codingstairs.duckdns.org/en/notes/backend/07-jobs-apscheduler)
  - Use `max_instances=1` and `coalesce=True` to prevent overlapping or stacked runs. Pin APScheduler 3.x, because 4.x changes the API. — [fixdevs](https://fixdevs.com/blog/apscheduler-not-working/)
- **Real-time delivery**
  - SSE is one-way and reconnects automatically, and is simpler for display-only dashboards. WebSocket is bidirectional and only worth it for interactive commands. Polling is simplest but generates the most requests. — [OneUptime blog](https://oneuptime.com/blog/post/2026-01-25-build-realtime-dashboards-fastapi/markdown)
  - Newer FastAPI documents `fastapi.sse.EventSourceResponse` with automatic 15 s keep-alives. Version not verified. `sse-starlette` is the third-party alternative. — [FastAPI SSE docs (Mintlify mirror)](https://mintlify.com/fastapi/fastapi/advanced/server-sent-events); [clay-atlas](https://clay-atlas.com/us/blog/2024/11/02/en-python-fastapi-server-sent-events-sse/)

### Inferences (proposed design)

**Layering (single repo, single FastAPI service):**
```
backend/
  app/main.py            # lifespan: init db, start scheduler (only if SCHEDULER_ENABLED=1)
  app/db/                # repository interface + MongoRepo + JsonFileRepo (fallback)
  app/ingest/            # agmarknet_client.py (data.gov.in, key from env), csv_backfill.py, normalise.py
  app/features/          # rolling stats, arrival z-scores, momentum, seasonality index, mandi distances
  app/models/            # baselines.py, forecaster.py (SARIMAX/Prophet/LightGBM quantile), registry.py
  app/services/          # signals.py, best_mandi.py, matching.py, alerts.py
  app/api/routes/        # demand.py, forecasts.py, alerts.py, matches.py (+ existing notifications.py)
  app/scheduler.py       # APScheduler 3.x AsyncIOScheduler jobs
frontend/src/features/broker-demand/ ...
```

**Scheduled jobs (IST timezone, `max_instances=1`, `coalesce=True`, `misfire_grace_time`):**

| Job | Trigger | Action |
|---|---|---|
| `ingest_prices` | every 3h from 10:00 to 22:00 IST, plus a 06:00 catch-up for the previous day | page through the API with `filters[arrival_date]`, upsert into `raw_prices` with a dedupe key |
| `compute_features` | after ingest | update `daily_market_stats` and arrival anomalies |
| `run_alerts` | after features | write to `alerts` and `notifications` |
| `forecast_daily` | 23:00 | predict for watched (commodity, market) series |
| `retrain_weekly` | Sunday 02:00 | retrain, backtest against baselines, register a new version, promote only if better |

Use a `job_locks` document with `findOneAndUpdate` and an expiry so that running with multiple workers stays safe. Also use a `SCHEDULER_ENABLED` env var.

**MongoDB collections:**
- `price_observations`: time-series collection, `timeField: "date"`, `metaField: "meta"`, where meta = {commodity, variety, state, district, market}, and `granularity: "hours"` because the data is daily. Measurements are min_price, max_price, modal_price (Rs/quintal), arrivals_tonnes (when available), grade, source and ingested_at.
  - Indexes: `{"meta.commodity":1,"meta.market":1,"date":-1}` and `{"meta.state":1,"meta.commodity":1,"date":-1}`.
  - Deduping happens before insert, because time-series collections do not support unique indexes. The ingest step checks a separate `ingest_keys` collection with a unique index on `commodity|variety|market|date|source`.
- `daily_market_stats`: normal collection with precomputed features (7- and 28-day rolling mean and std, arrival z-score, momentum, seasonal index). Indexed on (commodity, market, date).
- `forecasts`: {series_key, model_version, run_date, horizon_days, points:[{date, p10, p50, p90}], baseline_mape, model_mape, confidence:"high|medium|low"}. Indexes: (series_key, run_date desc) and a TTL on run_date of about 90 days.
- `alerts`: {type: price_spike|price_crash|arrival_surge|target_hit|listing_match, commodity, market, severity, message_en, message_hi, value, threshold, created_at, user_ids, read_by}. Index on (created_at desc) and on user.
- `model_registry`: {model_name, version, trained_at, train_window, features, metrics:{mape, smape, mase, coverage80}, artifact_path (joblib on disk), status: candidate|production|retired}.
- `markets`: {market, district, state, lat, lon} for distance, transport cost and maps (2dsphere index).
- `broker_profiles` / `watchlists`: commodities, home market, radius_km, transport Rs/qtl-km, commission %, target prices.
- Farmer `crop_listings` already exist. Add `commodity_normalised`, `market_nearest`, `location` (GeoJSON), `qty_quintals`, `available_from` and `grade`.

**JSON fallback:** `JsonFileRepo` implements the same interface, with one file per collection under `data/fallback/`. It writes atomically (temp file then rename) and filters in Python. Selection happens at startup by pinging Mongo with a short `serverSelectionTimeoutMS`. Seed sample CSV data for demos and offline tests.

**Analytics and modelling:**
- Baselines: naive (last value), seasonal naive (same week last year) and a 7-day moving average.
- Candidate models:
  - SARIMAX with exogenous arrivals, as supported by the RBI finding.
  - Or LightGBM with quantile objectives (0.1, 0.5, 0.9) on lag, rolling, arrival and calendar features.
- Train one global model per commodity across markets, so that sparse markets still get forecasts.
- Version models by date string, store them with joblib, and log metrics in `model_registry`.
- Promote a model only if its MASE is below 1 versus seasonal naive on a rolling-origin backtest.

**API (FastAPI, `/api/broker/...`, Pydantic response models):**
- `GET /demand/summary?commodity=&state=&date=`: gap and anomaly table for the heatmap.
- `GET /prices/history?commodity=&market=&days=90`
- `GET /forecasts/{commodity}/{market}?horizon=7`: returns points with p10, p50 and p90, confidence and model_version.
- `GET /signals?broker_id=`: action cards with buy/hold/sell, reason text and confidence.
- `GET /best-mandi?commodity=&from_market=&radius_km=&qty=`: ranked net price.
- `GET /matches?broker_id=`: farmer listings ranked against demand.
- `GET /alerts?since=` and `POST /alerts/{id}/read`.
- `GET /stream/alerts`: SSE (optional).
- `POST /admin/ingest/run` and `POST /admin/retrain`: run as BackgroundTasks and return a job_id. `GET /admin/jobs/{id}` gives status.
- `GET /health/data`: last ingest time, row counts and missing markets.
- Caching: an in-process TTL cache (cachetools, about 10–30 min) keyed by query params, cleared after each ingest. Add `ETag` or `Last-Modified` headers so polling clients get 304 responses.

**Frontend (React):**
- Data fetching with React Query or SWR, polling every 5–10 min with `refetchOnWindowFocus`. Optionally an `EventSource` on `/stream/alerts` that invalidates queries.
- Charts:
  - Recharts `ComposedChart` with an `Area` for the p10–p90 band (stacked range or `[low, high]` dataKey), a `Line` for p50 and history, and a `ReferenceLine` for today.
  - `BarChart` for arrivals.
- Map: react-leaflet with CircleMarkers coloured by anomaly.
- Filters: commodity, state, district, market, radius and horizon.
- The existing notifications route shows alerts. In-app alerts come first; web push or SMS can follow later.
- Near-real-time is effectively "few times a day", because Agmarknet updates daily and some markets lag a day. Polling every 5–15 minutes plus SSE for alerts is enough; WebSockets are unnecessary.

### Gaps
- Whether the data.gov.in API endpoint works in October 2026 could not be verified, because the fetch was blocked. The team must test it with a key and keep a CSV/backfill path (CEDA, Agmarknet 2.0 downloads).
- Whether arrival quantities are included in the data.gov.in daily price feed is unconfirmed. The listed fields omit arrivals, though Agmarknet reports carry them. A separate arrivals source or report scrape may be needed.
- Official MongoDB pages on time-series limitations (updates and deletes, unique index support) were not fetched. "No unique indexes" is a design precaution and should be verified against the Limitations page for the installed version.

## Q5. How should the module integrate with farmer crop listings for broker-farmer matching and farmer advice?

### Takeaway
Treat farmer listings as the app's own forward-supply signal, which public Agmarknet data lacks. Join listings to demand signals by normalised commodity and geography. Rank them for brokers by demand score, distance and net margin. Reflect the same signals back to farmers as "best time and place to sell" advice. The RBI and FPO evidence on farmers' low share of the consumer rupee motivates showing farmers the price they are likely to get.

### Cited Findings
- Kisan Network's model was farmers posting crop photos and availability while buyers browsed listings. — [TechCrunch](https://techcrunch.com/2016/03/09/y-combinator-backed-kisan-network-is-transforming-the-rural-indian-agricultural-market)
- Ninjacart advertises real-time demand-supply matching and farm-gate grading. — [Decentro blog](https://decentro.tech/blog/agritech-startups/)
- Shorter FPO channels raise the farmer's share to about 89% of the consumer rupee in one AP study. — [SASAPJAS](https://sasapjas.org/abstract/study-on-farmers-access-to-markets-through-fpos-in-kurnool-district-of-andhra-pradesh)
- Farmers who planted heavily after a tomato price spike faced crashes, which shows that boom-chasing creates gluts. — [FreshPlaza](https://www.freshplaza.com/north-america/article/9554432/indian-tomato-farmers-faced-with-losses-as-glut-crashes-prices/)

### Inferences
- **Matching score** for each listing L and broker B:
  - Formula: `score = w1·demand_score(commodity, region) + w2·(1 − distance/radius) + w3·qty_fit + w4·grade_fit + w5·freshness(available_from) + w6·expected_margin_norm`.
  - Return the top N with explanation chips such as "High demand at Azadpur", "38 km" and "Grade A".
- **Listing-driven supply:** aggregate open listings by commodity and district into an expected-supply count for the next 7–14 days. Add it to the demand–supply gap, and flag a "possible glut" when listing volume plus arrivals exceed the seasonal norm.
- **Farmer-side advice:** use the same forecasts and best-mandi engine with farmer-specific costs. Example: "Prices in Indore expected Rs 1,600–2,000 next week; Mandsaur pays about Rs 120/qtl more after transport." Signal "high demand now, list today" and warn about saturation before sowing. Keep the wording advisory and include the confidence chip.
- **Event flow:** a new listing triggers a match job (BackgroundTask) that creates `listing_match` alerts for brokers whose watchlist or radius matches. A broker's offer triggers a notification to the farmer through the existing notifications route.
- **Trust and fairness:** show farmers the mandi modal price next to any broker offer, as a transparency feature. This is consistent with eNAM's emphasis on bid-price SMS. — [Lok Sabha reply](https://sfacindia.com/UploadFile/Statistics/LS%20Qus%20No.%20U11382%20dt.%2020.03.2025.pdf)

### Gaps
- No sources were found on matching-algorithm designs used by Indian agritech marketplaces. The scoring above is a proposal.
- Commodity name normalisation between farmer free-text and Agmarknet's commodity and variety list needs a mapping table. Its size and effort are unknown.

## Q6. What are the testing and acceptance criteria?

### Takeaway
Test four layers:
1. Data-quality checks at ingest.
2. API contract tests (pytest with httpx and Pydantic schemas, against both the Mongo and JSON repositories).
3. Forecast acceptance on a rolling-origin backtest that must beat naive and seasonal-naive baselines, with calibrated intervals.
4. UI checks (component tests and a smoke E2E).

Published Indian mandi forecasting studies report MAPEs of about 8–15% for TOP commodities. This gives a realistic, if not directly comparable, target range.

### Cited Findings
- A GRU model achieved 14.59% MAPE for onion and 10.58% for tomato, beating ARIMA. — [Scientific Reports 2025 (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12215695/)
- LSTM achieved 7.99% MAPE for Agra potato prices, the best among the models tested. — [EAPR](https://eapr.net/node/701)
- A hybrid ARIMAX-LSTM on Tamil Nadu markets had RMSE of 232–2,045 depending on the crop. The authors flag data leakage as a risk. — [aconf paper 2026](https://submission-hk.aconf.org/hk/2026/04/paper_1194582_sjbfym0d3a8v1wbm_v1.pdf)
- ARMA-GARCH beat ARIMA for onion prices on MAPE, RMSE and Theil's U. — [ICAR IJAgS](https://epubs.icar.org.in/index.php/IJAgS/article/view/163270)
- Reported metrics vary widely across studies, crops and markets and are not directly comparable. None of the retrieved studies used a seasonal-naive baseline. — (synthesis of the above)
- Agmarknet-derived feeds can lag a day for some markets, which affects freshness tests. — [acrop.app](https://acrop.app/mandi)

### Inferences (proposed acceptance criteria)
- **Data quality (run at each ingest; failures go to `ingest_reports`):**
  - Schema validation via Pydantic.
  - `min_price ≤ modal_price ≤ max_price`.
  - Prices > 0 and within commodity-specific plausibility bounds.
  - Duplicate rate after dedupe = 0.
  - Date not in the future.
  - Units normalised (Rs/quintal).
  - Commodity and market names map to master tables, with unmapped names below 2% and logged.
  - Outlier flags where |modal − 28d median| > 5·MAD. Flag these rows; do not drop them.
  - Freshness SLA: data for D−1 is present by 10:00 IST for ≥ 80% of watched markets, else a banner is shown.
- **API contract:**
  - Every endpoint has a `response_model`.
  - pytest runs the same test suite parametrised over MongoRepo (local or mongomock) and JsonFileRepo.
  - Tests cover the forecast response shape (p10 ≤ p50 ≤ p90, horizon length), 404 for unknown commodities, 422 for bad params, latency below 300 ms p95 on cached endpoints, and SSE stream heartbeats.
  - Snapshot the OpenAPI schema to catch breaking changes.
- **Forecast accuracy:**
  - Rolling-origin backtest over at least 6 months, for horizons of 1, 7 and 14 days.
  - Promote a model only if MASE < 1 versus seasonal naive (or versus naive where history is under one year) and sMAPE is no worse than the moving average.
  - Coverage of the 80% interval must fall within 70–90%, as a calibration check.
  - Directional accuracy of the buy/hold/sell signal must exceed 55% and must beat an "always hold" rule on simulated margin.
  - Keep a per-series fallback to the baseline when the model fails.
  - Guard against leakage by using only features available at forecast time.
- **Alerts:** unit tests with synthetic series must show that an arrival series at 2.5× the median triggers a surge alert, that no duplicate alerts fire for the same event within 24 hours, and that thresholds are configurable.
- **UI:**
  - React Testing Library tests for filters, the empty, loading and stale-data states, and the forecast band rendering (band present, median line, today marker).
  - A Playwright or Cypress smoke flow: login as broker, pick a commodity, see an action card, open matches, receive an alert in notifications.
  - Accessibility: colour plus text label for signals, not colour alone.
  - Mobile width of 360 px.
  - Hindi label toggle.
- **Acceptance demo criteria:**
  - With Mongo stopped, the app boots on the JSON fallback and serves seeded data.
  - The scheduler runs exactly once per job with 2 workers (lock test).
  - The dashboard loads in under 3 s on seeded data.

### Gaps
- I found no published Indian benchmark that uses MASE or seasonal-naive comparisons, so the thresholds above are proposed engineering targets, not literature-derived standards.
- I found no data on what forecast accuracy brokers consider "useful enough" to act on.
