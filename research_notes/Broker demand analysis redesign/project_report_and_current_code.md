# Broker Demand Analysis: What the Master Report Says vs. the Current Implementation

Sources are local files. Short names used below:
- [Report] = C:\Users\rahul\Downloads\alip_farmer_broker_master_report2.md (631 lines, "ALIP Master Architecture & Technical Report: Farmer & Broker Modules", System Version `v2.1-hybrid`, dated October 2026)
- [ml_svc] = backend/services/demand_ml_service.py
- [mkt_svc] = backend/services/market_service.py
- [da] = backend/services/demand_analysis.py
- [region_svc] = backend/services/region_service.py
- [region_routes] = backend/routes/region_routes.py
- [market_routes] = backend/routes/market.py
- [UI_DA] = frontend/alip-frontend/src/pages/DemandAnalysis.js
- [UI_BD] = frontend/alip-frontend/src/pages/BrokerDashboard.js
- [api.js] = frontend/alip-frontend/src/services/api.js
- [live] = live GET calls to http://127.0.0.1:8000 (openapi.json, /market/demand/{region}) on 2026-10-15
- [pkl] = read-only inspection of backend/data/demand_model.pkl with backend\venv\Scripts\python.exe

All repo paths are relative to C:\Users\rahul\Final_Year.

## Q1. What does the master report say about demand analysis, brokers, the broker dashboard, market intelligence, data sources, ML models, and planned changes?

### Takeaway
The report describes a much richer broker "Predictive Demand & Anomaly Analytics" feature than the one that exists: five sub-engines (a dynamic absorption threshold, a Z-score anomaly detector, a 1-10 urgency scorer, a 7-day price-decay and break-even engine, and a seasonal harvest context), plus a 7-factor destination ranker, freight ROI and a shipment lifecycle. The report has no explicit "needs to be changed" or TODO section. The changes it implies come from the many services, endpoints and datasets it names that the code does not have.

### Cited Findings

**Report structure and status**
- The report is titled "ALIP Master Architecture & Technical Report: Farmer & Broker Modules", version `v2.1-hybrid`, status "Master System Architecture, Engineering Specifications & Visual Blueprints", dated October 2026. Its personas are "Indian Agricultural Producers (Farmers) & Commercial Commodity Traders (Brokers)". — [Report, lines 1-7]
- A search of the report for "change", "TODO" and "TBD" found only one table header (line 559). The report has no explicit list of planned changes. Everything is written as if already built. — [Report]

**§1 Master System Landscape (overall system)**
- The report describes a React 19 SPA with a Farmer Portal (`/farmer, /crop, /disease, /weather, /listing`) and a Broker Portal (`/broker, /demand, /supply, /listings, /notifications`), a FastAPI gateway on port 8000 with "JWT Token Validation & Role Guards (role: farmer | broker)", and the sub-routers `/crop, /disease, /weather, /market, /auth`. — [Report, §1, lines 47-60]
- The services it names are regional_crop_service.py (LightGBM + Prior Hybrid), disease_service.py, weather_service.py, market_ranking_service.py ("7-Factor Destination Ranker"), demand_ml_service.py ("Dynamic Thresholds & Price Decay") and shipment_service.py ("Haversine Freight Engine"). — [Report, §1, lines 62-70]
- The storage it names is MongoDB ("users, listings, shipments, scans"), Parquet stores ("district_season_features.parquet"), an in-memory scan event bus, and external APIs (OpenWeatherMap, Open-Meteo, SoilGrids). No mandi-price API (such as Agmarknet or data.gov.in) is named anywhere. — [Report, §1, lines 80-86]

**§2 ERD (entities relevant to demand)**
- USER has user_id, email, full_name, role "farmer | broker", location, phone and created_at. — [Report, §2, lines 110-118]
- CROP_LISTING has listing_id, farmer_id FK, crop_name, quantity_kg, price_per_kg, location, status "available | pending | sold" and created_at. — [Report, §2, lines 132-141]
- SHIPMENT has shipment_id, broker_id, listing_id, source_region, destination_region, crop, quantity_kg, transport_cost, truck_type "small|medium|large", status "initiated|in_transit|delivered|cancelled" and dispatched_at. BROKER_RATING has 1-5 stars with rater and rated broker IDs. — [Report, §2, lines 143-165]

