"""Train and evaluate the stock model using time-ordered, point-in-time data."""

import os
import warnings

import joblib
import numpy as np
import pandas as pd
import psycopg2
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

from model_bundle import CalibratedProbabilityModel
from prediction_features import (
    FEATURE_COLUMNS,
    LEGACY_FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    add_barrier_labels,
    build_features_for_stock,
)

try:
    from config import DB_CONN_STR
    DB_CONFIG = DB_CONN_STR
except ImportError:
    DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5435"

MODEL_FILE = os.getenv("MODEL_PATH", "models/stock_ai_brain_v3.pkl")
HOLDOUT_SESSIONS = 252
MIN_HOLDOUT_SESSIONS = 126
CALIBRATION_FRACTION = 0.12
# Keep the default below the container's memory-pressure threshold.  The
# candidate still has broad cross-sectional coverage, and deployments with
# more memory can raise this without changing code.
MAX_TRAINING_STOCKS = max(100, int(os.getenv("MAX_TRAINING_STOCKS", "300")))
TRAINING_START_DATE = "2021-01-01"

warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from xgboost import XGBClassifier
    MODEL_TYPE = "XGBoost"
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier
    MODEL_TYPE = "GradientBoosting"


def get_db_connection():
    try:
        return psycopg2.connect(DB_CONFIG)
    except Exception:
        return None


