"""Feature and event-label definitions shared by training, scoring, and backtests."""

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands


LEGACY_FEATURE_COLUMNS = [
    "trend_score",
    "rsi",
    "macd_diff",
    "bb_width",
    "atr_rel",
    "vol_shock",
    "vix_level",
    "vix_change",
    "usd_trend",
    "pe_ratio",
]

FEATURE_COLUMNS = [
    "trend_score",
    "rsi",
    "macd_diff_rel",
    "bb_width",
    "atr_rel",
    "vol_shock",
    "vix_level",
    "vix_change",
    "usd_trend_lag1",
    "eps_ttm_yield",
    "financial_age_log",
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "close_to_ema_20",
    "close_to_ema_50",
    "close_to_ema_200",
    "realized_vol_20",
    "nifty_ret_5d",
    "nifty_ret_20d",
    "relative_strength_20d",
    "us_ret_5d_lag1",
    "us_ret_20d_lag1",
    "crude_ret_5d_lag1",
    "crude_ret_20d_lag1",
    "intraday_return",
    "turnover_log",
]

HORIZON_SESSIONS = 5
UPSIDE_ATR_MULTIPLE = 1.5
DOWNSIDE_ATR_MULTIPLE = 1.0


def build_features_for_stock(raw_frame):
    """Build causal features for one stock, in date order.

    The caller supplies daily OHLCV and point-in-time macro/fundamental columns.
    Missing macro values are forward-filled only; future values are never backfilled.
    """
    if raw_frame is None or raw_frame.empty:
        return pd.DataFrame()

    df = raw_frame.copy()
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
        df = df.dropna(subset=["trade_date"]).sort_values("trade_date")
        df = df.drop_duplicates(subset=["trade_date"], keep="last")
    if len(df) < 200:
        return pd.DataFrame()

    required = ["open", "high", "low", "close", "volume"]
    if any(column not in df.columns for column in required):
        return pd.DataFrame()

    for column in required + [
        "india_vix", "usd_inr", "nifty50_close", "us_market_close",
        "crude_oil", "usd_inr_available", "us_market_close_available",
        "crude_oil_available", "eps", "eps_ttm",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    close = df["close"].astype(float)
    df["ema_20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["ema_50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["ema_200"] = EMAIndicator(close=close, window=200).ema_indicator()
    df["trend_score"] = (
        (close > df["ema_20"]).astype(int)
        + (df["ema_20"] > df["ema_50"]).astype(int)
        + (df["ema_50"] > df["ema_200"]).astype(int)
    )

    df["rsi"] = RSIIndicator(close=close, window=14).rsi()
    macd_diff = MACD(close=close).macd_diff()
    df["macd_diff"] = macd_diff
    df["macd_diff_rel"] = macd_diff / close.replace(0, np.nan)
    df["bb_width"] = BollingerBands(close=close, window=20).bollinger_wband()
    df["atr"] = AverageTrueRange(
        high=df["high"].astype(float),
        low=df["low"].astype(float),
        close=close,
    ).average_true_range()
    df["atr_rel"] = df["atr"] / close.replace(0, np.nan)

    average_volume = df["volume"].rolling(20, min_periods=20).mean()
    df["vol_shock"] = df["volume"] / (average_volume + 1.0)

    one_day_return = close.pct_change()
    df["ret_1d"] = one_day_return
    df["ret_5d"] = close.pct_change(5)
    df["ret_20d"] = close.pct_change(20)
    df["ret_60d"] = close.pct_change(60)
    df["close_to_ema_20"] = close / df["ema_20"] - 1.0
    df["close_to_ema_50"] = close / df["ema_50"] - 1.0
    df["close_to_ema_200"] = close / df["ema_200"] - 1.0
    df["realized_vol_20"] = one_day_return.rolling(20, min_periods=20).std()
    df["intraday_return"] = df["close"] / df["open"].replace(0, np.nan) - 1.0
    df["turnover_log"] = np.log1p((df["close"] * df["volume"]).clip(lower=0))

    if "india_vix" not in df.columns:
        df["india_vix"] = np.nan
    df["india_vix"] = df["india_vix"].ffill().fillna(15.0)
    df["vix_level"] = df["india_vix"]
    df["vix_change"] = df["india_vix"].diff().fillna(0.0)

    if "usd_inr" not in df.columns:
        df["usd_inr"] = np.nan
    df["usd_inr"] = df["usd_inr"].ffill()
    # Retain the same-date value for legacy-model compatibility. The promoted
    # model uses the strictly lagged variant below because FX is a global close.
    df["usd_trend"] = df["usd_inr"].pct_change(5).replace([np.inf, -np.inf], np.nan)
    df["usd_trend"] = df["usd_trend"].fillna(0.0)
    if "usd_inr_available" in df.columns:
        usd_available = pd.to_numeric(df["usd_inr_available"], errors="coerce").ffill()
    else:
        usd_available = df["usd_inr"].shift(1)
    df["usd_trend_lag1"] = usd_available.pct_change(5).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if "nifty50_close" not in df.columns:
        df["nifty50_close"] = np.nan
    df["nifty50_close"] = df["nifty50_close"].ffill()
    df["nifty_ret_5d"] = df["nifty50_close"].pct_change(5).fillna(0.0)
    df["nifty_ret_20d"] = df["nifty50_close"].pct_change(20).fillna(0.0)
    df["relative_strength_20d"] = df["ret_20d"] - df["nifty_ret_20d"]

    # US index, FX and commodity closes happen after the Indian cash close.
    # Shift one stock session so the model never sees information unavailable
    # when the signal is formed.
    for column, available_column, prefix in (
        ("us_market_close", "us_market_close_available", "us_ret"),
        ("crude_oil", "crude_oil_available", "crude_ret"),
    ):
        if column not in df.columns:
            df[column] = np.nan
        if available_column in df.columns:
            lagged = pd.to_numeric(df[available_column], errors="coerce").ffill()
        else:
            lagged = pd.to_numeric(df[column], errors="coerce").ffill().shift(1)
        df[f"{prefix}_5d_lag1"] = lagged.pct_change(5).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        df[f"{prefix}_20d_lag1"] = lagged.pct_change(20).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if "eps" not in df.columns:
        df["eps"] = 0.0
    df["eps"] = df["eps"].ffill().fillna(0.0)
    df["pe_ratio"] = np.where(
        df["eps"] > 0.1,
        (close / df["eps"]).clip(upper=200),
        0.0,
    )

    if "eps_ttm" not in df.columns:
        df["eps_ttm"] = np.nan
    df["eps_ttm"] = pd.to_numeric(df["eps_ttm"], errors="coerce").ffill().fillna(0.0)
    df["eps_ttm_yield"] = df["eps_ttm"] / close.replace(0, np.nan)
    if "financial_period" in df.columns:
        financial_period = pd.to_datetime(df["financial_period"], errors="coerce")
        period_age_days = (df["trade_date"] - financial_period).dt.days
    else:
        period_age_days = pd.Series(np.nan, index=df.index)
    df["financial_age_log"] = np.log1p(
        period_age_days.clip(lower=0, upper=3650).fillna(3650)
    )

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    # Ensure every row has at least 200 prior sessions for the long trend features.
    df = df.iloc[199:].copy()
    df.dropna(subset=FEATURE_COLUMNS + ["atr", "close", "open", "high", "low"], inplace=True)
    return df


def add_barrier_labels(frame, horizon=HORIZON_SESSIONS,
                       upside_atr=UPSIDE_ATR_MULTIPLE,
                       downside_atr=DOWNSIDE_ATR_MULTIPLE):
    """Label target-first barrier outcomes and simulated returns.

    A signal is formed after session t and enters at session t+1 open. The
    upside barrier is 1.5 ATR above entry and the stop is 1 ATR below entry.
    If both barriers trade during one daily bar, the stop is assumed to fill
    first. Rows without a complete forward horizon remain unlabeled.
    """
    if frame is None or frame.empty:
        return pd.DataFrame()

    result = frame.copy()
    result["target"] = np.nan
    result["realized_return"] = np.nan

    for _, group in result.groupby("sc_code", sort=False):
        group = group.sort_values("trade_date")
        indexes = group.index.to_numpy()
        size = len(group)
        if size <= horizon:
            continue

        entry = group["open"].shift(-1).to_numpy(dtype=float)
        atr = group["atr"].to_numpy(dtype=float)
        final_close = group["close"].shift(-horizon).to_numpy(dtype=float)
        target_level = entry + upside_atr * atr
        stop_level = entry - downside_atr * atr

        valid = (
            np.isfinite(entry)
            & np.isfinite(atr)
            & np.isfinite(final_close)
            & (entry > 0)
            & (atr > 0)
        )

        future_bars = []
        for step in range(1, horizon + 1):
            bar_open = group["open"].shift(-step).to_numpy(dtype=float)
            bar_high = group["high"].shift(-step).to_numpy(dtype=float)
            bar_low = group["low"].shift(-step).to_numpy(dtype=float)
            valid &= np.isfinite(bar_open) & np.isfinite(bar_high) & np.isfinite(bar_low)
            future_bars.append((step, bar_open, bar_high, bar_low))

        resolved = np.zeros(size, dtype=bool)
        target_won = np.zeros(size, dtype=bool)
        exit_price = final_close.copy()

        for step, bar_open, bar_high, bar_low in future_bars:
            active = valid & ~resolved
            if not active.any():
                break

            gap_up = (step > 1) & (bar_open >= target_level)
            gap_down = (step > 1) & (bar_open <= stop_level)
            hit_target = gap_up | ((bar_high >= target_level) & ~gap_down)
            hit_stop = gap_down | ((bar_low <= stop_level) & ~gap_up)

            # Conservative fill when both barriers trade in the same session.
            stop_first = active & hit_stop
            target_first = active & hit_target & ~hit_stop

            exit_price[stop_first] = np.where(
                gap_down[stop_first], bar_open[stop_first], stop_level[stop_first]
            )
            exit_price[target_first] = np.where(
                gap_up[target_first], bar_open[target_first], target_level[target_first]
            )
            target_won[target_first] = True
            resolved |= stop_first | target_first

        labels = np.where(valid, target_won.astype(float), np.nan)
        returns = np.where(valid, exit_price / entry - 1.0, np.nan)
        result.loc[indexes, "target"] = labels
        result.loc[indexes, "realized_return"] = returns

    return result