**Farmer side (how it connects to demand)**
- The farmer lifecycle is Crop Recommendation → Disease Detection → Weather Advisory → Crop Listing. — [Report, §1.1]
- Crop recommendation Mode C (the "Regional AI District Model v2.1") blends `S_hybrid = 0.20·P_ML + 0.80·P_prior`, with a 50 km boundary cutoff. On a 2014 test holdout it reports NDCG@3 = 0.9128 (pure ML 0.8121, prior 0.9081), Recall@3 = 0.9316, Recall@1 = 0.9188 and Brier = 0.0156. — [Report, §1.3, lines 248-255]. This is the only place in the report that gives evaluation metrics. The demand model has none.
- §1.6 Crop Marketplace Listing: farmers enter Farmer Name, Location, Crop Name, Quantity (kg), Target Price (₹/kg) and Contact Phone. The form "Emits `POST /market/listing/add`, creating an active listing in MongoDB and updating the **Broker Regional Supply Registry**." — [Report, §1.6, lines 324-328]
- §1.7: "Re-centering the primary district automatically updates weather queries, crop models, and mandi prices across the app." — [Report, §1.7, line 334]

**§2.1 Broker mission**
- "The **Broker Module** is ALIP's commercial intelligence and market-clearing engine for commission agents, commodity traders, and institutional buyers. Its mission is to **eliminate spatial market failure** through AI-driven redistribution, transport optimization, and deal settlement." — [Report, §2.1, line 357]

**§2.2 Broker architecture**
- The UI views are Market Overview Dashboard (/broker), "7-Factor Demand Intelligence (/demand)", Regional Supply Monitor (/supply), Master Crop Directory (/listings) and Market Alerts (/notifications). — [Report, §2.2, lines 366-370]
- The services are market_ranking_service.py (7-Factor), demand_ml_service.py (Dynamic Thresholds), urgency_service.py (1-10 Urgency Scorer), price_trajectory_service.py (7-Day Price Decay), shipment_service.py (Haversine Logistics), reliability_service.py (Broker Ratings) and seasonal_context_service.py (Harvest Wave Cycles). — [Report, §2.2, lines 374-380]
- The data models are "45+ Mandi Spatial Distance Index", "Shipments Collection", "Historical Supply Records (Z-Score)" and "Farmer Listings Collection". — [Report, §2.2, lines 384-387]

**§2.3 Market Overview & Broker Dashboard KPIs**
- The dashboard shows Total Market Volume ("Live cumulative tonnage"), Active Farmer Listings ("pending listings across all districts"), Oversupply Alerts ("Districts where local arrivals exceed dynamic absorption thresholds") and Undersupply Alerts ("Mandis facing deficits where prices are escalating"). — [Report, §2.3, lines 396-401]

**§2.4 7-Factor Weighted Market Ranking Engine**
- For an oversupplied mandi, the engine evaluates all destinations within 500 km and computes `S_composite = Σ w_k·f_k ∈ [0,100]`. — [Report, §2.4, lines 407-409]
- The weights are Demand Gap 0.20, Broker Reliability 0.20, Price Advantage 0.15, Transport Efficiency 0.15, Destination Saturation 0.10, Storage Availability 0.10 and En-Route Weather 0.10. — [Report, §2.4 table, lines 421-429]
- The formulas are as follows. Demand Gap = min(100, Deficit_dest/Oversupply_source ×100). Price Advantage ΔP = P_dest − P_source. Transport = max(0, 100 − Cost_100kg/5). Saturation = In-Transit/Deficit, which goes to 0 if incoming shipments fill more than 120% of the gap. Storage: Tier 1 perishables (Tomato, Banana) need cold storage and Tier 2 (Potato, Onion) need dry warehouses. Weather: transit rain or heat risk. — [Report, §2.4 table]

**§2.5 Predictive Demand & Anomaly Analytics (the core spec for this feature)**
- The input is "Region + Crop + Supply Volume (kg)". It feeds 5 analyzers. — [Report, §2.5, lines 436-442]
- (1) Dynamic Absorption Threshold Engine (`demand_ml_service.py`): "Traditional systems rely on static thresholds. ALIP computes dynamic demand capacity based on: Threshold_crop = Base_crop × M_region_type × M_density × M_market_size". "Urban centers with high population density are allocated higher capacity thresholds than rural feeder mandis." — [Report, §2.5, lines 444-447]. Note that this is a multiplicative formula, not the Gradient Boosting regressor that the code uses.
- (2) Statistical Z-Score & Supply Anomaly Detection (`supply_history_service.py`): `Z = (Current Supply − μ_history)/σ_history`. Z < 1.0 is normal, 1.0 ≤ Z < 2.0 is elevated and Z ≥ 2.0 is a critical anomaly. — [Report, §2.5, lines 448-451]
- (3) Multi-Signal Urgency Scorer (`urgency_service.py`): `Urgency = min(10, [Base(Oversupply Ratio)×M_perishability + Trend Boost] + Days Active)`. The tiers are: Tier 1 (Tomato, Banana) ×2.0, act within 1-2 days, "CRITICAL / EMERGENCY". Tier 2 (Potato, Onion, Maize) ×1.3, act within 5 days, "HIGH". Tier 3 (Rice, Wheat, Cotton) ×1.0, act within 14 days, "WATCH". — [Report, §2.5, lines 452-458]
- (4) 7-Day Price Trajectory & Decay Engine (`price_trajectory_service.py`): `P(t) = P0·(1−δ)^t` with δ ∈ [3%, 10%]. It computes cumulative losses per 100 kg and a "Break-Even Day (the exact calendar day beyond which transport freight exceeds remaining crop value)". It "Renders via Recharts AreaChart with a dashed break-even threshold line." — [Report, §2.5, lines 459-462]
- (5) Seasonal Harvest Context (`seasonal_context_service.py`): "Identifies peak harvesting months for each commodity. Flags whether market arrivals will self-correct naturally within 7–10 days or require aggressive geographical redistribution." — [Report, §2.5, lines 463-464]