def fetch_training_data(logger=None):
    """Stream one stock at a time and return a compact labeled training frame.

    The stock universe is selected by turnover before the final holdout window,
    so the holdout itself does not determine which securities enter the sample.
    A 90-day reporting lag is applied because the database stores fiscal period,
    not the actual public announcement timestamp.
    """
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("Database connection failed")

    universe_query = f"""
        WITH recent_dates AS (
            SELECT DISTINCT trade_date
            FROM daily_prices
            WHERE trade_date >= DATE '2021-01-01'
            ORDER BY trade_date DESC
            LIMIT {HOLDOUT_SESSIONS}
        ), holdout_start AS (
            SELECT MIN(trade_date) AS trade_date FROM recent_dates
        ), liquid_universe AS (
            SELECT p.sc_code
            FROM daily_prices p
            CROSS JOIN holdout_start h
            WHERE p.trade_date >= h.trade_date - INTERVAL '180 days'
              AND p.trade_date < h.trade_date
            GROUP BY p.sc_code
            HAVING COUNT(*) >= 60 AND AVG(p.volume) > 5000
            ORDER BY AVG(p.close * p.volume) DESC NULLS LAST, p.sc_code
            LIMIT {MAX_TRAINING_STOCKS}
        )
        SELECT sc_code FROM liquid_universe ORDER BY sc_code
    """
    stock_query = """
        SELECT
            p.sc_code, p.trade_date, p.open, p.high, p.low, p.close, p.volume,
            m.india_vix, m.usd_inr, m.nifty50_close, m.crude_oil,
            m.us_market_close, m.usd_inr_available, m.crude_oil_available,
            m.us_market_close_available, f.eps, f.eps_ttm, f.financial_period
        FROM daily_prices p
        LEFT JOIN macro_indicators m ON m.trade_date = p.trade_date
        LEFT JOIN LATERAL (
            SELECT
                CASE WHEN COUNT(*) = 4 THEN SUM(recent.eps) END AS eps_ttm,
                MAX(recent.eps) FILTER (WHERE recent.quarter_rank = 1) AS eps,
                MAX(recent.period) AS financial_period
            FROM (
                SELECT q.eps, q.period,
                       ROW_NUMBER() OVER (ORDER BY q.period DESC) AS quarter_rank
                FROM quarterly_financials q
                WHERE q.sc_code = p.sc_code
                  AND q.period <= p.trade_date - INTERVAL '90 days'
                  AND q.eps IS NOT NULL
                ORDER BY q.period DESC
                LIMIT 4
            ) recent
        ) f ON TRUE
        WHERE p.sc_code = %s AND p.trade_date >= DATE '2020-01-01'
        ORDER BY p.trade_date
    """
    raw_columns = [
        "sc_code", "trade_date", "open", "high", "low", "close", "volume",
        "india_vix", "usd_inr", "nifty50_close", "crude_oil", "us_market_close",
        "usd_inr_available", "crude_oil_available", "us_market_close_available",
        "eps", "eps_ttm", "financial_period",
    ]
    training_feature_columns = list(dict.fromkeys(FEATURE_COLUMNS + LEGACY_FEATURE_COLUMNS))
    compact_columns = ["trade_date", "sc_code"] + training_feature_columns + ["target", "realized_return"]
    compact_frames = []

    def finish_stock(rows):
        if not rows:
            return
        raw_stock = pd.DataFrame(rows, columns=raw_columns)
        features = build_features_for_stock(raw_stock)
        if features.empty:
            return
        # Load 2020 for the long EMA warm-up, but train on the original
        # post-warm-up window to keep cross-validation memory bounded.
        features = features.loc[
            features["trade_date"] >= pd.Timestamp(TRAINING_START_DATE)
        ].copy()
        if features.empty:
            return
        features = features.reset_index(drop=True)
        labeled = add_barrier_labels(features, horizon=HORIZON_SESSIONS)
        labeled = labeled.dropna(subset=["target", "realized_return"])
        if labeled.empty:
            return
        compact = labeled[compact_columns].copy()
        for feature in training_feature_columns + ["realized_return"]:
            compact[feature] = pd.to_numeric(compact[feature], errors="coerce").astype("float32")
        compact["target"] = compact["target"].astype("uint8")
        compact["sc_code"] = compact["sc_code"].astype("int64")
        compact_frames.append(compact)

    try:
        if logger:
            logger.log("[1/6] Selecting the liquid universe and loading one stock at a time...")
        with conn.cursor() as cursor:
            cursor.execute(universe_query)
            stock_codes = [row[0] for row in cursor.fetchall()]

        for number, stock_code in enumerate(stock_codes, start=1):
            with conn.cursor() as cursor:
                cursor.execute(stock_query, (stock_code,))
                rows = cursor.fetchall()
            finish_stock(rows)
            if logger and number % 100 == 0:
                logger.log(f"   Processed {number}/{len(stock_codes)} securities.")

        if not compact_frames:
            return pd.DataFrame(columns=compact_columns)
        frame = pd.concat(compact_frames, ignore_index=True)
        return frame.sort_values(["trade_date", "sc_code"]).reset_index(drop=True)
    finally:
        conn.close()


def build_training_frame(raw_frame, logger=None):
    """Engineer features per stock, then attach complete forward outcomes."""
    if raw_frame is None or raw_frame.empty:
        return pd.DataFrame()

    feature_frames = []
    groups = raw_frame.groupby("sc_code", sort=False)
    for number, (_, stock_frame) in enumerate(groups, start=1):
        features = build_features_for_stock(stock_frame)
        if not features.empty:
            feature_frames.append(features)
        if logger and number % 250 == 0:
            logger.log(f"   Feature engineering: {number}/{groups.ngroups} securities")

    if not feature_frames:
        return pd.DataFrame()

    features = pd.concat(feature_frames, ignore_index=True)
    features = features.sort_values(["trade_date", "sc_code"]).reset_index(drop=True)
    labeled = add_barrier_labels(features, horizon=HORIZON_SESSIONS)
    labeled = labeled.dropna(subset=["target", "realized_return"])
    labeled["target"] = labeled["target"].astype(int)
    return labeled.sort_values(["trade_date", "sc_code"]).reset_index(drop=True)


