"""
Phase 3: weekly price forecasts with an honest promotion gate.

Model: one global HistGradientBoosting quantile regressor per (horizon, quantile),
horizons 1/2/4 weeks, quantiles 0.1/0.5/0.9 -> 9 small models. Target is the
log price ratio log(p[t+h] / p[t]), so one model serves all commodities and
price levels. Features use only data at or before the origin week t.

Evaluation: rolling-origin backtest over the most recent weeks (origins every
4 weeks, each model trained only on samples whose target week is <= origin).
Baselines: naive (p[t]), seasonal naive (p[t+h-52]) and 4-week moving average.
"relative MAE" = model MAE / MAE of the strongest baseline for that series on
the same points (< 1 means the model beats every baseline).

The gate thresholds are engineering targets from the implementation plan, not
standards from the literature.
"""
import json
import logging
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from services.mandi.config import COMMODITIES, scoped_commodities, state_key
from services.mandi.normalize import utc_now_iso

log = logging.getLogger("alip.mandi.forecast")

HORIZONS = (1, 2, 4)
QUANTILES = (0.1, 0.5, 0.9)
LAGS = (1, 2, 3, 4, 8, 13, 26, 52)
MIN_SERIES_WEEKS = 26          # shorter series never get a forecast
MAX_MARKETS_PER_COMMODITY = 25 # keeps the training panel laptop-sized
HISTORY_WEEKS = 6 * 52
BACKTEST_STEP_WEEKS = 4
MIN_TRAIN_SAMPLES = 200
MIN_SERIES_POINTS = 3          # backtest points needed to judge one series

GATE = {
    "share_beating_baseline": 0.60,   # at h=1 and h=2
    "coverage_low": 0.70,             # nominal 80% interval (P10-P90)
    "coverage_high": 0.90,
    "directional_accuracy_h1": 0.55,
}

MODEL_NAME = "demand_forecast"
MODEL_ROOT = Path(__file__).resolve().parents[2] / "data" / "models" / MODEL_NAME

COMMODITY_CODES = {cid: i for i, cid in enumerate(COMMODITIES)}
LEVEL_CODES = {"national": 0, "state": 1, "market": 2}
FEATURES = (
    [f"lag_{k}" for k in LAGS]
    + ["roll_mean_4", "roll_mean_13", "vol_8", "vol_26", "history_weeks",
       "woy_sin", "woy_cos", "parent_spread", "arrivals_ratio",
       "commodity", "level", "season"]
)
CATEGORICAL = [FEATURES.index(name) for name in ("commodity", "level", "season")]


# ─── Panel of weekly series ────────────────────────────────
@dataclass
class Series:
    commodity: str
    level: str
    scope_key: str
    scope_name: str
    start: date                     # Monday of the first week
    prices: np.ndarray              # weekly grid, NaN where no data
    parent: "Series" = None
    arrivals: dict = field(default_factory=dict)  # week index -> rolling arrivals ratio

    @property
    def key(self) -> str:
        return f"{self.commodity}|{self.level}|{self.scope_key}"

    def week(self, idx: int) -> date:
        return self.start + timedelta(weeks=int(idx))

    def index_of(self, day: date) -> int:
        return (day - self.start).days // 7