**§2.6-2.10 Other broker features tied to demand**
- Freight: Small Truck 3 t at ₹25/km, Medium 10 t at ₹35/km, Large 20 t at ₹50/km. `ROI = (Agreed Price − Source Cost)×Q / (Distance×Rate)`. ROI ≥ 1.5 is "Good", 1.0 to 1.5 is "Acceptable" and below 1.0 is "Loss-Making". — [Report, §2.6, lines 468-478]
- The Regional Supply Explorer (/supply) uses bands Low < 200 kg, Medium 200-500 kg and High > 500 kg. Example query: "Guntur or Nashik". — [Report, §2.7, lines 481-483]
- The Listings Browser (/listings) supports search by farmer name, mandi location or crop, and filters by status (available, pending, sold). — [Report, §2.8]
- Alerts (/notifications): an Oversupply alert fires when "district arrivals exceed capacity by > 15%". An Undersupply alert fires "when inventory falls below minimum buffer stocks". — [Report, §2.9, lines 493-496]
- The shipment state machine runs Initiated ("Broker confirms deal in Demand Analysis") → In_Transit → Delivered or Cancelled. After delivery the counterparty submits a 1-5 star rating. — [Report, §2.10, lines 502-511]

**§3 Cross-module loop**
- "Farmer Produces & Lists ──> Ingested by Broker Registry ──> Broker Clears Oversupply ──> Price Signals Guide Farmer". — [Report, §3.1, line 522]
- Worked example: a farmer lists 2,500 kg of Tomato in Guntur at ₹22/kg. The broker runs Demand Analysis for Guntur and gets "Detects Oversupply (Z = 2.4, Urgency = 8/10, Day-7 Loss = ₹420/100kg)". The "Top 5 Destination Mandis (Hyderabad, Vijayawada, Chennai)" are shown. The broker selects Hyderabad ("ROI 2.1x, Distance 280km"), dispatches a Medium Truck and calls `POST /market/demand/initiate-shipment`. Then "Mandi prices & absorption data update Crop Recommendation algorithms". — [Report, §3.2, lines 538-552]
- Interaction matrix rows involving `/demand`:
  - Price Signal Transmission (Broker /demand → Farmer /crop) carries "Mandi price trajectories, demand gaps, MSP differentials".
  - Emergency Distress Clearing (Farmer /disease, /weather → Broker /demand): disease or storm events "trigger high-urgency broker notifications".
  - Logistics Coordination (Broker /demand → Farmer /profile).
  - Shared Auth & Role Guard: JWT bearer with `role: farmer` vs `role: broker`. — [Report, §3.3, lines 559-565]

**§6 Tech stack (as claimed)**
- The Broker Client is React 19 with Recharts. The backend is FastAPI on "Python 3.10". Crop inference uses LightGBM and Scikit-Learn. The Market Ranker is "Python Mathematical Engine" in market_ranking_service.py. The Logistics Engine is "45+ Mandi Freight Optimizer" in shipment_service.py. The database is "MongoDB Atlas / PyMongo". — [Report, §6, lines 571-582]

**§7 API catalog (as claimed) for market/demand**
- The report lists `POST /market/listing/add`, `GET /market/listings`, `GET /market/supply/{region}`, `GET /market/summary`, `GET /market/demand/threshold/...` ("Predict dynamic absorption threshold for mandi"), `POST /market/demand/trend/...` ("statistical supply trend and momentum"), `GET /market/demand/price-impact/..` ("price decay and break-even day"), `GET /market/demand/analysis/...` ("Full 7-Factor Weighted Market Ranking Engine") and `POST /market/demand/initiate-ship..` ("Dispatch freight logistics"). — [Report, §7, lines 617-625]
- Broker UI routes in the catalog: `/demand` is "7-Factor Demand Intelligence & Destination Ranking". `/profile` is "Broker Trading Identity & Reliability Rating". — [Report, §7, lines 600-605]

### Inferences
- The report is aspirational. It reads like a target spec for the redesign, not a description of the code.
- The report's own threshold formula (multiplicative) is not the GBR model in the code. A redesign must pick one and make the write-up consistent.
- The report never names a real market-price data source. "Mandi prices", "Historical Supply Records" and "MSP differentials" are named without a dataset behind them.