def date_based_splits(frame, n_splits=3, gap=HORIZON_SESSIONS):
    """Create expanding train/validation folds on shared market dates."""
    dates = np.sort(pd.to_datetime(frame["trade_date"]).drop_duplicates().to_numpy())
    if len(dates) <= n_splits * 2 + gap:
        raise ValueError(f"Not enough distinct dates for {n_splits} walk-forward folds")

    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    date_values = pd.to_datetime(frame["trade_date"]).to_numpy()
    splits = []
    for train_date_idx, valid_date_idx in splitter.split(dates):
        train_dates = dates[train_date_idx]
        valid_dates = dates[valid_date_idx]
        train_rows = np.flatnonzero(np.isin(date_values, train_dates))
        valid_rows = np.flatnonzero(np.isin(date_values, valid_dates))
        if len(train_rows) and len(valid_rows):
            splits.append((train_rows, valid_rows))
    return splits


def make_model(params=None):
    """Build the common estimator used by tuning and the backtest."""
    params = dict(params or {})
    if MODEL_TYPE == "XGBoost":
        defaults = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "n_jobs": 1,
            "max_bin": 32,
            "random_state": 42,
        }
        defaults.update(params)
        return XGBClassifier(**defaults)

    defaults = {"random_state": 42, "n_estimators": 200, "max_depth": 3}
    defaults.update(params)
    return GradientBoostingClassifier(**defaults)


def parameter_search_space():
    if MODEL_TYPE == "XGBoost":
        return {
            "n_estimators": [60, 100, 140],
            "learning_rate": [0.03, 0.05, 0.1],
            "max_depth": [2, 3],
            "min_child_weight": [3, 5],
            "subsample": [0.7, 0.85, 1.0],
            "colsample_bytree": [0.7, 0.85, 1.0],
            "scale_pos_weight": [1.0, 2.0, 4.0],
        }
    return {
        "n_estimators": [100, 200, 300],
        "learning_rate": [0.03, 0.05, 0.1],
        "max_depth": [2, 3],
    }


def positive_probability(model, features):
    probabilities = model.predict_proba(features)
    classes = list(model.classes_)
    return probabilities[:, classes.index(1)]


def _split_development_and_holdout(frame):
    dates = np.sort(pd.to_datetime(frame["trade_date"]).drop_duplicates().to_numpy())
    holdout_size = min(HOLDOUT_SESSIONS, max(MIN_HOLDOUT_SESSIONS, int(np.ceil(len(dates) * 0.20))))
    if len(dates) <= holdout_size + 3 * HORIZON_SESSIONS + 100:
        raise ValueError("Not enough history for a purged development set and final holdout")

    holdout_start = len(dates) - holdout_size
    development_dates = dates[: holdout_start - HORIZON_SESSIONS]
    holdout_dates = dates[holdout_start:]
    date_values = pd.to_datetime(frame["trade_date"]).to_numpy()
    development = frame.loc[np.isin(date_values, development_dates)].reset_index(drop=True)
    holdout = frame.loc[np.isin(date_values, holdout_dates)].reset_index(drop=True)
    return development, holdout


def _calibration_partition(development):
    dates = np.sort(pd.to_datetime(development["trade_date"]).drop_duplicates().to_numpy())
    calibration_size = max(63, int(np.ceil(len(dates) * CALIBRATION_FRACTION)))
    calibration_start = len(dates) - calibration_size
    fit_end = calibration_start - HORIZON_SESSIONS
    if fit_end <= 250:
        raise ValueError("Not enough dates before the calibration window")

    fit_dates = dates[:fit_end]
    calibration_dates = dates[calibration_start:]
    date_values = pd.to_datetime(development["trade_date"]).to_numpy()
    fit_frame = development.loc[np.isin(date_values, fit_dates)].reset_index(drop=True)
    calibration_frame = development.loc[np.isin(date_values, calibration_dates)].reset_index(drop=True)
    return fit_frame, calibration_frame