def _grid(points: list[dict], start: date, end: date) -> np.ndarray:
    grid = np.full((end - start).days // 7 + 1, np.nan)
    for p in points:
        grid[(date.fromisoformat(p["week_start"]) - start).days // 7] = p["price"]
    return grid


def _median_by_week(points):
    weeks = defaultdict(list)
    for p in points:
        weeks[p["week_start"]].append(p["price"])
    return [{"week_start": w, "price": statistics.median(v)} for w, v in sorted(weeks.items())]


def _rolling_arrivals(arrivals_weekly: list[dict], start: date) -> dict:
    """Week index -> this week's arrivals / median of the previous 8 weeks (no look-ahead)."""
    out, history = {}, []
    for a in arrivals_weekly:
        day = date.fromisoformat(a["week_start"])
        prior = [h["tonnes_per_day"] for h in history if (day - date.fromisoformat(h["week_start"])).days <= 56]
        if len(prior) >= 4 and statistics.median(prior) > 0:
            out[(day - start).days // 7] = a["tonnes_per_day"] / statistics.median(prior)
        history.append(a)
    return out


def build_panel(commodity: str, market_weeks: list[dict], arrivals_weekly: list[dict],
                for_training: bool = True) -> list[Series]:
    """
    National, state and market series for one commodity. For training only the
    best-covered markets are kept (laptop-sized panel); for serving every market
    is included so short histories get an explicit "insufficient" answer.
    """
    if not market_weeks:
        return []
    start = min(date.fromisoformat(p["week_start"]) for p in market_weeks)
    end = max(date.fromisoformat(p["week_start"]) for p in market_weeks)
    arrivals = _rolling_arrivals(arrivals_weekly, start)

    national = Series(commodity, "national", "india", "India", start,
                      _grid(_median_by_week(market_weeks), start, end), arrivals=arrivals)
    panel = [national]

    by_state, by_market = defaultdict(list), defaultdict(list)
    for p in market_weeks:
        by_state[state_key(p["state"])].append(p)
        by_market[p["market_key"]].append(p)
    states = {}
    for skey, points in by_state.items():
        s = Series(commodity, "state", skey, points[-1]["state"], start,
                   _grid(_median_by_week(points), start, end), parent=national, arrivals=arrivals)
        states[skey] = s
        panel.append(s)

    covered = sorted(by_market.items(), key=lambda kv: -len(kv[1]))
    if for_training:
        covered = [kv for kv in covered if len(kv[1]) >= MIN_SERIES_WEEKS][:MAX_MARKETS_PER_COMMODITY]
    for market_key, points in covered:
        parent = states.get(state_key(points[0]["state"]), national)
        panel.append(Series(commodity, "market", market_key, market_key.split("|")[-1].title(), start,
                            _grid(points, start, end), parent=parent, arrivals=arrivals))
    return panel


# ─── Features (data <= origin only) ────────────────────────
def _season(month: int) -> int:
    return 0 if 6 <= month <= 10 else 1 if month in (11, 12, 1, 2, 3) else 2  # kharif / rabi / zaid


def features_at(series: Series, t: int, h: int):
    """Feature vector for origin index t and horizon h, or None if p[t] is missing."""
    grid = series.prices
    p = grid[t]
    if not np.isfinite(p) or p <= 0:
        return None
    row = []
    for k in LAGS:
        past = grid[t - k] if t - k >= 0 else np.nan
        row.append(math.log(past / p) if np.isfinite(past) and past > 0 else np.nan)

    window4 = grid[max(0, t - 3):t + 1]
    window13 = grid[max(0, t - 12):t + 1]
    row.append(math.log(np.nanmean(window4) / p))
    row.append(math.log(np.nanmean(window13) / p))
    for span in (8, 26):
        seg = grid[max(0, t - span):t + 1]
        valid = seg[np.isfinite(seg)]
        returns = np.diff(np.log(valid)) if len(valid) >= 3 else []
        row.append(float(np.std(returns)) if len(returns) >= 2 else np.nan)
    row.append(float(min(np.isfinite(grid[:t + 1]).sum(), 156)))

    target = series.week(t + h)
    angle = 2 * math.pi * target.isocalendar()[1] / 52.0
    row += [math.sin(angle), math.cos(angle)]

    parent_p = series.parent.prices[t] if series.parent is not None else np.nan
    row.append(math.log(p / parent_p) if np.isfinite(parent_p) and parent_p > 0 else np.nan)
    row.append(series.arrivals.get(t, np.nan))
    row += [COMMODITY_CODES[series.commodity], LEVEL_CODES[series.level], _season(target.month)]
    return row


@dataclass
class Samples:
    X: np.ndarray
    y: np.ndarray
    series: list      # Series per row
    origin: np.ndarray  # origin index per row
    origin_week: list
    target_week: list


def make_samples(panel: list[Series], h: int) -> Samples:
    X, y, ser, origin, ow, tw = [], [], [], [], [], []
    for s in panel:
        grid = s.prices
        for t in range(len(grid) - h):
            target = grid[t + h]
            if not np.isfinite(target) or target <= 0:
                continue
            row = features_at(s, t, h)
            if row is None:
                continue
            X.append(row)
            y.append(math.log(target / grid[t]))
            ser.append(s)
            origin.append(t)
            ow.append(s.week(t).isoformat())
            tw.append(s.week(t + h).isoformat())
    return Samples(np.array(X, dtype=float).reshape(-1, len(FEATURES)), np.array(y), ser,
                   np.array(origin, dtype=int), ow, tw)


def _new_model(q: float) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="quantile", quantile=q, max_iter=150, learning_rate=0.05,
        max_leaf_nodes=15, min_samples_leaf=20, categorical_features=CATEGORICAL,
        random_state=42,
    )


def fit_quantiles(X: np.ndarray, y: np.ndarray) -> dict:
    return {q: _new_model(q).fit(X, y) for q in QUANTILES}


def predict_prices(models: dict, X: np.ndarray, base_prices: np.ndarray, widen: float = 0.0) -> np.ndarray:
    """
    (n, 3) price quantiles, sorted so P10 <= P50 <= P90 always holds.
    `widen` is the conformal correction in log space added to both interval ends.
    """
    raw = np.sort(np.column_stack([models[q].predict(X) for q in QUANTILES]), axis=1)
    raw[:, 0] = np.minimum(raw[:, 0] - widen, raw[:, 1])
    raw[:, 2] = np.maximum(raw[:, 2] + widen, raw[:, 1])
    return base_prices[:, None] * np.exp(raw)


# ─── Conformal calibration of the P10-P90 band ─────────────
NOMINAL_COVERAGE = QUANTILES[2] - QUANTILES[0]   # 0.8
MIN_CALIBRATION_SCORES = 20


def conformity_scores(p10, p90, actual) -> np.ndarray:
    """CQR score in log space: how far the outcome fell outside the raw band (negative = inside)."""
    return np.maximum(np.log(p10) - np.log(actual), np.log(actual) - np.log(p90))


def conformal_widen(scores) -> float:
    """
    Split-conformal correction (Romano et al., conformalized quantile regression):
    the ceil((n+1)(1-alpha))/n empirical quantile of past scores. Zero until enough scores exist.
    """
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    if n < MIN_CALIBRATION_SCORES:
        return 0.0
    level = min(1.0, math.ceil((n + 1) * NOMINAL_COVERAGE) / n)
    return float(np.quantile(scores, level))


# ─── Baselines ─────────────────────────────────────────────
def baselines(series: Series, t: int, h: int) -> dict:
    grid = series.prices
    seasonal = grid[t + h - 52] if t + h - 52 >= 0 else np.nan
    window = grid[max(0, t - 3):t + 1]
    return {
        "naive": grid[t],
        "seasonal_naive": seasonal if np.isfinite(seasonal) else np.nan,
        "moving_avg_4": float(np.nanmean(window)),
    }


# ─── Backtest ──────────────────────────────────────────────
def _metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    actual = np.array([r["actual"] for r in rows])
    p50 = np.array([r["p50"] for r in rows])
    base = np.array([r["origin_price"] for r in rows])
    err = p50 - actual
    out = {
        "n": len(rows),
        "mae": round(float(np.mean(np.abs(err))), 2),
        "rmse": round(float(np.sqrt(np.mean(err ** 2))), 2),
        "mape": round(float(np.mean(np.abs(err) / actual)), 4),
    }
    # Coverage is judged only where a conformal correction from earlier origins existed.
    calibrated = [r for r in rows if r.get("calibrated", True)]
    out["coverage_points"] = len(calibrated)
    out["coverage_80"] = (
        round(float(np.mean([(r["p10"] <= r["actual"] <= r["p90"]) for r in calibrated])), 4)
        if calibrated else None)
    moved = actual != base
    if moved.any():
        out["directional_accuracy"] = round(float(np.mean(np.sign(p50[moved] - base[moved]) == np.sign(actual[moved] - base[moved]))), 4)
    for name in ("naive", "seasonal_naive", "moving_avg_4"):
        pts = [r for r in rows if np.isfinite(r[name])]
        if pts:
            base_mae = float(np.mean([abs(r[name] - r["actual"]) for r in pts]))
            model_mae = float(np.mean([abs(r["p50"] - r["actual"]) for r in pts]))
            out[f"mae_{name}"] = round(base_mae, 2)
            out[f"rel_mae_{name}"] = round(model_mae / base_mae, 4) if base_mae > 0 else None
    # Compare against the strongest baseline, not just seasonal naive: on a
    # random-walk series last year's price is a weak guess, and beating it alone
    # would promote a model that has learnt nothing.
    candidates = {
        name: out[f"rel_mae_{name}"] for name in ("naive", "seasonal_naive", "moving_avg_4")
        if out.get(f"rel_mae_{name}") is not None
        and sum(np.isfinite(r[name]) for r in rows) >= max(MIN_SERIES_POINTS, len(rows) // 2)
    }
    if candidates:
        out["baseline"] = max(candidates, key=candidates.get)  # highest ratio = hardest to beat
        out["rel_mae"] = candidates[out["baseline"]]
    else:
        out["baseline"], out["rel_mae"] = None, None
    return out


def _policy(rows_h1: list[dict]) -> dict:
    """Sell-now vs hold-one-week: hold when P50 > today's price."""
    if not rows_h1:
        return {}
    follow = [(r["actual"] if r["p50"] > r["origin_price"] else r["origin_price"]) / r["origin_price"] - 1 for r in rows_h1]
    hold = [r["actual"] / r["origin_price"] - 1 for r in rows_h1]
    return {
        "follow_model_return": round(float(np.mean(follow)), 5),
        "always_hold_return": round(float(np.mean(hold)), 5),
        "always_sell_return": 0.0,
    }


def backtest(panel: list[Series], holdout_weeks: int = 52, step: int = BACKTEST_STEP_WEEKS,
             return_rows: bool = False) -> dict:
    if not panel:
        return {"origins": 0, "by_horizon": {}, "by_series": {}}
    last = max(s.week(len(s.prices) - 1) for s in panel)
    span_weeks = max(len(s.prices) for s in panel)
    holdout_weeks = min(holdout_weeks, span_weeks // 3)
    origins = [(last - timedelta(weeks=w)).isoformat() for w in range(holdout_weeks, 0, -step)]

    rows_by_h = {h: [] for h in HORIZONS}
    scores_by_h = {h: [] for h in HORIZONS}
    used_origins = set()
    for h in HORIZONS:
        samples = make_samples(panel, h)
        if not len(samples.y):
            continue
        target_weeks = np.array(samples.target_week)
        origin_weeks = np.array(samples.origin_week)
        for origin in origins:
            train = target_weeks <= origin          # only outcomes known at the origin
            test = origin_weeks == origin
            if train.sum() < MIN_TRAIN_SAMPLES or not test.any():
                continue
            used_origins.add(origin)
            models = fit_quantiles(samples.X[train], samples.y[train])
            idx = np.flatnonzero(test)
            base_prices = np.array([samples.series[i].prices[samples.origin[i]] for i in idx])
            # Interval correction learnt only from earlier origins whose outcomes are known.
            known = [sc for (target_week, sc) in scores_by_h[h] if target_week <= origin]
            widen = conformal_widen(known)
            raw = predict_prices(models, samples.X[idx], base_prices)
            preds = predict_prices(models, samples.X[idx], base_prices, widen)
            for j, i in enumerate(idx):
                s, t = samples.series[i], samples.origin[i]
                actual = s.prices[t + h]
                scores_by_h[h].append((s.week(t + h).isoformat(),
                                       float(conformity_scores(raw[j, 0], raw[j, 2], actual))))
                rows_by_h[h].append({
                    "series": s.key, "origin_week": origin, "origin_price": s.prices[t],
                    "actual": actual, "p10": preds[j, 0], "p50": preds[j, 1], "p90": preds[j, 2],
                    "calibrated": len(known) >= MIN_CALIBRATION_SCORES,
                    **baselines(s, t, h),
                })

    by_horizon, by_series = {}, defaultdict(dict)
    for h, rows in rows_by_h.items():
        overall = _metrics(rows)
        per_series = defaultdict(list)
        for r in rows:
            per_series[r["series"]].append(r)
        judged = {k: _metrics(v) for k, v in per_series.items() if len(v) >= MIN_SERIES_POINTS}
        for key, m in judged.items():
            by_series[key][f"h{h}"] = m
        beating = [m for m in judged.values() if m.get("rel_mae") is not None]
        overall["series_judged"] = len(beating)
        overall["share_beating_baseline"] = (
            round(sum(m["rel_mae"] < 1 for m in beating) / len(beating), 4) if beating else None)
        if h == 1:
            overall["policy"] = _policy(rows)
        by_horizon[f"h{h}"] = overall
    result = {"origins": len(used_origins), "holdout_weeks": holdout_weeks,
              "by_horizon": by_horizon, "by_series": dict(by_series),
              # correction for the final model: all out-of-sample scores from the backtest
              "conformal_widen": {f"h{h}": round(conformal_widen([sc for _, sc in scores_by_h[h]]), 5)
                                  for h in HORIZONS}}
    if return_rows:
        result["rows"] = rows_by_h
    return result


def evaluate_gate(report: dict) -> dict:
    """Promotion decision with the reason for every failed check."""
    bh = report.get("by_horizon") or {}
    reasons = []
    for h in ("h1", "h2"):
        share = (bh.get(h) or {}).get("share_beating_baseline")
        if share is None or share < GATE["share_beating_baseline"]:
            reasons.append(f"{h}: {share} of series beat the baseline (need >= {GATE['share_beating_baseline']})")
    for h in ("h1", "h2", "h4"):
        cov = (bh.get(h) or {}).get("coverage_80")
        if cov is None or not GATE["coverage_low"] <= cov <= GATE["coverage_high"]:
            reasons.append(f"{h}: P10-P90 coverage {cov} outside {GATE['coverage_low']}-{GATE['coverage_high']}")
    da = (bh.get("h1") or {}).get("directional_accuracy")
    if da is None or da <= GATE["directional_accuracy_h1"]:
        reasons.append(f"h1: directional accuracy {da} (need > {GATE['directional_accuracy_h1']})")
    policy = (bh.get("h1") or {}).get("policy") or {}
    if not policy or policy["follow_model_return"] < policy["always_hold_return"]:
        reasons.append(f"h1: following the model does not beat always-hold ({policy or 'no data'})")
    return {"promoted": not reasons, "reasons": reasons, "thresholds": GATE}


# ─── Training, registry and serving ────────────────────────
async def load_panels(store, commodities=None, today: date = None, for_training: bool = True) -> list[Series]:
    from services.mandi.insights import weekly_arrivals

    today = today or date.today()
    date_from = (today - timedelta(weeks=HISTORY_WEEKS)).isoformat()
    panel = []
    for cid in commodities or scoped_commodities():
        market_weeks = await store.weekly_market_medians(cid, date_from)
        arrivals = weekly_arrivals(await store.find_arrivals(cid, date_from=date_from))
        panel.extend(build_panel(cid, market_weeks, arrivals, for_training))
    return panel


def _version() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


async def train_and_evaluate(store, commodities=None, today: date = None, model_root: Path = MODEL_ROOT) -> dict:
    """Backtest, fit final models on all data, save the version, promote only if the gate passes."""
    panel = await load_panels(store, commodities, today)
    eligible = [s for s in panel if np.isfinite(s.prices).sum() >= MIN_SERIES_WEEKS]
    version = _version()
    result = {"version": version, "model": MODEL_NAME, "created_at": utc_now_iso(),
              "series_total": len(panel), "series_eligible": len(eligible)}

    report = backtest(eligible)
    gate = evaluate_gate(report)
    result.update({"backtest": {k: v for k, v in report.items() if k != "by_series"}, "gate": gate})

    final, trained = {}, 0
    for h in HORIZONS:
        samples = make_samples(eligible, h)
        if len(samples.y) >= MIN_TRAIN_SAMPLES:
            final[h] = fit_quantiles(samples.X, samples.y)
            trained = max(trained, len(samples.y))
    result["train_samples"] = trained
    result["trained"] = len(final) == len(HORIZONS)
    result["promoted"] = bool(gate["promoted"] and result["trained"])
    if not result["trained"]:
        gate["reasons"].insert(0, f"not enough training samples (need {MIN_TRAIN_SAMPLES} per horizon)")

    if result["trained"]:
        folder = model_root / version
        folder.mkdir(parents=True, exist_ok=True)
        joblib.dump(final, folder / "models.joblib")
        meta = {**result, "features": FEATURES, "horizons": HORIZONS, "quantiles": QUANTILES,
                "series_metrics": report["by_series"]}
        (folder / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        result["path"] = str(folder)

    registry = await store.get_master("model_registry")
    registry.append({"_id": version, **{k: result[k] for k in (
        "model", "created_at", "promoted", "trained", "series_eligible", "train_samples")},
        "gate_reasons": gate["reasons"], "summary": result["backtest"]["by_horizon"]})
    await store.replace_master("model_registry", registry[-50:])
    log.info("forecast model %s trained=%s promoted=%s", version, result["trained"], result["promoted"])
    return result


async def promoted_version(store):
    registry = await store.get_master("model_registry")
    promoted = [r for r in registry if r.get("promoted")]
    return max(promoted, key=lambda r: r["_id"]) if promoted else None


def _confidence(metrics: dict, weeks: int, stale: bool):
    if weeks < MIN_SERIES_WEEKS:
        return "insufficient", f"only {weeks} weeks of history (need {MIN_SERIES_WEEKS})"
    if stale:
        return "insufficient", "no recent price for this series"
    h1 = (metrics or {}).get("h1")
    if not h1 or h1.get("rel_mae") is None:
        return "insufficient", "not enough backtest points for this series"
    if h1["rel_mae"] >= 1:
        return "insufficient", f"does not beat {h1['baseline']} (relative MAE {h1['rel_mae']})"
    covered = GATE["coverage_low"] <= h1.get("coverage_80", 0) <= GATE["coverage_high"]
    return ("high" if h1["rel_mae"] < 0.8 and covered else "medium"), None


async def run_forecasts(store, commodities=None, today: date = None, model_root: Path = MODEL_ROOT) -> dict:
    """Predict P10/P50/P90 at 1/2/4 weeks for every series; hide series that failed the backtest."""
    commodities = commodities or scoped_commodities()
    current = await promoted_version(store)
    models, meta = None, {}
    if current and (model_root / current["_id"] / "models.joblib").exists():
        models = joblib.load(model_root / current["_id"] / "models.joblib")
        meta = json.loads((model_root / current["_id"] / "meta.json").read_text(encoding="utf-8"))
    series_metrics = meta.get("series_metrics", {})
    widen = (meta.get("backtest") or {}).get("conformal_widen") or {}
    computed_at = utc_now_iso()
    written = defaultdict(int)

    panel = await load_panels(store, commodities, today, for_training=False)
    by_commodity = defaultdict(list)
    for s in panel:
        by_commodity[s.commodity].append(s)

    for cid in commodities:
        docs = []
        series_list = by_commodity.get(cid, [])
        latest = max((s.week(len(s.prices) - 1) for s in series_list), default=None)
        for s in series_list:
            finite = np.flatnonzero(np.isfinite(s.prices))
            if not len(finite):
                continue
            t = int(finite[-1])
            weeks = int(len(finite))
            stale = (latest - s.week(t)).days > 14
            confidence, reason = _confidence(series_metrics.get(s.key), weeks, stale)
            if models is None:
                confidence, reason = "insufficient", "no forecast model has passed the backtest gate yet"
            doc = {
                "_id": s.key, "commodity": cid, "commodity_name": COMMODITIES[cid]["name"],
                "level": s.level, "scope_key": s.scope_key, "scope_name": s.scope_name,
                "origin_week": s.week(t).isoformat(), "origin_price": round(float(s.prices[t]), 2),
                "price_unit": "Rs/quintal", "weeks_of_history": weeks,
                "confidence": confidence, "reason": reason,
                "model_version": current["_id"] if current else None,
                "backtest": series_metrics.get(s.key), "computed_at": computed_at, "horizons": [],
            }
            if confidence != "insufficient":
                for h in HORIZONS:
                    row = features_at(s, t, h)
                    q = predict_prices(models[h], np.array([row], dtype=float), np.array([s.prices[t]]),
                                       widen.get(f"h{h}", 0.0))[0]
                    doc["horizons"].append({
                        "h_weeks": h, "target_week": s.week(t + h).isoformat(),
                        "p10": round(float(q[0]), 2), "p50": round(float(q[1]), 2), "p90": round(float(q[2]), 2),
                    })
            docs.append(doc)
            written[confidence] += 1
        await store.replace_scoped("forecasts", cid, docs)
    log.info("forecasts written: %s", dict(written))
    return {"model_version": current["_id"] if current else None, "by_confidence": dict(written)}