### Gaps
- The report gives no dataset, training procedure, target definition or evaluation metric for the demand model. The 2014-holdout metrics in §1.3 are for crop recommendation only.
- The report does not define "Base_crop", the multiplier values M_*, the "Trend Boost", "Days Active", the δ value per crop, or the "minimum buffer stocks".
- The report has no section explicitly titled "changes needed". If the user has a separate list of required changes, it is not in this file.

## Q2. How is demand analysis currently built (end-to-end data flow, model, endpoints, UI)?

### Takeaway
The UI calls one endpoint, `GET /market/demand/{region}`. The backend aggregates "available" listings, either from MongoDB `market_data` or from a JSON fallback, by region and crop. It falls back to a hard-coded demo seed when there are no listings. For crops it knows, it predicts an "expected demand" for each region with a 6-feature GradientBoostingRegressor trained on 56 hand-written rows embedded in the source. Supply is classified as oversupply if supply > 1.5×demand and undersupply if supply < 0.5×demand. Redistribution options are nearest-first by Haversine distance. Price impact uses a fixed elasticity table. Three further endpoints (threshold, trend, price-impact) exist but the UI never calls them.

### Cited Findings

**Frontend entry and routes**
- `/demand` is wrapped in `<ProtectedRoute role="broker">`. The role check happens only on the client against `user.role`. — [App.js, lines 26-31, 59-61]
- The DemandAnalysis page has a single text input "region" and quick pills for Hyderabad, Chennai, Mumbai, Delhi, Bangalore, Pune and Kolkata. Clicking Analyse calls `getDemandAnalysis(region)`. There is no crop selector, no supply-volume input and no date input. — [UI_DA, lines 10-27, 97-103]
- `getDemandAnalysis = (region) => api.get(\`/market/demand/${region}\`)`. Unlike the other helpers, this one does not call encodeURIComponent, and it never sends the optional `crop` query parameter. — [api.js, lines 62-63]
- The UI renders `result.alerts` as cards (type, message and action), and `result.crop_analysis` per crop with current_supply_kg, expected_demand_kg, a supply_demand_ratio bar (barPct = ratio×50, so 2× fills the bar), the recommendation text, redistribution pills ("Send to / Source from {region} · {kg}") and a price_impact line (price_drop_pct + recommendation). It also reads `item.description`, which the API never returns. It uses no charts at all: no recharts and no framer-motion. — [UI_DA, lines 107-285]
- The UI text claims "real-time market supply–demand balance" and "Expected demand is estimated from the crop, season and regional market profile." — [UI_DA, lines 163-165, 294-297]

**Backend route → service**
- `GET /market/demand/{region}?crop=` → `analyze_demand(region, crop)` in market_service. — [market_routes, lines 48-54]
- The region router is mounted with `prefix="/market"`, which places its endpoints under `/market/regions/*` and `/market/demand/{threshold|trend|price-impact}/*`. — [main.py, lines 34-35]
- Live OpenAPI endpoints for the market: `/market/listing/add` (POST), `/market/listings`, `/market/supply`, `/market/supply/{region}`, `/market/demand/{region}`, `/market/summary`, `/market/thresholds`, `/notifications/alerts`, `/market/regions/nearest/{region}/{crop}`, `/market/regions/distance/{r1}/{r2}`, `/market/regions/all`, `/market/regions/info/{region}`, `/market/demand/threshold/{region}/{crop}`, `POST /market/demand/trend/{region}/{crop}` (body: list of numbers) and `/market/demand/price-impact/{region}/{crop}/{supply_kg}`. The API has no `/market/demand/analysis/...` and no `/market/demand/initiate-shipment`. — [live openapi.json]

