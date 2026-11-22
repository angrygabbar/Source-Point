"""Chronological out-of-sample event backtest for the stock prediction model."""

import os

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score

from model_bundle import CalibratedProbabilityModel
from prediction_features import FEATURE_COLUMNS
from train_model import (
    MODEL_TYPE,
    date_based_splits,
    fetch_training_data,
    make_model,
    positive_probability,
    select_signal_threshold,
)


def _fold_parameters():
    if MODEL_TYPE == "XGBoost":
        return {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 4,
            "min_child_weight": 3,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "scale_pos_weight": 1.0,
        }
    return {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 3}


def run_backtest(threshold=None, cost_bps=None, logger=print):
    """Fit on past sessions and score later sessions, with realized exits.

    The result is trade-level, equal-weight event performance, not a portfolio
    simulation. `cost_bps` is a configurable round-trip friction assumption.
    """
    if threshold is None and os.getenv("BACKTEST_SIGNAL_THRESHOLD"):
        threshold = float(os.getenv("BACKTEST_SIGNAL_THRESHOLD"))
    if cost_bps is None:
        cost_bps = float(os.getenv("BACKTEST_ROUND_TRIP_COST_BPS", "30"))

    frame = fetch_training_data()
    if frame.empty:
        logger("No complete historical labels are available for the backtest.")
        return None

    folds = date_based_splits(frame, n_splits=3)
    out_of_sample = []
    params = _fold_parameters()

    for fold_number, (train_indices, test_indices) in enumerate(folds, start=1):
        train_frame = frame.iloc[train_indices].reset_index(drop=True)
        test_frame = frame.iloc[test_indices].copy()
        train_dates = np.sort(pd.to_datetime(train_frame["trade_date"]).drop_duplicates().to_numpy())
        calibration_size = max(40, int(np.ceil(len(train_dates) * 0.12)))
        calibration_start = len(train_dates) - calibration_size
        fit_end = calibration_start - 5
        if fit_end < 100:
            logger(f"Fold {fold_number}: insufficient dates; skipped.")
            continue

        fit_dates = train_dates[:fit_end]
        calibration_dates = train_dates[calibration_start:]
        fit_mask = pd.to_datetime(train_frame["trade_date"]).isin(fit_dates)
        calibration_mask = pd.to_datetime(train_frame["trade_date"]).isin(calibration_dates)
        fit_frame = train_frame.loc[fit_mask]
        calibration_frame = train_frame.loc[calibration_mask]

        estimator = make_model(params)
        estimator.fit(fit_frame[FEATURE_COLUMNS], fit_frame["target"])
        calibration_scores = positive_probability(estimator, calibration_frame[FEATURE_COLUMNS])
        if calibration_frame["target"].nunique() < 2:
            logger(f"Fold {fold_number}: calibration window has one class; skipped.")
            continue
        calibrator = LogisticRegression(max_iter=1000, solver="lbfgs")
        calibrator.fit(calibration_scores.reshape(-1, 1), calibration_frame["target"])
        calibrated = calibrator.predict_proba(calibration_scores.reshape(-1, 1))[:, 1]
        calibration_rate = float(calibration_frame["target"].mean())
        fold_threshold = threshold
        if fold_threshold is None:
            fold_threshold = select_signal_threshold(
                calibration_frame["target"],
                calibrated,
                minimum_precision=max(0.35, calibration_rate + 0.08),
                minimum_coverage=0.01,
            )
        if fold_threshold is None:
            fold_threshold = 1.01
            logger(f"Fold {fold_number}: no calibrated threshold met the Buy quality target.")
        model = CalibratedProbabilityModel(
            estimator,
            calibrator,
            buy_threshold=fold_threshold,
            strong_buy_threshold=fold_threshold,
        )

        test_frame["probability"] = model.predict_proba(test_frame[FEATURE_COLUMNS])[:, 1]
        test_frame["signal_threshold"] = fold_threshold
        test_frame["fold"] = fold_number
        out_of_sample.append(test_frame[[
            "trade_date", "sc_code", "target", "realized_return", "probability",
            "signal_threshold", "fold"
        ]])
        logger(
            f"Fold {fold_number}: trained through {fit_frame.trade_date.max().date()}, "
            f"tested {test_frame.trade_date.min().date()} to {test_frame.trade_date.max().date()} "
            f"({len(test_frame):,} stock-sessions)."
        )

    if not out_of_sample:
        logger("No out-of-sample folds completed.")
        return None

    predictions = pd.concat(out_of_sample, ignore_index=True)
    signals = predictions[predictions["probability"] >= predictions["signal_threshold"]].copy()
    prevalence = float(predictions["target"].mean())
    ap = float(average_precision_score(predictions["target"], predictions["probability"]))
    brier = float(brier_score_loss(predictions["target"], predictions["probability"]))
    baseline_brier = prevalence * (1.0 - prevalence)
    logger(f"\nWalk-forward OOS: {len(predictions):,} stock-sessions across {predictions.fold.nunique()} folds")
    logger(f"Positive target rate: {prevalence:.3%}; PR-AUC: {ap:.4f}; Brier: {brier:.4f} (base {baseline_brier:.4f})")
    logger(
        f"Signal threshold: {threshold if threshold is not None else 'calibration-selected'}; "
        f"coverage: {len(signals) / len(predictions):.3%}"
    )

    if signals.empty:
        logger("No signals crossed the configured probability threshold.")
        return {"predictions": predictions, "signals": signals}

    signals["net_return"] = signals["realized_return"] - (cost_bps / 10000.0)
    precision = float(precision_score(signals["target"], np.ones(len(signals)), zero_division=0))
    logger(f"Signals: {len(signals):,}; target-first hit rate: {precision:.3%}")
    logger(
        f"Mean realized return: gross {signals.realized_return.mean():.3%}, "
        f"net {signals.net_return.mean():.3%} after {cost_bps:g} round-trip bps; "
        f"net-positive trades: {(signals.net_return > 0).mean():.3%}"
    )
    return {"predictions": predictions, "signals": signals}


if __name__ == "__main__":
    run_backtest()