def _metrics(labels, probabilities, threshold):
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predicted = probabilities >= threshold
    positive_rate = float(labels.mean()) if len(labels) else 0.0
    coverage = float(predicted.mean()) if len(predicted) else 0.0
    precision = float(precision_score(labels, predicted, zero_division=0))
    average_precision = float(average_precision_score(labels, probabilities)) if labels.sum() else 0.0
    brier = float(brier_score_loss(labels, probabilities))
    baseline_brier = positive_rate * (1.0 - positive_rate)
    return {
        "positive_rate": positive_rate,
        "signal_threshold": float(threshold),
        "signal_coverage": coverage,
        "signal_precision": precision,
        "average_precision": average_precision,
        "brier": brier,
        "baseline_brier": baseline_brier,
    }


def select_signal_threshold(labels, probabilities, minimum_precision, minimum_coverage):
    """Choose the broadest calibrated signal band that meets a precision goal."""
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    if len(labels) == 0:
        return None

    candidates = np.unique(np.quantile(probabilities, np.linspace(0.50, 1.0, 101)))
    eligible = []
    for threshold in candidates:
        selected = probabilities >= threshold
        coverage = float(selected.mean())
        if coverage < minimum_coverage or not selected.any():
            continue
        precision = float(labels[selected].mean())
        if precision >= minimum_precision:
            eligible.append((coverage, float(threshold)))
    if not eligible:
        return None
    # Highest coverage meeting the target; threshold breaks ties conservatively.
    eligible.sort(key=lambda item: (-item[0], -item[1]))
    return eligible[0][1]