**analyze_demand data flow** [mkt_svc, lines 398-456]
1. `_load_regional_supply_index()` reads Mongo `market_data.find({"status":"available"})` and sums quantity_kg into `{region:{crop:kg}}` (keys lower-cased). If that is empty, it returns `_seed_demo_regional_data()`, a hard-coded set of 7 cities × 3 crops (for example hyderabad rice 650, maize 420, cotton 220). — [mkt_svc, lines 91-105, 128-142]
2. On PyMongoError it reads the local JSON store `backend/data/local_market_listings.json` the same way, and also falls back to the demo seed if that is empty. — [mkt_svc, lines 120-125, 430-454]; the store is in [local_market_store.py]
3. In the Mongo path, if the region has no supply, it falls back to the Hyderabad demo seed regardless of the region requested (`fallback_region = "hyderabad" if region_key else "hyderabad"`). — [mkt_svc, lines 412-418]
4. `_build_demand_result`: for each crop in the region's supply, it estimates expected demand for every candidate region (26 REGIONS + regions with data + the queried region). That means up to about 27 model predictions per crop on each request. — [mkt_svc, lines 191-219]
5. `_estimate_expected_demand`: if the crop is not in CROP_MAP (rice, wheat, maize, cotton, sugarcane, groundnut, soybean), it uses the static `DEMAND_THRESHOLDS` (rice 500, maize 400, cotton 300, tomato 200, onion 250, wheat 600, sugarcane 800, default 300). Otherwise it calls `predict_dynamic_threshold` with region_type, population_density and market_size from region_service.REGIONS. Unknown regions default to semi-urban, 3000 and medium. — [mkt_svc, lines 163-188]; [da, lines 596-605]
6. `build_market_signal`/`classify_supply`: oversupply if qty > 1.5×threshold, undersupply if qty < 0.5×threshold, otherwise balanced. Severity is high for oversupply, medium for undersupply and low otherwise. — [da, lines 672-677, 819-884]
7. `find_redistribution_options`: candidates come from REGION_COORDINATES plus regions with data. An oversupplied source is matched to undersupplied destinations, with transferable = min(source−threshold, dest_threshold−dest_qty), and vice versa. Results are sorted by distance and the top 3 are kept. — [da, lines 725-790]
8. `estimate_price_impact` is attached only when the status is oversupply. — [mkt_svc, lines 222-227]
9. Signals are upserted into the Mongo `market_alerts` collection by id `{region}_{crop}_{type}`. — [mkt_svc, lines 145-160, 421]
- Response shape: `{success, region, analysis:{crop:kg}, expected_demand:{crop:kg}, crop_analysis:{crop:{current_supply_kg, expected_demand_kg, supply_demand_ratio, market_status, demand_model, season, recommendation, redistribution_options[], price_impact}}, alerts[], recommendations[], signals[], thresholds, total_alerts, storage?}`. Live example for Hyderabad: rice 650 vs 691 (0.94, balanced), maize 420 vs 527, cotton 220 vs 520 (0.42, undersupply, no redistribution options). — [live /market/demand/Hyderabad]
- A live call for Delhi with the local store returned empty analysis and crop_analysis with storage "local". Delhi is one of the UI's quick pills but is not in REGIONS or REGION_COORDINATES. — [live /market/demand/Delhi]; [UI_DA, line 98]

**The ML model (demand_model.pkl)**
- The algorithm is `GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)`. The features are `[crop_enc, season_enc, region_type_enc, population_density, market_size_enc, month]` and the target is `demand_threshold_kg`. — [ml_svc, lines 37-41, 120-141]
- The training data is 56 hand-typed rows (`X_TRAIN`/`Y_TRAIN`) hard-coded in the module. The density values reuse the REGIONS population_density numbers. The targets are invented round numbers (for example 820, 650, 1100). Only 7 crops are covered. Wheat appears only in rabi and every other crop mostly in kharif. No zaid rows exist. No real source is cited. — [ml_svc, lines 42-116]
- Training runs a 5-fold CV R² and prints it, without saving it. It then fits on all the data and dumps to `data/demand_model.pkl`. At import time, `get_demand_model()` loads the pickle if it exists and otherwise trains. The relative paths (`os.makedirs("data")`, `MODEL_PATH = "data/demand_model.pkl"`) depend on the process working directory. — [ml_svc, lines 22, 118-154]
- If the model is unavailable, the fallback returns a 500 kg "fallback-static" threshold. — [ml_svc, lines 169-180]
- Pickle inspection: type `sklearn.ensemble._gb.GradientBoostingRegressor`, n_estimators 100, max_depth 4, `feature_names_in_` None (fitted on a bare numpy array), n_features_in_ 6. It loads cleanly under Python 3.12.12 and sklearn 1.7.2. The file is 213,720 bytes with mtime Oct 15 01:33, so it was regenerated recently. Sample predictions: rice/kharif/urban/18480/large/Jul → 813.4; rice/rabi/urban/Jan → 683.4; unknown crop (7)/semi-urban/Oct → 343.4. — [pkl]
- Encoding mapping: crop is label-encoded as an ordinal integer, with unknown crops mapped to 7 ("default"), which never appears in the training data. Season is derived from the month with a fixed SEASON_MONTHS map (Oct = kharif, Nov-Mar = rabi, Apr-May = zaid). — [ml_svc, lines 25-35, 182-194]

