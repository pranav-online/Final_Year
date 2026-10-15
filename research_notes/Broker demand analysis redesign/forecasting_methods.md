# Forecasting Approaches for Mandi Demand, Arrivals and Prices (Final-Year Project Stack)

Scope note: 15 tool calls were used. Several key full texts (Nature/Scientific Reports, Springer, Taylor & Francis, PMC) blocked automated fetching, so some numbers below come from search-result summaries of those papers, not from reading the full papers. These are marked "(abstract/summary-level)". Check them against the PDFs before quoting them in a report.

---

## 1. Defining and proxying "demand" when only prices and arrivals are observable

### Takeaway
Agmarknet gives a daily price (min/max/modal) and an arrival quantity for each market and commodity. It records no consumption or offtake, so true demand cannot be observed. The standard framing is: arrivals are realised supply, the price is the clearing outcome, and "demand pressure" is inferred from how price responds to arrivals relative to normal. For a broker, present a "Demand-Supply Pressure Index", not a "demand forecast".

### Cited Findings
- Studies of onion in Western Maharashtra, including Lasalgaon, find a negative arrivals–price relationship across years in all markets. In individual months, though, arrivals and prices were sometimes positively related, which is what happens when a demand shift dominates a supply shift (summary-level) — [IJH / IAHS journal](https://journal.iahs.org.in/index.php/ijh/article/download/214/1434)
- An IIM Bangalore analysis of daily Agmarknet price–volume data reportedly estimated a mandi demand curve. The curve was flat (inelastic) below a threshold price and sloped downward with an elasticity of about −1 above it. This was a pooled national analysis. The page could not be fetched to verify it (summary-level) — [IIMB Centres of Excellence page](https://iimb.ac.in/node/3547)
- Onion prices at Lasalgaon are strongly seasonal. The seasonal index peaks in October, followed by November and August, and is lowest in May (summary-level) — [CUP Trends and Price Behaviour Analysis of Onion in India](https://kr.cup.edu.in/items/87f898c8-94ae-42a9-8c76-4a0ad1f72d50/full); [AgEcon Search record](https://ageconsearch.umn.edu/record/345214/files/Trends%20and%20Price%20Behaviour%20Analysis.pdf)
- Seasonality influences onion price behaviour but is not the only factor (summary-level) — [Krishikosh: Economic analysis of price behaviour of onion in major markets](https://krishikosh.egranth.ac.in/items/24c6ba25-787c-476a-93a7-4630eaa1d229)
- IBM Research used historical price, market arrival quantities and weather together as inputs for tomato and maize price models across 14 Indian markets. This treats arrivals as the supply-side driver — [IBM Research: context-based model selection for crop price forecasting](https://research.ibm.com/publications/towards-context-based-model-selection-for-improved-crop-price-forecasting)

### Inferences
- A pragmatic, explainable broker framing:
  - **Supply signal**: arrivals relative to the seasonal norm, `arr_ratio = arrivals_7d / median(arrivals, same ISO-week, previous 3 years)`.
  - **Price signal**: price relative to the seasonal norm, `price_ratio = modal_7d / median(modal, same week, previous years)`, plus 7-day and 28-day momentum.
  - **Demand-Supply Pressure Index (DSPI)**: z-score(price momentum) − z-score(arrival anomaly), or equivalently the residual from a regression of log price on log arrivals plus seasonality. A positive residual means price is higher than current arrivals would justify, which suggests demand pressure. A negative residual means a glut or weak demand.
  - Quadrant labels are easy for a broker to act on:
    - High arrivals and rising price: strong demand.
    - Low arrivals and rising price: supply shortage.
    - High arrivals and falling price: glut.
    - Low arrivals and falling price: weak demand.
- Call it an "index" or "pressure", never "demand quantity". Say plainly that it is inferred.
- Because the elasticity is nonlinear (the IIMB finding of a flat-then-sloped curve), fit the price–arrival relationship in log space, or let a tree model learn it, rather than assuming a constant elasticity.

### Gaps
- I found no peer-reviewed Indian study that formally defines a composite "mandi demand index" from prices and arrivals. The DSPI above is a design proposal, not an established method.
- I could not verify the IIMB elasticity finding at its source because the site was unreachable.

---

## 2. Methods used for Indian commodity price and arrival forecasting, with reported accuracy

### Takeaway
Indian studies span ARIMA/SARIMA, hybrids (ARIMA-ANN, ETS-SVM, wavelet-ANN), tree ensembles (RF, XGBoost, LightGBM) and deep models (LSTM, GRU, NBEATSX). Deep or hybrid models often "win" in papers, but the margins depend on the series, the horizon and the test window, and baselines are often weak or missing. For a student team on a CPU, the best value is seasonal-naive/MA baselines, then SARIMA or ETS, then one LightGBM with lag and rolling features. LSTM is optional at most.

### Cited Findings
**Onion / potato / tomato (TOP)**
- A study of retail prices compared Auto-ARIMA, RNN, LSTM, VAR, Random Forest and XGBoost. LSTM was best for onion and tomato, and XGBoost was best for potato (summary-level) — [ResearchGate: Indian Commodity Market Price Comparative Study of Forecasting Methods – Onion, Potato, Tomato](https://www.researchgate.net/publication/358037089_Indian_Commodity_Market_Price_Comparative_Study_of_Forecasting_Methods_-_A_Case_Study_on_Onion_Potato_and_Tomato)
- A study of monthly retail and wholesale TOP prices found that hybrids won, and the winner differed by commodity:
  - Onion: Additive-ARIMA-ANN.
  - Potato: Multiplicative-ETS-SVM.
  - Retail tomato: Multiplicative-ARIMA-SVM.

  The full paper returned 403, so this is summary-level — [Applied Artificial Intelligence (T&F) 2021: Time Series Forecasting of Price of Agricultural Products Using Hybrid Methods](https://www.tandfonline.com/doi/full/10.1080/08839514.2021.1981659)
- A study of daily AGMARKNET wholesale prices covered January 2010 to June 2024, 165 markets and 23 commodities:
  - GRU beat ARIMA. Reported GRU MAPE was about 16% for onion and about 15% for tomato, against about 92% for ARIMA (summary-level).
  - A separate summary of the same work gives a tomato GRU MAPE of 10.58%.
  - The authors list weather inputs as future work.

  An ARIMA MAPE of about 92% suggests a long multi-step ARIMA forecast without re-fitting, or a poorly specified ARIMA. Treat it as a weak baseline, not a fair comparison — [Scientific Reports 2025: Enhancing agricultural commodity price forecasting with deep learning](https://www.nature.com/articles/s41598-025-05103-z); [PMC copy](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12215695/)
- A study added weather (precipitation and temperature) as exogenous inputs for TOP prices in major Indian markets. NBEATSX had the lowest average error (RMSE 110.33), and the weather-augmented deep models beat the statistical and classical ML baselines (summary-level) — [Scientific Reports, Jul 2024 (DOAJ record)](https://doaj.org/article/3c3f82bed9ae413d868a2b0d8830f1de)
- For Agra potato prices, linear time-series models were compared with neural networks, and LSTM had the lowest MAPE and RMSE (summary-level) — [Potato Research (Springer) 2024](https://link.springer.com/article/10.1007/s11540-024-09838-6)
- For weekly TOP prices, a hidden-Markov-based deep learning model was compared with MLP, RNN, LSTM and GRU. LSTM-family MAPEs were reported at roughly 6–13% (on training data, per the summary) — [SSCA journal: Price Forecasting of TOP (Ramasubramanian et al.)](https://www.ssca.org.in/media/4_SA99102023_R2_SA_26112023_V_99yqeAF._Ramasubramanian_FINAL_Finally.pdf)
- ARIMA-only studies of onion markets in Gujarat reported post-sample MAPE of about 22–28% — [DSIMS journal (Laijawala & Gupta)](https://dsims.org.in/assets/files/r-vol/1.%20Mr.%20Parth%20Laijawala%20&%20Mr.%20Maneesh%20Gupta_1-19.pdf)
- ARIMA has been applied to Indian potato prices on its own — [Economic Affairs: Forecasting of Potato Prices in India, ARIMA](https://ndpublisher.in/files/html/ea-65-4-001.html)
- Tomato prices at Jabalpur were modelled with SARIMA–GARCH (monthly), and tomato arrivals and prices across 8 markets for 2010–2021 were modelled with SARIMA and VECM (summary-level) — [ICAR JISAS](https://epubs.icar.org.in/index.php/JISAS/article/download/181950/67167/541718); [Krishikosh thesis](https://krishikosh.egranth.ac.in/items/38e9401d-6642-4d30-9979-d281f6d283f5/full)

**Pulses / wheat / other crops**
- ICAR-IASRI (Anjoy, Paul, Sinha, Paul, Ray) built a wavelet (MODWT, Haar) plus ANN hybrid for multi-step forecasts of the monthly WPI of pulses. It was significantly better than plain ANN in all cases. The abstract gives no figures — [Indian Journal of Agricultural Sciences (ICAR ePubs)](https://epubs.icar.org.in/index.php/IJAgS/article/view/71022)
- A study of groundnut prices in Tamil Nadu used weekly Agmarknet prices and weather from 2010 to 2023. It compared LightGBM, XGBoost, HistGradientBoosting and CatBoost — [Scientific Reports 2025: Weather-driven groundnut price forecasting with boosting](https://www.nature.com/articles/s41598-025-08573-3)
- A study of 9 commodities in Maharashtra used AGMARKNET data from 2001 to October 2025, aggregated to monthly modal prices. It benchmarked ML models against naive baselines with expanding-window validation. The full text was blocked, so no numbers are available — [Springer 2026: Forecasting agricultural commodity prices using ML models](https://link.springer.com/article/10.1007/s44564-026-00015-0)
- An India-wide study of major food crops compared LR, SVM, AdaBoost, RF and XGBoost on environmental and economic factors. XGBoost was best with R² = 0.94 (an R² on levels is not a forecasting-skill metric) — [MDPI proceedings, doi 10.3390/blsf2025054007](https://doi.org/10.3390/blsf2025054007)
- Wheat: I found no IASRI wheat price-forecasting study with metrics.
  - A Türkiye daily wheat study reported an ensemble R² of 0.9942, and the authors acknowledge its short sample — [Sustainability 2026](https://www.mdpi.com/2071-1050/18/4/1960)
  - An Iranian study found that ARIMA+ANN hybrids beat either model alone on world wheat prices — [JEAD](https://jead.um.ac.ir/article_28847_en.html)
- A non-Indian comparison on Nepal's Kalimati vegetable price index found XGBoost the strongest standalone model, with R² = 0.824 — [arXiv 2605.30720](https://arxiv.org/pdf/2605.30720)
- Also non-Indian: a TCN-XGBoost hybrid reported lower error than ARIMA and LSTM on rice, wheat and corn — [PMC12047798](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12047798/)

**General evidence on global gradient boosting**
- In the M5 competition (42,840 Walmart series), a LightGBM won, and ML methods had their first clear win over statistical benchmarks. The top solutions were mostly gradient boosting (LightGBM, XGBoost, CatBoost) trained as global, cross-learning models over many related series — [M5 results paper (Makridakis, Spiliotis, Assimakopoulos)](https://statmodeling.stat.columbia.edu/wp-content/uploads/2021/10/M5_accuracy_competition.pdf); [Durham repository](https://durham-repository.worktribe.com/OutputFile/1207845); [Medium M5 learnings](https://medium.com/analytics-vidhya/predicting-the-future-with-learnings-from-the-m5-competition-d54e84ca3d0d)
- An open-source student-style project on Agmarknet data compares SARIMA, Prophet and LightGBM against a seasonal-naive baseline and adds a best-market comparison dashboard. It is a useful template, but its results are not peer-reviewed — [GitHub Agriculture_price_analyzer](https://github.com/kaushikitripathi13-a11y/Agriculture_price_analyzer)

### Inferences
- Accuracy band to expect: well-built models on Indian wholesale vegetable prices typically report MAPE in the low teens to mid-20s %. Weekly or monthly aggregates and short horizons sit at the low end, and daily or volatile series like tomato and onion sit at the high end. Prices of pulses and wheat are smoother, being influenced by MSP and procurement, so expect lower MAPE. That last point is my inference and not sourced. Numbers are not comparable across papers because frequency, horizon and test windows differ.
- Many "deep beats ARIMA" results compare against a weak ARIMA, are not rolling-origin, and omit seasonal-naive. A student project gains credibility by including those baselines.
- Best value for effort, in order:
  1. Seasonal-naive and moving-average baselines (minutes to build).
  2. SARIMA or ETS via statsmodels, per series, on weekly data.
  3. A global LightGBM over all commodity-market series with lag, rolling, calendar and arrival features, plus quantile objectives for ranges.
  4. Prophet as an optional comparator, which is easy to fit with Indian holidays.
  5. LSTM/GRU only as a stretch goal. They are CPU-feasible on weekly data but rarely worth the tuning time for a student team.
- Forecast weekly aggregates (the median modal price per week) rather than raw daily data. Daily Agmarknet data has gaps (market holidays, missing reports) and noise.

### Gaps
- I could not extract per-model MAPE/RMSE tables for onion, tomato or potato from the full texts (paywalls and bot-blocks).
- I found no Indian study that reports LightGBM vs SARIMA vs seasonal-naive under rolling-origin CV with published numbers.
- I found no reliable arrivals-forecasting accuracy figures, as most studies forecast price.

---

## 3. Feature engineering

### Takeaway
The proven core is lags, rolling statistics of price and arrivals, and calendar seasonality. Weather and nearby-market prices are useful additions. Festival and kharif/rabi effects are domain-motivated, but I found little Indian quantification of them.

### Cited Findings
- Historical prices, market arrival quantities and weather (which affects production and transport) were used together as features for Indian tomato and maize price models — [IBM Research](https://research.ibm.com/publications/towards-context-based-model-selection-for-improved-crop-price-forecasting)
- Adding precipitation and temperature improved deep-model accuracy for TOP prices in Indian markets (summary-level) — [Scientific Reports 2024 (DOAJ)](https://doaj.org/article/3c3f82bed9ae413d868a2b0d8830f1de)
- Weekly weather combined with Agmarknet prices drove boosting models for groundnut prices in Tamil Nadu — [Scientific Reports 2025 groundnut](https://www.nature.com/articles/s41598-025-08573-3)
- Onion prices show stable month-of-year seasonality: the peak is in October–November and the trough in May (Lasalgaon) — [CUP onion study](https://kr.cup.edu.in/items/87f898c8-94ae-42a9-8c76-4a0ad1f72d50/full)
- Onion prices across major markets, including Lasalgaon, move together in long-run equilibrium (cointegrated). This supports using prices in related or lead markets as features (summary-level) — [serialsjournals onion integration](https://serialsjournals.com/abstract/12495_14.pdf)
- In wheat markets, Delhi prices lead regional markets, and the lead–lag relationship is linked to distance and transaction costs (summary-level) — [CUP: Market integration and price transmission in wheat markets of India](https://kr.cup.edu.in/handle/32116/4443)
- Lead, lag and isolated markets can be identified within a state, for example in paddy — [AgEcon Search: Investigating commodity price](https://ageconsearch.umn.edu/record/345189/files/Investigating%20Commodity%20Price.pdf)

### Inferences
Recommended feature set for a global LightGBM. Keys are (commodity, market, week), and every feature must be computable using only data up to the forecast origin t.

- **Target**: log(modal price) at t+h. You can also predict log(P_{t+h}/P_t) directly and convert back, which stabilises a global model across price levels.
- **Price lags**: 1, 2, 3, 4, 8, 13, 26 and 52 weeks.
- **Rolling statistics** (shifted so they end at t): mean, std, min and max over 4, 8, 13 and 26 weeks; the rolling coefficient of variation; momentum `P_t/P_{t-4} − 1`; and `max − min` spread, using Agmarknet's min and max price columns.
- **Arrivals**: the log arrivals lags and rolling means listed above, the arrival anomaly against the same week in prior years, and the cumulative arrivals since the start of the season.
- **Calendar**: week-of-year (as a raw value or as sin/cos), month, and the crop-season flag. Kharif harvest arrivals run roughly October–December, rabi roughly March–May, and late-kharif onion December–February. These are approximate and should be verified per crop and state.
- **Festival flags**: Diwali, Navratri/Dussehra, Ganesh Chaturthi, Eid and Holi windows (−2 to +1 weeks), from the Python `holidays` package with country="IN". Prophet accepts these as a holidays dataframe.
- **Spatial**: same-commodity price in the nearest 3–5 markets, or the state mean and the national median (lag ≥ 1); the spread to the reference or lead market (Lasalgaon for onion, Delhi Azadpur for vegetables and wheat); and national total arrivals.
- **Policy and exogenous** (optional): the MSP flag or level for wheat and pulses, and export-ban or stock-limit dummies, especially for onion. Weather comes from NASA POWER or Open-Meteo: lagged rainfall and temperature anomalies in the producing district.
- **IDs**: commodity, market and state as categorical features for LightGBM.

### Gaps
- I found no Indian paper that quantifies the effect of festival dummies on mandi prices.
- I have no sourced, crop-specific kharif/rabi arrival calendars. The months above are general agronomic knowledge and need verification against Agmarknet arrival seasonality.

---

## 4. Evaluation protocol

### Takeaway
Use rolling-origin (expanding-window) backtesting at the horizons the broker cares about (1–4 weeks). Report MAE, RMSE and MASE/RMSSE against seasonal-naive and naive baselines, and keep MAPE only as a secondary, audience-friendly metric. Check interval coverage empirically.

### Cited Findings
- Rolling forecasting origin: each training set uses only data before the test point, the earliest observations are never test sets, and accuracy is averaged over the origins. "A good way to choose the best forecasting model is to find the model with the smallest RMSE computed using time series cross-validation." — [Hyndman & Athanasopoulos, FPP3 §5.10](https://otexts.com/fpp3/tscv.html)
- "With time series forecasting, one-step forecasts may not be as relevant as multi-step forecasts". Evaluate at the needed horizon. Error grows with the horizon, and residual (in-sample) accuracy understates true error — [FPP3 §5.10](https://otexts.com/fpp3/tscv.html)
- Accuracy metrics:
  - MAE targets the median and RMSE the mean, and both are scale-dependent.
  - MAPE is undefined or extreme near zero and penalises negative errors more heavily.
  - FPP3 recommends against sMAPE.
  - MASE/RMSSE scale errors by the in-sample (seasonal) naive MAE, and a value < 1 means the model beats the naive benchmark. "MASE or RMSSE are often preferable scale-free measures".
  - Different metrics can rank methods differently.

  — [FPP3 §5.8](https://otexts.com/fpp3/accuracy.html)
- Expanding-window validation against naive baselines has been used for AGMARKNET monthly modal prices — [Springer 2026](https://link.springer.com/article/10.1007/s44564-026-00015-0)
- Prediction intervals in skforecast:
  - It implements split conformal prediction: an empirical quantile of absolute out-of-sample residuals is added to and subtracted from the forecast, with optional bins so the width scales with the predicted value.
  - Conformal calibration can also correct bootstrapped or quantile-regression intervals.
  - "The empirical coverage should always be validated with backtesting".
  - In-sample residuals gave only ~61% coverage for a nominal 80% interval.
  - With a single correction factor, coverage is above nominal at early steps and below it at later steps.
  - The page provides `calculate_coverage` and `winkler_score` for evaluating intervals.

  — [skforecast conformal prediction guide](https://skforecast.org/latest/user_guides/probabilistic-forecasting-conformal-prediction)

### Inferences
Concrete protocol for weekly data from about 2015 onward:
1. **Hold-out**: keep the last 52 weeks as the final test set, untouched until the end.
2. **Backtest on the remaining data**: use expanding-window origins every 4 weeks over the last 2–3 years, with horizons h = 1, 2 and 4 weeks (about 7, 14 and 30 days). Re-fit statistical models at each origin. Re-fit LightGBM every 4–13 origins to save CPU.
3. **Baselines**:
   - Naive (last value).
   - Seasonal naive (same week last year).
   - 4-week moving average.
   - Optionally drift.
4. **Metrics**:
   - Report MAE (₹/quintal, which the broker can interpret), RMSE and MASE (seasonal-naive scaled) per commodity × market × horizon.
   - Add MAPE for communication.
   - Add the directional accuracy of the up/down call, because brokers act on direction.
   - Add the "% of series where MASE < 1".
5. **Intervals**: produce LightGBM quantile models (α = 0.1, 0.5, 0.9) or split-conformal residual intervals. Report empirical coverage of the 80% interval (target 75–85%), pinball loss and the Winkler score.
6. **Significance**: optionally run Diebold–Mariano (statsmodels has no built-in DM test, but it is about 20 lines of code), or simply report the win rate over baselines across series.

### Gaps
- I found no Indian study reporting interval coverage for mandi price forecasts, so no domain benchmark for coverage is available.

---

## 5. Broker-facing outputs and which are reliable enough to show

### Takeaway
Reliable enough to show: 1–4 week forecasts with 80% ranges, trend and momentum, volatility, seasonal-norm comparisons, and price spreads between markets. Show spatial arbitrage as "spread minus estimated transport cost" with explicit caveats. Show "best market" only as a ranking of current and forecast net price, not as advice. Anomaly alerts based on robust z-scores are reliable and cheap.

### Cited Findings
- Indian food markets across states are imperfectly integrated. Unexploited arbitrage gains persist even after accounting for transport costs, and information frictions contribute to this (World Bank, Boffa & Varela 2019) — [World Bank: Integration and Price Transmission in Key Food Commodity Markets in India](https://openknowledge.worldbank.org/entities/publication/60fe08d8-4be7-5db5-9c94-fdb7a2429556/full)
- Across 21 commodities and 60 Indian markets (monthly data), market pairs with better transport infrastructure and shorter distances were more integrated, with no robust evidence of rising integration (IMF 2020, summary-level) — [IMF: Agricultural Market Integration in India](https://bookstore.imf.org/books/agricultural-market-integration-in-india)
- In competitive markets, inter-market price differences should not exceed transport costs. Speed of convergence measures integration (Indian onion, AGMARKNET 2010–11) — [Testing market integration and the law of one price in Indian onions](https://www.researchgate.net/profile/Sendhil_Ramadas/publication/266261789_Testing_market_integration_and_convergence_to_the_law_of_one_price_in_Indian_onions/links/542ba3100cf27e39fa918ab9/Testing-market-integration-and-convergence-to-the-law-of-one-price-in-Indian-onions.pdf)
- Distance between wheat markets maps onto transaction-cost thresholds, so threshold models fit these markets — [CUP wheat market integration](https://kr.cup.edu.in/handle/32116/4443)
- Interval widths and coverage must be validated by backtest, and coverage degrades at longer horizons — [skforecast conformal guide](https://skforecast.org/latest/user_guides/probabilistic-forecasting-conformal-prediction)
- Extreme short-term volatility (prices doubling within a week) is a recognised forecasting problem in isolated vegetable markets. Point forecasts are fragile in these episodes (non-Indian) — [arXiv 2606.29248](https://arxiv.org/pdf/2606.29248)

### Inferences
Reliability tiers for the UI:
- **Show confidently (descriptive or derived from data)**:
  - Current price vs seasonal norm.
  - Arrivals vs norm.
  - The DSPI quadrant.
  - 4- and 13-week momentum.
  - Rolling volatility: the std of weekly log returns over 8 weeks, annualised or shown as a ±% band.
  - Price spread between markets today.
  - Anomaly alerts: robust z-score of the weekly change using median/MAD, flagged when |z| > 3, or an arrivals collapse below the 10th percentile.
- **Show with ranges and an accuracy badge**:
  - 1–4 week price forecasts as a median and an 80% band.
  - Show the backtest MASE and coverage next to each forecast.
  - Hide the forecast, or grey it out, if MASE ≥ 1 for that series, meaning the model does not beat seasonal-naive.
  - Show a trend direction (up, flat or down) with its backtested directional accuracy.
- **Show as decision support with caveats**:
  - **Spatial arbitrage**: `net_spread = P_dest − P_src − transport_cost(distance, ₹/qtl/km) − mandi fees/commission`.
  - Flag it only if net_spread exceeds a threshold, such as > 5% or > 1 std of historical spread.
  - Use forecast prices at the arrival date (t + travel days), not today's prices.
  - The transport cost should be a user-editable parameter.
  - **Best market to sell or buy**: rank markets within a radius by expected net realisation, meaning the forecast median minus transport and fees. Also show downside, using the 10th-percentile quantile.
- **Avoid or label as experimental**:
  - 30-day daily-resolution point forecasts for tomato and onion.
  - Any "demand quantity" forecast.
  - Arbitrage claims during policy shocks (export bans, stock limits).
- Use 7–30 days as 1–4 weekly steps. I found no evidence that daily-resolution 30-day forecasts are reliable for perishables.

### Gaps
- I found no published Indian estimates of per-km transport cost for each commodity. Students will need to assume a cost (for example, from freight quotes) and expose it as a parameter.
- I found no studies that evaluate a "best market" recommender against realised outcomes.

---

## 6. Model-ops at student scale

### Takeaway
Train one global LightGBM per horizon (or with the horizon as a feature) across all commodity-market series, with categorical IDs. Keep per-series SARIMA/ETS and seasonal-naive as baselines and as fallbacks. Retrain weekly or monthly, version the models with joblib plus a metadata JSON, and serve them from FastAPI. Prevent leakage with shifted features and time-ordered splits. Handle cold start by falling back to the global model or a hierarchy (state/national median).

### Cited Findings
- M5 winners trained global, cross-learning gradient-boosting models over many related series. The winning approach used recursive store-level LightGBM models. Transfer learning on those models achieved similar accuracy with about 25% less training time — [Medium M5 learnings](https://medium.com/analytics-vidhya/predicting-the-future-with-learnings-from-the-m5-competition-d54e84ca3d0d); [KU Leuven Lirias](https://lirias.kuleuven.be/retrieve/636194); [M5 results](https://pure.unic.ac.cy/en/publications/m5-accuracy-competition-results-findings-and-conclusions/)
- A 2026 arXiv paper reports that global tree forecasters can perform poorly when evaluated on hierarchical aggregates (monthly totals). This suggests evaluating at the level you serve — [arXiv 2609.27912](https://arxiv.org/pdf/2609.27912)
- Leakage rules for intervals:
  - Calibration residuals must come from out-of-sample backtests and never from the test set.
  - Splits must be chronological: train, then calibration, then test.

  — [skforecast conformal guide](https://skforecast.org/latest/user_guides/probabilistic-forecasting-conformal-prediction)
- No future observations may be used in constructing a forecast — [FPP3 §5.10](https://otexts.com/fpp3/tscv.html)
- IBM Research proposed context-based model selection for Indian crop prices that uses trend and data-quality features. This supports choosing per series between the global model and simpler fallbacks according to data quality — [IBM Research](https://research.ibm.com/publications/towards-context-based-model-selection-for-improved-crop-price-forecasting); a related framework analyses time-series data quality for crop price forecasting in emerging economies — [HUTECH library record](https://lib.hutech.edu.vn/chi-tiet?id=165168)

### Inferences
- **Global vs per-series**:
  - Use one global LightGBM (CPU training takes seconds to minutes on a few hundred thousand weekly rows). It shares strength across markets and handles short histories.
  - Use per-series statsmodels SARIMA/ETS only for the top 10–20 commodity-market pairs as baselines, because fitting them is slow at scale.
  - Prophet is optional, one model per series, and useful for its explainable seasonality and holiday components.
- **Multi-horizon strategy**: train a direct model for each horizon (h = 1, 2, 4), each with quantiles 0.1, 0.5 and 0.9. That makes 9 small LightGBM models in total. skforecast's `ForecasterDirect` and Darts provide this pattern, but plain pandas plus LightGBM is enough.
- **Leakage checklist**:
  - Build all rolling features with `groupby(series).shift(1).rolling(...)`.
  - Fit any scaler or encoder on the training period only.
  - Compute the seasonal norm from prior years only.
  - Nearby-market features must be lagged too.
  - Do not use the target-week's arrivals; they are unknown at forecast time unless forecast separately.
  - Never shuffle in `train_test_split`; use time-based splits.
- **Retraining cadence**:
  - Ingest Agmarknet data daily or weekly.
  - Refresh predictions weekly by re-running the existing model on new features.
  - Retrain LightGBM monthly, and statistical models weekly (they are cheap).
  - Monitor rolling MAE against seasonal-naive. Retrain early if MASE exceeds 1 for more than 4 weeks.
- **Storage**:
  - Save `models/{model_name}/{version}/model.joblib` (or the LightGBM native `.txt`) plus `meta.json`, covering the training date range, features, backtest metrics and coverage.
  - Keep features and forecasts in SQLite or Parquet.
  - At startup, FastAPI loads the latest version.
  - Endpoints:
    - `/forecast?commodity&market&h` returns the median and the p10/p90 band.
    - `/signals` returns momentum, volatility, DSPI and anomalies.
    - `/arbitrage?commodity&origin&radius&cost_per_km`.
    - `/best-market`.
  - Precompute nightly and serve from the database to keep latency low.
- **Cold start (sparse history)**:
  - With fewer than 26 weeks of history, rely on the global model, since the categorical ID is unseen or rare and the model leans on commodity, state and calendar features.
  - Alternatively, use hierarchical fallbacks: state median price × the series' historical ratio to the state, then the national seasonal profile, then the last observed value.
  - Flag low-confidence forecasts in the UI and widen the intervals by using conformal residuals from similar series.
- **Compute**: all of the above runs on a CPU laptop. LSTM/GRU via PyTorch CPU on weekly data is feasible but optional. It would add a dependency beyond the stated stack.

### Gaps
- I found no Indian-mandi-specific study comparing global and per-series models, or evaluating retraining cadence. The recommendations rely on M5 and general practice.
- I did not fetch the LightGBM quantile-objective documentation or the Prophet holidays documentation. These are standard features (`objective="quantile", alpha=...`; Prophet `holidays` dataframe), but they are not cited here.
