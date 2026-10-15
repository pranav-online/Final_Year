# Indian Mandi Price and Arrival Data Sources for a Broker Demand-Analysis Backend

Research date: 2026-10-15. Items marked **[VERIFIED LIVE]** were tested directly with HTTP requests on 2026-10-14/15 (IST); everything else is cited from web sources. Some endpoints are undocumented internals of government web apps and may change without notice.

---

## 1. Agmarknet (agmarknet.gov.in): content, API status, history, and the Agmarknet 2.0 redesign

### Takeaway
Agmarknet is now "Agmarknet 2.0": a React single-page app backed by a JSON REST API at `https://api.agmarknet.gov.in/v1/`. It has no public developer documentation or keys. Several read-only endpoints (reference lists, weekly state-wise price trends, and a national price and arrival dashboard) answered anonymous requests in testing. The detailed daily market-wise price and arrival report endpoint requires a captcha, which blocks straightforward scraping. All old ASP.NET scrapers (`Default.aspx`, `SA_Pri_Month.aspx`) target the retired site and should be treated as outdated.

### Cited Findings
- Agmarknet was "technologically upgraded as Agmarknet Portal 2.0 in November, 2025". A Parliament statement put linked mandis at 4,367, and the portal covers 350+ commodities and 2,000 varieties. A mobile app lets market officials enter data on the spot — [VisionIAS summary](https://visionias.in/current-affairs/schemes/ministry-of-agriculture-farmers-welfare/integrated-scheme-for-agricultural-marketing-schemes-agmarknet-portal); [UNI India](https://www.uniindia.com/north-india/development-up-mandi/196607)
- All 251 Uttar Pradesh mandis connected to Agmarknet 2.0 through API integration from the UP e-Mandi portal (late Sept 2026), giving "100 percent market reporting" in UP. This shows state systems now push data by API — [The Hans India](https://www.thehansindia.com/news/national/yogi-government-connects-all-251-up-mandis-to-national-network-1127009); [UNI India](https://www.uniindia.com/north-india/development-up-mandi/196607)
- **[VERIFIED LIVE]** `https://agmarknet.gov.in/` serves `<title>Agmarknet 2.0</title>`, a React bundle (`/static/js/main.<hash>.js`). Its CSP header allows `connect-src https://api.agmarknet.gov.in`, and the bundle hard-codes the base URL `https://api.agmarknet.gov.in/v1/` — [agmarknet.gov.in](https://agmarknet.gov.in/)
- **[VERIFIED LIVE]** These endpoints worked without auth:
  - `GET https://api.agmarknet.gov.in/v1/daily-price-arrival/filters` → `{"status":true,"data":{"cmdt_data":[{"cmdt_id":380,"cmdt_name":"Absinthe","cmdt_group_id":12},...]}}` (master lists for filters).
  - `GET https://api.agmarknet.gov.in/v1/commodities?page_size=500` → 605 commodities, each with `id`, `cmdt_name`, `cmdt_group`, `arrival_unit`, `price_unit`, `is_msp`, `comm_code`, `varieties[]`, `grades[]`. Example IDs: Wheat=1, Onion=23, Potato=24, Tomato=65.
  - `GET https://api.agmarknet.gov.in/v1/location/state?page_size=100` → 36 states/UTs with nested `districts[]`, including LGD codes (`state_lg_code`, `district_lg_code`) and multilingual names. Useful as a canonical location master.
  - `GET https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-weekly?report_mode=Statewise&commodity=23&year=2026&month=9&week=1` → state-wise onion prices (Rs./Quintal) for the week, previous week, previous month, and same week last year, plus % changes. `week` must be 1–4.
  - `POST https://api.agmarknet.gov.in/v1/dashboard-data/` with JSON `{"dashboard":"marketwise_price_arrival","date":"2026-10-13","commodities":[23],"downloadreport":"false","page":0}` → national commodity-wise records with `cmdt_grp_name`, `cmdt_name`, `msp_price`, `as_on_price`, `one_day_ago_price`, `two_day_ago_price` (Rs./Quintal), `as_on_arrival`, `one_day_ago_arrival`, `two_day_ago_arrival` (**Metric Tonnes**), `reported_date`, `trend`. Note that `downloadreport` must be the string `"false"`; a boolean returned an error.
  — [api.agmarknet.gov.in (tested)](https://api.agmarknet.gov.in/v1/commodities?page_size=3)
- **[VERIFIED LIVE]** `POST https://api.agmarknet.gov.in/v1/daily-price-arrival/report` (the market-wise daily price and arrival report, with params such as `from_date`/`to_date` in `yyyy-MM-dd`) returned `{"detail":"Captcha key and captcha value are required.","code":"TOKEN_OR_CAPTCHA_REQUIRED"}`. Other endpoints such as `market-holiday` returned `Authorization header missing`. `price-trend/wholesale-prices-monthly` returned HTTP 500 for the parameter combinations tried — [api.agmarknet.gov.in (tested)](https://api.agmarknet.gov.in/v1/)
- The bundle also lists dashboard IDs and report paths such as `market_details_sp` (market profile), `season_price_arrival`, `prevailing_market_below_msp`, `/price-trend/wholesale-arrivals-weekly`, `/price-trend/varietywise-prices-weekly`, and `/all-type-report/commodity-wise-mandi-arrival`. The price-trend calls take params `report_mode` (Statewise/districtwise/marketwise/"marketwise(all)"), `commodity`, `year`, `month`, `week`, `state`, `district`, `market`, and `export` — [Agmarknet 2.0 JS bundle](https://agmarknet.gov.in/)
- The older generation of scrapers targeted `agmarknet.gov.in/Default.aspx` and `PriceTrends/SA_Pri_Month.aspx` with Selenium/BeautifulSoup. Those pages belong to the pre-2.0 site — [jha-vineet69/AgriMarket](https://github.com/jha-vineet69/AgriMarket); [meet-sapu/Web_Crawler](https://github.com/meet-sapu/Web_Crawler)
- A 2017 scraped dataset noted that the old site allowed only one day's data per download — [iancovert/Agmarknet](https://github.com/iancovert/Agmarknet)
- History: a third-party mirror (CEDA, Ashoka University) offers Agmarknet data from **2000 to present**, lagging by a few months — [agmarket-mcp on Glama](https://glama.ai/mcp/servers/Krishna-Baldwa/agmarket-mcp)

### Inferences
- Agmarknet itself has no supported public API. The `api.agmarknet.gov.in/v1` endpoints are internal to the web app: undocumented, unversioned for outside users, and subject to change. The captcha on the detailed report shows the operators actively discourage bulk scraping of market-level data.
- Agmarknet 2.0 is the only easily reachable source of **arrival quantities** (tonnes). The data.gov.in feed has prices only. The `dashboard-data` endpoint gives national commodity-level arrivals; market-level arrivals sit behind the captcha.
- The `commodities` and `location/state` masters, which include LGD codes, are valuable for normalising names even if you take prices from elsewhere.

### Gaps
- No official statement was found on how far back Agmarknet 2.0's own history goes. The old site was widely reported to hold data from about 2001/2003, but I did not verify this for 2.0.
- No official terms of use for `api.agmarknet.gov.in` were found. Its rate limits are unknown.
- The working parameter set for `wholesale-prices-monthly` was not established (it returned 500).

---

## 2. data.gov.in OGD API: "Current Daily Price of Various Commodities from Various Markets (Mandi)"

### Takeaway
This is the only official, documented, key-based API for mandi prices, and it is the backbone for a FastAPI project. Resource ID `9ef84268-d588-465a-a308-a864a43d0070`, ~16–19k rows per day, prices only (min/max/modal in Rs./quintal, no arrivals), **current day only**. The public sample key caps responses at 10 records. History must be built by pulling every day, or backfilled from another source.

### Cited Findings
- **[VERIFIED LIVE]** Endpoint format:
  `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=<KEY>&format=json&offset=0&limit=<N>&filters[state.keyword]=Maharashtra&filters[commodity]=Onion`
  Supported params: `api-key`, `format` (json/xml/csv), `offset`, `limit`, and `filters[<field>]`. The state filter key is **`state.keyword`** (per `field_exposed`). The other exposed filter fields are `district`, `market`, `commodity`, `variety`, and `grade` — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- **[VERIFIED LIVE]** Response metadata: `title: "Current Daily Price of Various Commodities from Various Markets (Mandi)"`, `org: Ministry of Agriculture and Farmers Welfare / Department of Agriculture and Farmers Welfare`, `created_date: 2021-08-02`, `updated_date: 2026-10-14T20:00:57Z`, `index_name/target_bucket.index: daily_mandi_price`, `catalog_uuid: 6141ea17-a69d-4713-b600-0a43c8fd9a6c`, `version: 2.2.0`, `total`, `count`, `limit`, `offset`, `records[]` — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- **[VERIFIED LIVE]** Sample record:
  `{"state":"Maharashtra","district":"Nashik","market":"APMC Nasik ","commodity":"Onion","variety":"Unhali","grade":"Local","arrival_date":"14/10/2026","min_price":1600,"max_price":4151,"modal_price":3400}`
  Fields: `state, district, market, commodity, variety, grade, arrival_date (dd/mm/yyyy string), min_price, max_price, modal_price` (doubles). Note the trailing space in `"APMC Nasik "`, so names need trimming. Every record in the pull had the same `arrival_date` (the current day) — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- **[VERIFIED LIVE]** Totals on 2026-10-14/15: `total=19095` records nationally; 49 records for Maharashtra + Onion — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- **[VERIFIED LIVE]** The public sample key `579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b` returned only 10 records when `limit=1000` was requested. Response headers showed `X-Ratelimit-Limit: -1` / `X-Ratelimit-Remaining: -1`, so no explicit numeric rate limit was advertised — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- A working open-source collector confirms the following. The demo key returns at most 10 records per request, so a full ~16k-row daily pull takes about 1,700 requests; registering a free key allows larger pages. The source "only serves the current day", so past days cannot be backfilled. The feed fills through the day, so pull after about 14:00 IST (cron `30 14 * * *`). The collector had a bug where it trusted `limit=1000` and stopped after the first 10-row page. Schema `state, district, market, commodity, variety, grade, arrival_date, min_price, max_price, modal_price, pulled_on`; prices in Rs./quintal — [herrrickshaw/agri-commodity-tracker](https://github.com/herrrickshaw/agri-commodity-tracker)
- Another project uses the same resource ID with Python Requests and keeps the API key in `.env` — [madrewarparth/AgriPrice_Detection_System](https://github.com/madrewarparth/AgriPrice_Detection_System)
- The `datagovindia` Python wrapper exists on PyPI. The latest release listed is 1.0.2 (Sept 2024) — [PyPI datagovindia](https://pypi.org/project/datagovindia/0.4); [piwheels](https://www.piwheels.org/project/datagovindia)
- A third-party MCP project describes the data.gov.in feed as "frequently down / WAF-blocked" — [agmarket-mcp on Glama](https://glama.ai/mcp/servers/Krishna-Baldwa/agmarket-mcp)
- Most data.gov.in data is under the Government Open Data Licence – India, which permits reuse with attribution — [atlas.co summary](https://atlas.co/data-portals/data-gov-in/)
- Historical related dataset: "Variety-wise Daily Market Prices of Commodity" (wholesale max/min/modal, sourced from AGMARKNET, OGL-India) is listed on AIKosh (uploaded 24/02/25). Its metadata is inconsistent: frequency is shown as "Monthly" while the description says daily, the date range is "N.A.", and the size is 0 — [AIKosh](https://aikosh.indiaai.gov.in/home/datasets/details/variety_wise_daily_market_prices_of_commodity.html)
- Resource landing page — [data.gov.in resource page](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

### Inferences
- API key signup: register a free account on data.gov.in. A key is generated in the user profile ("My Account") and replaces the sample key. I could not fetch the signup page (HTTP 403 to automated fetch), so confirm the flow and any per-key page cap by logging in. With a personal key, `limit` values of several hundred to thousands per page are commonly reported, but I did not verify this.
- Because the resource is overwritten daily, a **daily scheduled pull is mandatory** to build history. Missing a day means losing that day's data for good, unless it is backfilled from Agmarknet or CEDA.
- The updated timestamp (~20:00 UTC = 01:30 IST next day) suggests late-night refreshes, and the open-source evidence suggests data accumulates through the IST day. Run two pulls per day, for example 15:00 and 23:30 IST, and upsert. This is a sensible hedge.

### Gaps
- No official documentation was retrieved on per-key rate limits or the maximum `limit` for registered keys (the data.gov.in API page returned 403).
- I could not confirm whether data.gov.in hosts a separate long-history mandi price resource with an API. The AIKosh listing has unclear coverage.

---

## 3. eNAM (enam.gov.in): public trade and price data or API?

### Takeaway
eNAM has public dashboards (trade data, live price, Agmarknet comparison) but **no documented public API**. Bulk or market-level data is officially available "on request". For a student project, eNAM is at best a secondary, scrape-only source and is not recommended.

### Cited Findings
- The eNAM dashboard links to public pages: Trading Details (`/web/dashboard/trade-data`), e-NAM Live Price (`/web/dashboard/live_price`), ReMS Price Dissemination, an Agmarknet Price Dashboard, an "eNAM vs AGMARKNET Price Dashboard", Live Trade screen board (`/NAMV2/screen-board/index.html`), and e-NAM MIS (`/analytics`). Downloadable files are only guidelines and directories (PDFs) — [eNAM dashboard](https://enam.gov.in/web/dashboard/trade-data)
- An RTI reply (2025) says mandi-level eNAM data on quantity and value traded is available on request and points to enam.gov.in — [SFAC RTI reply](https://sfacindia.com/UploadFile/Statistics/RTI%20No.%2000033%20dt.%2023.07.25.pdf)
- **[TESTED, FAILED]** A POST to the AJAX endpoint `https://enam.gov.in/web/Ajax_ctrl/trade_data_list`, which earlier community scrapers used, with state, APMC, commodity, and date form fields returned an HTML page instead of JSON. That earlier usage is from memory and not verified here, so treat the endpoint as unverified or changed — [enam.gov.in (tested)](https://enam.gov.in/web/Ajax_ctrl/trade_data_list)

### Inferences
- eNAM covers only eNAM-integrated mandis and their electronic trades. Its prices differ from Agmarknet reports, which is why the "eNAM vs AGMARKNET" dashboard exists. Use it only for validation, not as a primary feed.

### Gaps
- I could not confirm the current fields or backend format of the eNAM trade-data dashboard.

---

## 4. Other sources: DoCA PMC, NHRDF, Kaggle and other historical datasets, CEDA, IMD weather, UPAg

### Takeaway
For **historical backfill**, the most useful source is the CEDA (Ashoka University) Agri Market API: Agmarknet prices from 2000, keyed by numeric IDs, needs a free key. For demand drivers, the useful sources are DoCA retail and wholesale prices (consumer-side signal for 22 essentials), IMD weather (rainfall and temperature drive supply), and UPAg/ministry production estimates (seasonal supply). Kaggle has mostly snapshots, not reliable long histories.

### Cited Findings
- **CEDA Agri Market API.** Base `https://api.ceda.ashoka.edu.in/v1`, `Authorization: Bearer <CEDA_API_KEY>`. Endpoints: `GET /agmarknet/commodities`, `GET /agmarknet/geographies` (census state and district IDs), `POST /agmarknet/markets` (`commodity_id, state_id, district_id, indicator="price"`), and `POST /agmarknet/prices` (`commodity_id, state_id, from_date, to_date` as YYYY-MM-DD, optional `district_id` list). Response envelope `{"output":{"type":"success","data":[...]}}`; price rows hold `date, census_state_id, census_district_id, market_id, min_price, max_price, modal_price`. The API returns HTTP 429 when rate-limited — [agmarket-mcp api.py](https://github.com/Krishna-Baldwa/agmarket-mcp/blob/feat/ceda-api-migration/src/agmarknet_mcp/api.py)
- CEDA coverage runs from 2000 to present, lagging by a few months — [agmarket-mcp on Glama](https://glama.ai/mcp/servers/Krishna-Baldwa/agmarket-mcp)
- **[VERIFIED LIVE]** `GET https://api.ceda.ashoka.edu.in/v1/agmarknet/commodities` without a key → `{"status":"failure","message":"Unauthorised, no api key passed."}`. The CEDA portal is at `agmarknet.ceda.ashoka.edu.in` ("CEDA Agri Market Data") — [CEDA API (tested)](https://api.ceda.ashoka.edu.in/v1/agmarknet/commodities)
- **DoCA Price Monitoring Division/Cell.** Monitors daily retail and wholesale prices of **22 essential commodities** (cereals, pulses, edible oils, vegetables such as onion, potato, and tomato, sugar, tea, milk, salt). Reporting centres were 101 by one DoCA source, 114 in a 2020 Parliament reply, and 179 by March 2022 per CEDA — [DoCA PMD](https://consumeraffairs.nic.in/price-monitoring-cell/price-monitoring-cell); [2020 LS reply](https://fcainfoweb.nic.in/PMS/writereaddata/2020_LS_B_3765.pdf); [CEDA Daily Food Prices](https://dca.ceda.ashoka.edu.in)
- Since **September 2023**, DoCA publishes prices only at state and national level. Centre-level data is no longer published, though CEDA keeps a centre-level archive for 2009–2023 — [CEDA DCA README](https://dca.ceda.ashoka.edu.in/README.html)
- **Historical datasets.** The Kaggle dataset "current daily prices of commodities from mandi" (brpuneet898, mirrored on Baselight) is a snapshot of the data.gov.in feed, not a long history — [Baselight mirror](https://baselight.app/u/kaggle/dataset/brpuneet898_current_daily_prices_of_commodities_from_mandi)
- Mendeley Data (Dec 2025, DOI 10.17632/ds9jmxp9zy.1) holds a 2014–2024 **onion** dataset that combines Agmarknet price and arrivals with IMD weather. It is useful as a ready demand and supply-driver example — [Mendeley Data](https://data.mendeley.com/datasets/ds9jmxp9zy)
- India Data Portal (ISB) lists an "APMC arrivals and prices" (Agriculture Marketing) dataset — [India Data Portal CKAN](https://ckandev.indiadataportal.com/dataset/apmc-arrivals-and-prices/resource/a83bd1ad-ba46-41c7-9a80-c75537ce1172)
- **UPAg (upag.gov.in).** The Unified Portal for Agricultural Statistics (launched Sept 2023) standardises prices, production, area, yield, and trade data. It generates crop production estimates by triangulating IEG, Crop Weather Watch Group, MNCFC, and state data. Its price data comes from Agmarknet, vetted and updated regularly. Users can build custom reports — [Vikaspedia](https://en.vikaspedia.in/agriculture/agri-directory/unified-portal-for-agricultural-statistics); [Krishi Jagran](https://krishijagran.com/news/niti-aayog-launches-unified-portal-upag-for-agricultural-statistics-to-revolutionize-data-management/?amp=1); [Agriculture Post](https://agriculturepost.com/agritech/otsi-develops-upag-unified-portal-for-agricultural-statistics-for-ministry-of-agriculture/)

### Inferences
- **Demand drivers for broker-facing forecasting:**
  - Arrivals (supply) come from Agmarknet 2.0.
  - Lagged prices come from data.gov.in and CEDA.
  - Retail-wholesale spread from DoCA signals downstream consumer demand.
  - Rainfall and temperature from IMD affect supply shocks, as with onion and tomato.
  - Seasonal production estimates come from UPAg.
  - Festival and holiday calendars also matter. Agmarknet 2.0 has a `market-holiday` endpoint, but it needs auth.
- **NHRDF.** Its onion and garlic price reports were not researched in depth, so treat it as optional. Its onion data largely mirrors Nashik/Lasalgaon APMC prices, which are already in Agmarknet.
- Because CEDA uses census IDs and Agmarknet 2.0 uses LGD codes, a mapping table is needed when joining sources.

### Gaps
- No documented UPAg public API was found. Downloads appear to be via portal reports.
- The NHRDF site and its data formats were not verified.
- The IMD API/data access was not researched in this pass. Common options are IMD gridded rainfall via the `imdlib` Python package, or Open-Meteo as a free proxy. Both are unverified here.
- CEDA API key signup terms and quotas were not confirmed.

---

## 5. Practical data issues and cleaning practice

### Takeaway
Expect untrimmed and inconsistent names, string dates, and a per-day snapshot model. Prices may also be missing, zero, or have min > modal. Arrival units vary by commodity. Normalise against a master (Agmarknet 2.0 commodity and LGD location lists), validate price ordering, and treat holidays and non-reporting days as missing rather than zero.

### Cited Findings
- **[VERIFIED LIVE]** data.gov.in market names carry trailing whitespace (`"APMC Nasik "`, `"APMC Satana "`), and dates are `dd/mm/yyyy` strings — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- **[VERIFIED LIVE]** In the Agmarknet 2.0 masters, each commodity has its own `arrival_unit` and `price_unit` codes (e.g. Onion `arrival_unit=7`, `price_unit=1`). Dashboard prices are labelled "Rs./Quintal" and arrivals "Metric Tonnes". The units master (`/units`) requires auth — [api.agmarknet.gov.in (tested)](https://api.agmarknet.gov.in/v1/commodities?page_size=3)
- **[VERIFIED LIVE]** Varieties and grades sit under each commodity (Onion variety "Unhali", grade "Local"; Wheat grade "FAQ") — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- Agmarknet 2.0 has internal "anomalous" entry workflows (`/notification-anomalous`, `/anomalous-reasons`, `data-entry/market/anamolous`) and "nil transaction" and "no-entry" reports. This means outliers and non-reporting are known issues at source — [Agmarknet 2.0 JS bundle](https://agmarknet.gov.in/)
- Recommended practices from a working pipeline: dedupe on (state, district, market, commodity, variety, grade, arrival_date); keep `pulled_on` separate from `arrival_date`; check `min_price ≤ modal_price ≤ max_price`; flag partial pulls — [herrrickshaw/agri-commodity-tracker](https://github.com/herrrickshaw/agri-commodity-tracker)
- UP reached 100% reporting only after API integration in Sept 2026. This implies coverage gaps in earlier data and in states without integration — [The Hans India](https://www.thehansindia.com/news/national/yogi-government-connects-all-251-up-mandis-to-national-network-1127009)

### Inferences
- Cleaning recipe:
  1. Trim and case-fold all names.
  2. Map commodity and market names to Agmarknet 2.0 master IDs, with a manual alias table for spelling variants.
  3. Parse dates to ISO.
  4. Drop or flag zero prices and rows violating min ≤ modal ≤ max.
  5. Flag modal prices beyond about 3× the MAD from a rolling 30-day median per (market, commodity, variety).
  6. Aggregate variety and grade to commodity level with an arrival-weighted modal price where arrivals are available.
  7. Reindex to a daily calendar and keep holidays and non-reporting days as NaN, with forward-fill limited to a few days for modelling only.
  8. Use modal price as the target.

### Gaps
- No authoritative published guide on Agmarknet data quality was found in this pass.

---

## 6. Recommended ingestion design for a FastAPI + MongoDB backend

### Takeaway
Use data.gov.in (with a registered key) as the primary daily price feed, a one-time CEDA backfill for history, and the Agmarknet 2.0 public `dashboard-data` and `price-trend` endpoints as an optional arrivals and trend signal. Run the jobs on a scheduler (APScheduler or cron) separately from request handling. Store raw and cleaned collections in MongoDB with idempotent upserts.

### Cited Findings
- Daily-only feed, need to pull after ~14:00 IST, and idempotent day-replace semantics — [herrrickshaw/agri-commodity-tracker](https://github.com/herrrickshaw/agri-commodity-tracker)
- Pagination: data.gov.in exposes `total`, `offset`, `limit`, `count`. The sample key returns 10 per page **[VERIFIED LIVE]** — [api.data.gov.in (tested)](https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070)
- CEDA history from 2000 with date-range queries per commodity and state, and 429 back-off — [agmarket-mcp api.py](https://github.com/Krishna-Baldwa/agmarket-mcp/blob/feat/ceda-api-migration/src/agmarknet_mcp/api.py)

### Inferences (proposed design)
- **Jobs:**
  1. `daily_mandi_pull` at 15:00 and 23:30 IST: page through data.gov.in with `offset` until `offset >= total`. Use a personal key and limit ≥ 500, with retry and backoff because the feed is sometimes unavailable. Upsert into `mandi_prices_raw` keyed by `(arrival_date, state, district, market, commodity, variety, grade)`, and store `pulled_at`.
  2. `daily_arrivals_pull`: POST Agmarknet 2.0 `dashboard-data` (`marketwise_price_arrival`) for national commodity arrivals. Store this as best-effort, since it is undocumented.
  3. `weekly_trend_pull`: state-wise weekly prices via `price-trend/wholesale-prices-weekly`.
  4. `clean_and_aggregate`: raw → `mandi_prices_clean` (normalised IDs, ISO date, outlier flags) → `region_commodity_daily` (state and district aggregates for forecasting).
- **Backfill:** a one-time CEDA pull per (commodity, state) for a manageable window (e.g. 2018–present, top 20–30 broker commodities), chunked by year. Store it with `source:"ceda"`. Reconcile overlapping dates with data.gov.in by preferring the daily feed. CEDA lags by months, so the daily feed must fill the recent gap.
- **MongoDB:** compound unique index on the natural key; indexes on `(commodity_id, state, arrival_date)`. Consider time-series collections for the clean daily series. Keep masters (`commodities`, `locations`, `aliases`) as separate collections seeded from Agmarknet 2.0 `/commodities` and `/location/state`.
- **FastAPI:** serve forecasts and prices only from MongoDB, never live upstream calls. Expose `/prices?commodity=&state=&district=&from=&to=`, `/arrivals`, `/forecast`, and a `/health/ingestion` endpoint showing the last successful pull date per source, so gaps are visible.
- **Resilience:** alert on days where the pulled total is below about 50% of the trailing median. If the daily data.gov.in pull is missed, the only recovery path is CEDA, once its lag catches up.

### Gaps
- Optimal page size and safe request rate for registered data.gov.in keys are unverified.
- The stability of the Agmarknet 2.0 internal endpoints over time is unknown, so treat them as optional enrichments.