**Other demand functions**
- `analyze_supply_trend(history, threshold)` fits a linear regression with np.polyfit over a caller-supplied list. pct_change = slope/mean. The labels are rapidly_increasing (>15%), increasing (>5%), decreasing and rapidly_decreasing. Weeks-to-breach is computed against 1.5×threshold, and "periods" are assumed to be weeks. — [ml_svc, lines 211-311]
- `estimate_price_impact`: %ΔP = elasticity × %ΔQ using a hard-coded `PRICE_SENSITIVITY` table of base prices and elasticities (for example rice ₹22 / −0.35, cotton ₹65 / −0.25, sugarcane ₹3 / −0.20). The urgency labels are critical below −30%, high below −15% and medium otherwise. — [ml_svc, lines 313-402]
- `region_service.get_nearest_regions` ranks nearby regions by distance − 5×demand_score, where demand_score is a heuristic over population density, market size, local production and region type. Suitability bands are <150 km, <250 km and <350 km. — [region_svc, lines 55-99, 160-190]

**Broker dashboard**
- BrokerDashboard calls only `getMarketSummary()` and shows Total Listings, Active Regions, Crop Types and "Active Deals" = `Math.round(total_listings * 0.73)`. — [UI_BD, lines 4, 228-236, 349-366]
- `/market/summary` returns `{total_listings, regions_active, regional_summary, thresholds}`. In the Mongo path it has no demo fallback. — [mkt_svc, lines 459-497]
- The dashboard has a "More coming soon" card: "Trade history, price forecasting and farmer messaging are in development." — [UI_BD, lines ~427-432]

**Listings input**
- CropListing.js uses free-text Location ("City/District") and Crop Name ("e.g. rice, wheat") inputs and posts to `/market/listing/add`. The backend lower-cases and strips both. The pydantic `CropStatus` values are available, sold and reserved. The report says available, pending and sold. — [CropListing.js, lines 102-107]; [mkt_svc, lines 29-39]; [models/market.py]
- AllListings.js loads `/market/listings` and filters on the client by crop and status. — [AllListings.js, lines 3-48]

### Inferences
- The "ML" in demand analysis amounts to a smoothed lookup over invented numbers. Its output depends almost entirely on static region attributes (density, market size), the crop index and the month. It ignores actual listings history, prices and time series.
- Expected demand is static per region and crop within a month. Nothing in it reacts to market conditions.

### Gaps
- The CV R² from training is printed but not persisted, so the current pickle's score is unknown. I did not retrain it, per the constraints.
- MongoDB health could not be confirmed during the live calls (/health/database returned no body within 5 s). The live responses came from the local or demo path.

## Q3. What are the concrete weaknesses and gaps between the report and the code?

### Takeaway
The current feature uses synthetic data and has no time dimension. It shows no real prices and no evaluation, and it falls back to demo data silently. Most of what the report promises for /demand (Z-score, urgency, price trajectory, seasonal context, 7-factor ranking, shipments, ratings) does not exist in the code.

### Cited Findings

**Data**
- The training data is 56 hard-coded synthetic rows with no provenance. — [ml_svc, lines 42-116]
- The base prices and elasticities are hard-coded constants. No mandi price feed (Agmarknet or data.gov.in) exists anywhere in the code. The listing `price_per_kg` is averaged only in `/market/supply` and is never used in demand analysis. — [ml_svc, lines 313-322]; [mkt_svc, lines 42-63]
- Demo seed data (7 cities) is substituted silently when no listings exist. `/market/demand` does not return an `is_demo` flag, whereas `/market/supply` does. — [mkt_svc, lines 91-105, 128-142, 348-359, 423-429]
- If a region has no supply in the Mongo path, the Hyderabad demo seed is returned under the queried region's name. — [mkt_svc, lines 412-418]

**No time dimension**
- Supply is the sum of quantity_kg over all currently "available" listings regardless of created_at. The service keeps no history. The trend endpoint needs the caller to send the history list, and the UI never does. — [mkt_svc, lines 128-142]; [region_routes, lines 570-605]
- The report's Z-score anomaly detection (`supply_history_service.py`) and "Historical Supply Records" do not exist. — [Report, §2.5]; file listing of backend/services

**Model and evaluation**
- No held-out metrics are saved or exposed. CV R² is printed only during training. No backtest exists, and nothing compares the model to the static thresholds. — [ml_svc, lines 133-137]
- Crop is ordinal-encoded into a tree model. Unknown crops map to code 7, which is absent from training. Tomato and onion, which are central to the report's urgency tiers and Guntur tomato example, are not in CROP_MAP and use static thresholds. — [ml_svc, line 25]; [mkt_svc, lines 163-169]
- The report's threshold formula (Base×M_region×M_density×M_market) is not what the code does (GBR). — [Report, §2.5]; [ml_svc]