def train_global_model(logger=None):
    """Tune, calibrate, evaluate on a final holdout, then save only if useful."""
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(message, flush=True)

    log(f"--- Starting date-aware training ({MODEL_TYPE}) ---")
    try:
        frame = fetch_training_data(logger=logger)
        log(f"[2/6] Prepared {len(frame):,} complete labeled stock/session rows.")
        if frame.empty:
            log("No complete labeled rows were available; model was not changed.")
            return {"promoted": False, "reason": "empty training data"}

        training_stock_count = int(frame["sc_code"].nunique())
        development, holdout = _split_development_and_holdout(frame)
        del frame
        feature_cols = FEATURE_COLUMNS
        legacy_only_columns = [column for column in LEGACY_FEATURE_COLUMNS if column not in feature_cols]

        # Score the active model before releasing its compatibility columns.
        y_holdout = holdout["target"].to_numpy(dtype=np.uint8, copy=True)
        holdout_returns = holdout["realized_return"].to_numpy(dtype=np.float32, copy=True)
        holdout_start = str(pd.to_datetime(holdout["trade_date"]).min().date())
        holdout_end = str(pd.to_datetime(holdout["trade_date"]).max().date())
        incumbent_path = os.getenv("LEGACY_MODEL_PATH", "stock_ai_brain_v2.pkl")
        incumbent_average_precision = None
        incumbent_net_return = None
        incumbent_coverage = 0.0
        incumbent_precision = 0.0
        round_trip_cost = float(os.getenv("MODEL_PROMOTION_COST_BPS", "30")) / 10000.0
        try:
            incumbent = joblib.load(incumbent_path)
            incumbent_scores = positive_probability(incumbent, holdout[LEGACY_FEATURE_COLUMNS])
            incumbent_average_precision = float(
                average_precision_score(y_holdout, incumbent_scores)
            )
            incumbent_selected = incumbent_scores >= 0.60
            incumbent_coverage = float(incumbent_selected.mean())
            if incumbent_selected.any():
                incumbent_precision = float(y_holdout[incumbent_selected].mean())
                incumbent_net_return = float(
                    holdout_returns[incumbent_selected].mean() - round_trip_cost
                )
            del incumbent, incumbent_scores
        except Exception as exc:
            log(f"Could not score the packaged legacy model on this holdout: {exc}")

        fit_frame, calibration_frame = _calibration_partition(development)
        del development
        for old_column in legacy_only_columns:
            holdout.drop(columns=old_column, inplace=True, errors="ignore")
            fit_frame.drop(columns=old_column, inplace=True, errors="ignore")
            calibration_frame.drop(columns=old_column, inplace=True, errors="ignore")
        X_holdout = np.ascontiguousarray(
            holdout[feature_cols].to_numpy(dtype=np.float32, copy=True)
        )
        del holdout

        y_cal = calibration_frame["target"].to_numpy(dtype=np.uint8, copy=True)
        if np.unique(y_cal).size < 2:
            raise ValueError("Calibration partition contains only one target class")
        X_cal = np.ascontiguousarray(
            calibration_frame[feature_cols].to_numpy(dtype=np.float32, copy=True)
        )
        del calibration_frame

        y_fit = fit_frame["target"].to_numpy(dtype=np.uint8, copy=True)
        if np.unique(y_fit).size < 2:
            raise ValueError("Training partition contains only one target class")

        cv_splits = date_based_splits(fit_frame, n_splits=3)
        fit_date_start = pd.to_datetime(fit_frame["trade_date"]).min().date()
        fit_date_end = pd.to_datetime(fit_frame["trade_date"]).max().date()
        X_fit = np.ascontiguousarray(fit_frame[feature_cols].to_numpy(dtype=np.float32, copy=True))
        del fit_frame
        log(
            f"[3/6] Date-based tuning: {len(cv_splits)} folds; "
            f"fit dates {fit_date_start} to {fit_date_end}"
        )
        search = RandomizedSearchCV(
            estimator=make_model(),
            param_distributions=parameter_search_space(),
            n_iter=3,
            scoring="average_precision",
            cv=cv_splits,
            n_jobs=1,
            pre_dispatch=1,
            random_state=42,
            refit=True,
            error_score="raise",
        )
        search.fit(X_fit, y_fit)
        tuned_estimator = search.best_estimator_
        log(f"Best time-split PR-AUC: {search.best_score_:.4f}")
        log(f"Best parameters: {search.best_params_}")

        calibration_scores = positive_probability(tuned_estimator, X_cal)
        calibrator = LogisticRegression(max_iter=1000, solver="lbfgs")
        calibrator.fit(calibration_scores.reshape(-1, 1), y_cal)
        calibrated_scores = calibrator.predict_proba(calibration_scores.reshape(-1, 1))[:, 1]
        calibration_rate = float(y_cal.mean())
        buy_goal = max(0.35, calibration_rate + 0.08)
        strong_buy_goal = max(0.50, calibration_rate + 0.20)
        buy_threshold = select_signal_threshold(
            y_cal, calibrated_scores, minimum_precision=buy_goal, minimum_coverage=0.01
        )
        strong_buy_threshold = select_signal_threshold(
            y_cal, calibrated_scores, minimum_precision=strong_buy_goal, minimum_coverage=0.005
        )
        if strong_buy_threshold is None:
            strong_buy_threshold = 1.01
        if buy_threshold is None:
            log(
                "Calibration window did not yield a Buy threshold with at least "
                f"{buy_goal:.1%} precision and 1% coverage."
            )
            buy_threshold_for_model = 1.01
        else:
            buy_threshold_for_model = buy_threshold
        holdout_raw_scores = positive_probability(tuned_estimator, X_holdout)
        holdout_probabilities = calibrator.predict_proba(
            holdout_raw_scores.reshape(-1, 1)
        )[:, 1]
        del holdout_raw_scores
        metrics = _metrics(y_holdout, holdout_probabilities, threshold=buy_threshold_for_model)
        metrics["training_stock_count"] = training_stock_count
        metrics["holdout_start"] = holdout_start
        metrics["holdout_end"] = holdout_end
        metrics["holdout_rows"] = int(len(y_holdout))
        selected_holdout = holdout_probabilities >= buy_threshold_for_model
        selected_returns = holdout_returns[selected_holdout]
        mean_net_return = (
            float(selected_returns.mean() - round_trip_cost)
            if len(selected_returns)
            else float("-inf")
        )
        metrics["mean_net_return"] = mean_net_return
        metrics["round_trip_cost_bps"] = round_trip_cost * 10000.0

        if incumbent_average_precision is not None:
            metrics["incumbent_average_precision"] = incumbent_average_precision
            metrics["incumbent_mean_net_return"] = incumbent_net_return
            metrics["incumbent_signal_coverage"] = incumbent_coverage
            metrics["incumbent_signal_precision"] = incumbent_precision

        log(
            f"Calibration thresholds: Buy={buy_threshold_for_model:.3f}, "
            f"Strong Buy={strong_buy_threshold:.3f}; holdout net mean={mean_net_return:.3%}"
        )
        log(
            "[4/6] Final unseen holdout: "
            f"{len(y_holdout):,} examples, base rate={metrics['positive_rate']:.3f}, "
            f"PR-AUC={metrics['average_precision']:.3f}, "
            f"Brier={metrics['brier']:.4f} (base={metrics['baseline_brier']:.4f}), "
            f"signal precision={metrics['signal_precision']:.3f}, "
            f"signal coverage={metrics['signal_coverage']:.3f}"
        )
        if incumbent_average_precision is not None:
            incumbent_net_text = (
                f"{incumbent_net_return:.3%}" if incumbent_net_return is not None else "no signals"
            )
            log(
                f"Active v2 on the same holdout: PR-AUC={incumbent_average_precision:.3f}, "
                f"signal precision={incumbent_precision:.3f}, "
                f"coverage={incumbent_coverage:.3f}, net mean={incumbent_net_text}"
            )

        beats_baselines = (
            buy_threshold is not None
            and metrics["average_precision"] >= metrics["positive_rate"] + 0.02
            and metrics["brier"] <= metrics["baseline_brier"] - 0.001
            and metrics["signal_coverage"] >= 0.005
            and metrics["signal_precision"] >= max(0.35, metrics["positive_rate"] + 0.05)
            and mean_net_return > 0.0
            and (
                incumbent_average_precision is None
                or metrics["average_precision"] > incumbent_average_precision
            )
            and (
                incumbent_net_return is None
                or mean_net_return > incumbent_net_return
            )
        )
        if not beats_baselines:
            log(
                "Holdout failed the benchmark, active-model comparison, signal-quality, "
                "or net-return gate; existing model was kept."
            )
            return {"promoted": False, "metrics": metrics}

        # Refit through the latest complete label date after the holdout audit.
        production_estimator = clone(tuned_estimator)
        production_X = np.concatenate((X_fit, X_cal, X_holdout), axis=0)
        production_y = np.concatenate((y_fit, y_cal, y_holdout), axis=0)
        production_estimator.fit(production_X, production_y)
        del production_X, production_y
        production_model = CalibratedProbabilityModel(
            production_estimator,
            calibrator,
            buy_threshold=buy_threshold_for_model,
            strong_buy_threshold=strong_buy_threshold,
            validation_metrics=metrics,
            trained_through=holdout_end,
        )

        os.makedirs(os.path.dirname(MODEL_FILE) or ".", exist_ok=True)
        temporary_file = f"{MODEL_FILE}.tmp"
        joblib.dump(production_model, temporary_file)
        os.replace(temporary_file, MODEL_FILE)
        log(f"[5/6] Promoted calibrated model to {MODEL_FILE}")
        log("[6/6] Training complete; the app can now load this model safely.")
        return {"promoted": True, "metrics": metrics, "model_path": MODEL_FILE}
    except Exception as exc:
        log(f"Training failed; the active model was left unchanged: {exc}")
        return {"promoted": False, "reason": str(exc)}


if __name__ == "__main__":
    train_global_model()