**Mismatches between UI, API and report**
- The UI calls only `/market/demand/{region}`. It never uses `/market/demand/threshold`, `/trend` or `/price-impact`, or `getRegionalDemandEstimate` (defined in api.js but unused by DemandAnalysis.js). — [api.js, lines 86-89]; [UI_DA]
- The UI has no crop filter or supply input, although the report's input is "Region + Crop + Supply Volume (kg)". — [UI_DA]; [Report, §2.5]
- The `Delhi` pill has no region data. `getDemandAnalysis` does not URL-encode its parameter. `item.description` is never returned. — [UI_DA, lines 98, 192]; [api.js, line 63]
- The report's endpoints `GET /market/demand/analysis/...` and `POST /market/demand/initiate-shipment` do not exist. Neither do the services market_ranking_service, urgency_service, price_trajectory_service, shipment_service, reliability_service, seasonal_context_service and supply_history_service, or the shipments and ratings collections. — [live openapi.json]; [backend/services listing]
- The report says the UI uses a Recharts AreaChart with a break-even line. DemandAnalysis.js imports no chart library. — [Report, §2.5 item 4]; [UI_DA, lines 1-4]
- The report claims "45+ Mandi Spatial Distance Index". The code has 26 entries in REGIONS (region_service) and a different list of 27 in REGION_COORDINATES (demand_analysis). For example, Guntur, Nellore, Khammam, Kurnool, Tirupati, Anantapur, Rajahmundry and Patna are only in REGIONS, and Mysore, Madurai, Kochi, Amritsar, Varanasi, Jodhpur, Surat, Visakhapatnam and Thiruvananthapuram are only in REGION_COORDINATES. Redistribution distances therefore come back as None for regions missing from REGION_COORDINATES, including Guntur from the report's flagship example. — [Report, §2.2]; [region_svc, lines 11-38]; [da, lines 608-636]
- The report's alert rule is "exceed capacity by > 15%". The code uses supply > 1.5× threshold (+50%) for oversupply and < 0.5× for undersupply. — [Report, §2.9]; [da, lines 672-677]
- The report's listing status is available/pending/sold. The model's is available/sold/reserved. — [Report, §2]; [models/market.py]
- The report says Python 3.10 and LightGBM. The venv is Python 3.12.12, and requirements.txt has no lightgbm. — [Report, §6]; [pkl]; [requirements.txt]
- The dashboard's "Active Deals" figure is invented (total_listings × 0.73). — [UI_BD, line 363]

**Dead code, duplication and robustness**
- `region_service.get_nearest_regions` is defined twice. The second definition, with a different sort key, overrides the first. — [region_svc, lines 102-127, 160-190]
- `get_enhanced_demand_analysis` ("ALIP Enhanced Broker Intelligence v2.0") in market_service is never routed or called. — [mkt_svc, lines 533-591]; grep of backend
- `routes/broker.py` and `models/broker.py` are empty files, and the broker router is not included in main.py. `DemandQuery` in models/market.py is imported but unused. — [routes/broker.py]; [main.py]; [market_routes, line 2]
- region_routes.py repeats `from services.demand_ml_service import ...` mid-file three times, and `get_region_info` twice. — [region_routes, lines 1-10, 94-97, 136-140]
- Two parallel region systems exist (REGIONS with title-case keys plus metadata, and REGION_COORDINATES with lower-case keys and coordinates only), each with its own Haversine implementation. — [region_svc]; [da]
- There is no backend auth on the market endpoints. JWT is issued in auth.py, but no route uses `Depends` or validates a token. The role guard exists only in the React ProtectedRoute. — [routes/auth.py grep]; [App.js]
- Model paths are relative to the working directory, so starting uvicorn from another directory would retrain and write `data/demand_model.pkl` there. — [ml_svc, lines 22, 118]
- Each `/market/demand` request runs about 27 GBR predictions per crop and writes alert upserts on a GET. — [mkt_svc, lines 199-210, 421]

### Inferences
- For a final-year evaluation, the weakest points are synthetic training data with no metrics and the gap between the report's claims and the running system. Both are easy for an examiner to spot.
- The time dimension is the largest missing piece. Z-score, trend, price trajectory and seasonality all need dated supply and price records, which neither the listings collection nor any other store currently provides.

### Gaps
- I did not check whether the backend test suite covers demand analysis beyond `test_auth_registration.py`, which calls `get_all_market_alerts`.

## Q4. Which existing pieces can be reused?

### Takeaway
The listings pipeline, the Mongo-with-JSON-fallback pattern, the region metadata, the axios layer, the client role routing and the response pattern (crop_analysis, alerts, redistribution options) are solid foundations. The model, the static price table and the demo seeding should be replaced or clearly labelled.

### Cited Findings
- **Auth and roles:** `/auth/register` and `/auth/login` issue a JWT with role farmer or broker (create_access_token in config/security). A local user store exists at `backend/data/local_users.json` (gitignored). The client `ProtectedRoute role="broker"` guards /broker, /demand, /supply, /listings and /notifications. — [routes/auth.py, lines 23-45]; [App.js]; [.gitignore]
- **Listings collection:** Mongo `market_data` documents hold farmer_name, location (lower-case), crop_name (lower-case), quantity_kg, price_per_kg, status, contact and created_at (UTC). These timestamps could seed a time series of supply and asking prices. — [mkt_svc, lines 29-39]
- **JSON fallback store:** `local_market_store.py` provides `insert_listing` and `find_listings(query)` with an equality-match query and a thread lock, stored in `backend/data/local_market_listings.json` (gitignored). The pattern of catching PyMongoError and falling back to local storage is used in every market service function. — [local_market_store.py]; [mkt_svc]
- **Alert persistence:** the `market_alerts` collection is upserted with created_at and updated_at. It could become a crude history of signals. — [mkt_svc, lines 145-160]; [config/database.py]
- **Region data:** REGIONS has 26 cities with lat, lng, state, population_density, region_type, primary_crops and market_size. Helpers include get_region_info (case-insensitive), get_nearest_regions, get_distance_between and get_all_regions, exposed under `/market/regions/*`. — [region_svc]; [region_routes]
- **Classification and redistribution logic:** classify_supply, find_redistribution_options (with transferable qty and direction) and build_action are reusable with a new demand source. — [da, lines 672-884]
- **Trend and price-impact functions:** these are usable building blocks once real history exists. — [ml_svc, lines 211-402]
- **Database config:** Motor `AsyncIOMotorClient` with a 5 s timeout. MONGODB_URL defaults to localhost:27017 and the DB to `alip_local`. The collections are users, farmer_data, broker_data, market_data and market_alerts. — [config/database.py]
- **axios layer:** base `http://127.0.0.1:8000`, an interceptor adds `Bearer` from localStorage, and helpers exist for market, supply, regions, nearest, distance, regional demand estimate and notifications. — [api.js]
- **Notifications:** `GET /notifications/alerts` → `get_all_market_alerts()` computes signals for every region, with high and medium counts. — [routes/notifications.py]; [mkt_svc, lines 500-530]
- **Existing datasets in backend/data:** Crop_recommendation.csv, crop_model.pkl, label_encoder.pkl, weather_model.pkl, soil_data.py and local_users.json. None contain market prices or arrivals. — [backend/data listing]

### Inferences
- A redesign can keep the `/market/demand/{region}` contract shape (crop_analysis, alerts, redistribution_options) so that the current UI degrades gracefully, while adding time-series fields.
- The two region tables should be merged into one source before more geography is added.

### Gaps
- I did not read config/security.py (JWT secret and expiry) or middleware/ in detail.

## Q5. Tech stack and constraints

### Takeaway
The backend is FastAPI on Python 3.12.12 with scikit-learn 1.7.2, Motor 3.7.1 and pymongo 4.17, running on port 8000. The frontend is CRA (react-scripts 5) with React 19, recharts 3.8.1, framer-motion 12.40 and lucide-react, using inline-style components.

### Cited Findings
- The venv runs Python 3.12.12 with scikit-learn 1.7.2. — [pkl]
- requirements.txt pins fastapi 0.128.0, starlette 0.50.0, uvicorn 0.40.0, motor 3.7.1, pymongo 4.17.0, pydantic 2.12.5, numpy 2.2.6, pandas 2.3.3, polars 1.39.2, scipy 1.15.3, scikit-learn 1.7.2, joblib 1.5.2, requests 2.32.5, httpx 0.28.1, torch 2.5.1+cu121, tensorflow 2.20.0 and google-genai. It has no lightgbm, statsmodels, prophet or xgboost. — [backend/requirements.txt]
- Frontend dependencies are axios ^1.16.1, framer-motion ^12.40.0, lucide-react ^1.16.0, react and react-dom ^19.2.6, react-router-dom ^7.15.1, react-scripts ^5.0.1, recharts ^3.8.1, react-hot-toast, react-markdown and remark-gfm. — [frontend/alip-frontend/package.json]
- The backend serves on 127.0.0.1:8000 (live), with CORS allowing all origins. FastAPI app version is "1.0.0". — [main.py, lines 13-25]; [live]
- Git history has 4 commits: 3542fff Initial commit, f91d098 "Add ALIP project source" (2026-10-08, which added all demand files: demand_analysis.py 293 lines, demand_ml_service.py 402, market_service.py 591, DemandAnalysis.js 703), 3b74fcb merge, and 588b73e "Update weather advisory with disease integration, enhance dashboards and API". The demand code has had no history since the initial import. — [git log]
- `backend/data/local_market_listings.json`, `local_users.json` and `.env` files are gitignored. — [.gitignore]

### Inferences
- New time-series or forecasting work fits within numpy, pandas, scikit-learn and scipy without new heavy dependencies. statsmodels or lightgbm would be new additions.
- Recharts is already installed, so the report's promised AreaChart with a break-even line can be built without new frontend dependencies.

### Gaps
- No real mandi or arrivals dataset is present in the repo. Sourcing one (for example Agmarknet or data.gov.in daily prices) falls outside this audit's scope.
