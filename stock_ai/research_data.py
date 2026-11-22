"""Detailed stock research data from the local BSE store and cached public data."""

from __future__ import annotations

import difflib
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import psycopg2
import yfinance as yf
from ta.momentum import StochasticOscillator
from ta.trend import ADXIndicator

from config import DB_CONN_STR


MAX_HISTORY_ROWS = 6000
EXTERNAL_CACHE_HOURS = 24
RANGE_DAYS = {
    "1m": 31,
    "3m": 93,
    "6m": 186,
    "1y": 366,
    "3y": 1096,
    "5y": 1827,
    "max": None,
}

# Known BSE-code to Yahoo symbol mappings. Other symbols are resolved by a
# conservative company-name match and are always returned with their source.
TICKER_OVERRIDES = {
    507685: "WIPRO.BO",
    532540: "TCS.BO",
    500325: "RELIANCE.BO",
    500180: "HDFCBANK.BO",
    500209: "INFY.BO",
}

_external_locks: dict[int, threading.Lock] = {}
_external_locks_guard = threading.Lock()
_local_cache: OrderedDict[int, tuple[float, dict]] = OrderedDict()
_local_cache_lock = threading.Lock()
LOCAL_CACHE_SECONDS = 600
LOCAL_CACHE_MAX_STOCKS = 8


def _connect():
    return psycopg2.connect(DB_CONN_STR)


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _iso(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date().isoformat()
    if hasattr(value, "date") and not isinstance(value, date):
        value = value.date()
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _clean_company_name(value):
    text = re.sub(r"[^A-Z0-9 ]+", " ", str(value or "").upper())
    ignored = {"LIMITED", "LTD", "CORPORATION", "CORP", "COMPANY", "CO", "THE"}
    return " ".join(token for token in text.split() if token not in ignored)


def _company_match_score(left, right):
    a = _clean_company_name(left)
    b = _clean_company_name(right)
    if not a or not b:
        return 0.0
    sequence = difflib.SequenceMatcher(None, a, b).ratio()
    a_tokens, b_tokens = set(a.split()), set(b.split())
    overlap = len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))
    return max(sequence, overlap)


def _find_yahoo_symbol(code, company_name, cached_symbol=None):
    if cached_symbol:
        return cached_symbol
    if int(code) in TICKER_OVERRIDES:
        return TICKER_OVERRIDES[int(code)]
    if not company_name:
        return None

    result = yf.Search(str(company_name), max_results=10)
    candidates = []
    for quote in getattr(result, "quotes", []) or []:
        symbol = str(quote.get("symbol") or "").upper()
        quote_type = str(quote.get("quoteType") or "").upper()
        name = quote.get("longname") or quote.get("shortname") or ""
        if quote_type and quote_type not in {"EQUITY", "STOCK"}:
            continue
        if not symbol.endswith((".BO", ".NS")):
            continue
        score = _company_match_score(company_name, name)
        # For a BSE security, prefer its BSE listing when match quality is close.
        venue_bonus = 0.035 if symbol.endswith(".BO") else 0.0
        candidates.append((score + venue_bonus, score, symbol))

    candidates.sort(reverse=True)
    if not candidates or candidates[0][1] < 0.48:
        return None
    # Refuse ambiguous results rather than attach another company's financials.
    if len(candidates) > 1 and candidates[0][1] - candidates[1][1] < 0.035:
        same_name = _clean_company_name(company_name) == _clean_company_name(
            getattr(result, "quotes", [])[0].get("longname")
            or getattr(result, "quotes", [])[0].get("shortname")
            or ""
        ) if getattr(result, "quotes", []) else False
        if not same_name:
            return None
    return candidates[0][2]


def _frame_as_table(frame, max_periods=8):
    if frame is None or getattr(frame, "empty", True):
        return {"periods": [], "rows": []}
    frame = frame.iloc[:, :max_periods]
    periods = [_iso(column) for column in frame.columns]
    rows = []
    for metric, series in frame.iterrows():
        values = [_num(series.iloc[index]) for index in range(len(periods))]
        if any(value is not None for value in values):
            rows.append({"metric": str(metric), "values": values})
    return {"periods": periods, "rows": rows}


def _get_yahoo_payload(code, company_name, cached_symbol=None):
    symbol = _find_yahoo_symbol(code, company_name, cached_symbol)
    if not symbol:
        return None

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    # Keep fields used in analysis; raw Yahoo payloads are inconsistent and can
    # contain provider-specific objects that are not safe to store as JSON.
    info_fields = (
        "longName", "shortName", "symbol", "exchange", "fullExchangeName", "currency",
        "quoteType", "sector", "industry", "country", "website", "longBusinessSummary",
        "fullTimeEmployees", "marketCap", "enterpriseValue", "sharesOutstanding", "floatShares",
        "regularMarketPrice", "previousClose", "dayLow", "dayHigh", "fiftyTwoWeekLow",
        "fiftyTwoWeekHigh", "trailingPE", "forwardPE", "priceToBook",
        "priceToSalesTrailing12Months", "enterpriseToRevenue", "enterpriseToEbitda",
        "trailingEps", "forwardEps", "bookValue", "beta", "dividendRate", "dividendYield",
        "payoutRatio", "returnOnEquity", "returnOnAssets", "profitMargins", "operatingMargins",
        "grossMargins", "revenueGrowth", "earningsGrowth", "totalCash", "totalDebt",
        "debtToEquity", "currentRatio", "quickRatio", "freeCashflow", "operatingCashflow",
        "targetMeanPrice", "targetHighPrice", "targetLowPrice", "recommendationKey",
        "recommendationMean", "numberOfAnalystOpinions", "lastFiscalYearEnd", "mostRecentQuarter",
    )
    profile = {}
    for field in info_fields:
        value = info.get(field)
        if field in {"lastFiscalYearEnd", "mostRecentQuarter"}:
            value = datetime.fromtimestamp(value, timezone.utc).date().isoformat() if value else None
        elif isinstance(value, (str, bool)) or value is None:
            pass
        else:
            value = _num(value)
        profile[field] = value

    try:
        income_quarterly = _frame_as_table(ticker.quarterly_income_stmt, max_periods=8)
    except Exception:
        income_quarterly = {"periods": [], "rows": []}
    try:
        income_annual = _frame_as_table(ticker.income_stmt, max_periods=8)
    except Exception:
        income_annual = {"periods": [], "rows": []}
    try:
        balance_quarterly = _frame_as_table(ticker.quarterly_balance_sheet, max_periods=8)
    except Exception:
        balance_quarterly = {"periods": [], "rows": []}
    try:
        balance_annual = _frame_as_table(ticker.balance_sheet, max_periods=8)
    except Exception:
        balance_annual = {"periods": [], "rows": []}
    try:
        cashflow_quarterly = _frame_as_table(ticker.quarterly_cashflow, max_periods=8)
    except Exception:
        cashflow_quarterly = {"periods": [], "rows": []}
    try:
        cashflow_annual = _frame_as_table(ticker.cashflow, max_periods=8)
    except Exception:
        cashflow_annual = {"periods": [], "rows": []}

    ownership = []
    try:
        holders = ticker.major_holders
        if holders is not None and not holders.empty:
            ownership = [
                {"metric": str(index), "value": _num(row.get("Value"))}
                for index, row in holders.iterrows()
            ]
    except Exception:
        pass

    analyst_recommendations = []
    try:
        recommendations = ticker.recommendations_summary
        if recommendations is not None and not recommendations.empty:
            for _, row in recommendations.head(6).iterrows():
                analyst_recommendations.append({
                    "period": str(row.get("period", "")),
                    "strong_buy": _num(row.get("strongBuy")),
                    "buy": _num(row.get("buy")),
                    "hold": _num(row.get("hold")),
                    "sell": _num(row.get("sell")),
                    "strong_sell": _num(row.get("strongSell")),
                })
    except Exception:
        pass

    actions = []
    try:
        dividends = ticker.dividends
        for action_date, amount in dividends.tail(40).items():
            actions.append({"date": _iso(action_date), "type": "Dividend", "value": _num(amount)})
    except Exception:
        pass
    try:
        splits = ticker.splits
        for action_date, ratio in splits.tail(20).items():
            actions.append({"date": _iso(action_date), "type": "Stock split", "value": _num(ratio)})
    except Exception:
        pass
    actions.sort(key=lambda item: item["date"] or "", reverse=True)

    has_data = any((profile.get("longName"), income_quarterly["rows"], balance_quarterly["rows"]))
    if not has_data:
        return None
    return {
        "schema_version": 3,
        "provider": "Yahoo Finance via yfinance",
        "symbol": symbol,
        "profile": profile,
        "statements": {
            "income_quarterly": income_quarterly,
            "income_annual": income_annual,
            "balance_quarterly": balance_quarterly,
            "balance_annual": balance_annual,
            "cashflow_quarterly": cashflow_quarterly,
            "cashflow_annual": cashflow_annual,
        },
        "ownership": ownership,
        "analyst_recommendations": analyst_recommendations,
        "actions": actions,
    }


def _read_cached_external(code):
    conn = _connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT yahoo_symbol, fetched_at, payload FROM external_stock_research_cache WHERE sc_code = %s",
                (code,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {"symbol": row[0], "fetched_at": row[1], "payload": row[2]}
    finally:
        conn.close()


def get_external_research(code, refresh=False):
    """Return cached company facts, refreshing at most once per 24 hours."""
    code = int(code)
    try:
        cached = _read_cached_external(code)
    except Exception as exc:
        return {"available": False, "error": f"Research cache unavailable: {exc}"}

    now = datetime.now(timezone.utc)
    if cached:
        fetched_at = cached["fetched_at"]
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age_hours = (now - fetched_at).total_seconds() / 3600
        cache_version = int(cached["payload"].get("schema_version", 0))
        if not refresh and age_hours < EXTERNAL_CACHE_HOURS and cache_version >= 3:
            return {
                "available": True,
                "stale": False,
                "fetched_at": fetched_at.isoformat(),
                "age_hours": round(age_hours, 1),
                **cached["payload"],
            }

    with _external_locks_guard:
        lock = _external_locks.setdefault(code, threading.Lock())
    if not lock.acquire(blocking=False):
        if cached:
            return {
                "available": True,
                "stale": True,
                "fetched_at": cached["fetched_at"].isoformat(),
                **cached["payload"],
            }
        return {"available": False, "loading": True}

    try:
        conn = _connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT sc_name FROM daily_prices WHERE sc_code = %s ORDER BY trade_date DESC LIMIT 1",
                    (code,),
                )
                name_row = cursor.fetchone()
        finally:
            conn.close()
        name = name_row[0] if name_row else None
        payload = _get_yahoo_payload(code, name, cached.get("symbol") if cached else None)
        if payload is None:
            raise RuntimeError("No sufficiently close Yahoo Finance company match was found")

        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        conn = _connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO external_stock_research_cache (sc_code, provider, yahoo_symbol, fetched_at, payload)
                    VALUES (%s, %s, %s, NOW(), %s::jsonb)
                    ON CONFLICT (sc_code) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        yahoo_symbol = EXCLUDED.yahoo_symbol,
                        fetched_at = EXCLUDED.fetched_at,
                        payload = EXCLUDED.payload
                    """,
                    (code, payload["provider"], payload["symbol"], serialized),
                )
            conn.commit()
        finally:
            conn.close()
        return {
            "available": True,
            "stale": False,
            "fetched_at": now.isoformat(),
            "age_hours": 0,
            **payload,
        }
    except Exception as exc:
        if cached:
            fetched_at = cached["fetched_at"]
            return {
                "available": True,
                "stale": True,
                "fetched_at": fetched_at.isoformat(),
                "error": str(exc),
                **cached["payload"],
            }
        return {"available": False, "error": str(exc), "provider": "Yahoo Finance via yfinance"}
    finally:
        lock.release()


def refresh_cached_research(max_items=None, logger=print):
    """Refresh previously researched companies in a paced daily batch.

    Public Yahoo endpoints are unofficial and rate-limited. The scheduled job
    rotates through stocks the user has actually opened, rather than scraping
    thousands of unrelated securities on every run.
    """
    try:
        limit = int(max_items or os.getenv("RESEARCH_REFRESH_LIMIT", "100"))
    except (TypeError, ValueError):
        limit = 100
    limit = min(500, max(1, limit))
    conn = _connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT sc_code
                FROM external_stock_research_cache
                ORDER BY fetched_at ASC, sc_code
                LIMIT %s
                """,
                (limit,),
            )
            codes = [int(row[0]) for row in cursor.fetchall()]
    finally:
        conn.close()

    if not codes:
        logger("External research refresh skipped: no stocks have been researched yet.")
        return {"selected": 0, "refreshed": 0, "failed": 0}

    logger(f"Refreshing external research for {len(codes)} previously researched stocks.")
    refreshed = 0
    failed = 0
    for index, code in enumerate(codes, start=1):
        try:
            result = get_external_research(code, refresh=True)
            if result.get("available") and not result.get("stale"):
                refreshed += 1
                logger(f"Research refresh {index}/{len(codes)}: BSE {code} updated via {result.get('symbol')}.")
            else:
                failed += 1
                logger(f"Research refresh {index}/{len(codes)}: BSE {code} unchanged; source unavailable.")
        except Exception as exc:
            failed += 1
            logger(f"Research refresh {index}/{len(codes)}: BSE {code} failed: {str(exc)[:120]}")
        if index < len(codes):
            time.sleep(1.0)
    logger(f"External research batch complete: {refreshed} refreshed, {failed} failed.")
    return {"selected": len(codes), "refreshed": refreshed, "failed": failed}


def _safe_series_return(series, sessions):
    if len(series) <= sessions:
        return None
    previous = _num(series.iloc[-1 - sessions])
    latest = _num(series.iloc[-1])
    if previous is None or latest is None or previous == 0:
        return None
    return (latest / previous) - 1.0


def get_local_research(code, period="1y"):
    """Build history, valuation-ready local fundamentals and technicals."""
    code = int(code)
    period = period if period in RANGE_DAYS else "1y"
    with _local_cache_lock:
        cache_entry = _local_cache.get(code)
        if cache_entry and time.monotonic() - cache_entry[0] < LOCAL_CACHE_SECONDS:
            _local_cache.move_to_end(code)
            return _slice_local_payload(cache_entry[1], period)

    conn = _connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.trade_date, p.sc_name, p.open, p.high, p.low, p.close, p.volume,
                       p.delivery_pct, m.india_vix, m.usd_inr, m.nifty50_close,
                       m.crude_oil, m.us_market_close
                FROM (
                    SELECT trade_date, sc_name, open, high, low, close, volume, delivery_pct
                    FROM daily_prices
                    WHERE sc_code = %s
                    ORDER BY trade_date DESC
                    LIMIT %s
                ) p
                LEFT JOIN macro_indicators m ON m.trade_date = p.trade_date
                ORDER BY p.trade_date ASC
                """,
                (code, MAX_HISTORY_ROWS),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            columns = [description[0] for description in cursor.description]
            prices = pd.DataFrame(rows, columns=columns)
            cursor.execute(
                """
                SELECT period, revenue, net_profit, eps
                FROM quarterly_financials
                WHERE sc_code = %s
                ORDER BY period DESC
                LIMIT 40
                """,
                (code,),
            )
            financial_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT COUNT(*) FILTER (WHERE delivery_pct > 0), COUNT(*)
                FROM daily_prices WHERE sc_code = %s
                """,
                (code,),
            )
            delivery_rows, all_price_rows = cursor.fetchone()
    finally:
        conn.close()

    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    for column in (
        "open", "high", "low", "close", "volume", "delivery_pct", "india_vix",
        "usd_inr", "nifty50_close", "crude_oil", "us_market_close",
    ):
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    prices = prices.dropna(subset=["trade_date", "close"]).sort_values("trade_date").reset_index(drop=True)
    if prices.empty:
        return None

    close = prices["close"]
    high = prices["high"]
    low = prices["low"]
    volume = prices["volume"].fillna(0)
    prices["sma20"] = close.rolling(20, min_periods=20).mean()
    prices["sma50"] = close.rolling(50, min_periods=50).mean()
    prices["sma200"] = close.rolling(200, min_periods=200).mean()
    prices["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    prices["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    prices["ema200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    prices["macd"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    prices["macd_signal"] = prices["macd"].ewm(span=9, adjust=False).mean()
    prices["macd_hist"] = prices["macd"] - prices["macd_signal"]
    prices["bb_mid"] = close.rolling(20, min_periods=20).mean()
    prices["bb_std"] = close.rolling(20, min_periods=20).std()
    prices["bb_upper"] = prices["bb_mid"] + 2 * prices["bb_std"]
    prices["bb_lower"] = prices["bb_mid"] - 2 * prices["bb_std"]
    prices["volume_avg20"] = volume.rolling(20, min_periods=20).mean()
    prices["volume_ratio"] = volume / prices["volume_avg20"].replace(0, np.nan)
    daily_return = close.pct_change()
    prices["realized_vol20"] = daily_return.rolling(20, min_periods=20).std() * np.sqrt(252)

    latest = prices.iloc[-1]
    latest_date = latest["trade_date"].date()
    latest_close = _num(latest["close"])
    previous_close = _num(prices["close"].iloc[-2]) if len(prices) > 1 else None
    last_252 = prices.tail(252)
    high_52w = _num(last_252["high"].max())
    low_52w = _num(last_252["low"].min())
    macro_returns = None
    valid_market = prices[["close", "nifty50_close"]].dropna()
    if len(valid_market) > 25:
        stock_returns = valid_market["close"].pct_change().dropna()
        index_returns = valid_market["nifty50_close"].pct_change().dropna()
        paired = pd.concat([stock_returns, index_returns], axis=1).dropna().tail(252)
        beta = None
        correlation = None
        if len(paired) >= 30 and paired.iloc[:, 1].var() > 0:
            beta = _num(paired.iloc[:, 0].cov(paired.iloc[:, 1]) / paired.iloc[:, 1].var())
            correlation = _num(paired.iloc[:, 0].corr(paired.iloc[:, 1]))
        macro_returns = {
            "nifty_return_1m": _safe_series_return(valid_market["nifty50_close"], 21),
            "nifty_return_1y": _safe_series_return(valid_market["nifty50_close"], 252),
            "beta_1y": beta,
            "correlation_1y": correlation,
        }

    technical = {}
    for label, key in (
        ("sma_20", "sma20"), ("sma_50", "sma50"), ("sma_200", "sma200"),
        ("ema_20", "ema20"), ("ema_50", "ema50"), ("ema_200", "ema200"),
        ("macd", "macd"), ("macd_signal", "macd_signal"), ("macd_histogram", "macd_hist"),
        ("bollinger_middle", "bb_mid"), ("bollinger_upper", "bb_upper"),
        ("bollinger_lower", "bb_lower"), ("volume_average_20d", "volume_avg20"),
        ("volume_ratio_20d", "volume_ratio"), ("annualized_volatility_20d", "realized_vol20"),
    ):
        technical[label] = _num(latest[key])

    try:
        oscillator = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        technical["stochastic_k"] = _num(oscillator.stoch().iloc[-1])
        technical["stochastic_d"] = _num(oscillator.stoch_signal().iloc[-1])
    except Exception:
        technical["stochastic_k"] = technical["stochastic_d"] = None
    try:
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        technical["adx_14"] = _num(adx.adx().iloc[-1])
        technical["positive_di_14"] = _num(adx.adx_pos().iloc[-1])
        technical["negative_di_14"] = _num(adx.adx_neg().iloc[-1])
    except Exception:
        technical["adx_14"] = technical["positive_di_14"] = technical["negative_di_14"] = None

    # Match the serving feature implementation for RSI, ATR and its relative value.
    from prediction_features import build_features_for_stock

    feature_input = prices[[
        "trade_date", "open", "high", "low", "close", "volume", "india_vix", "usd_inr",
        "nifty50_close", "crude_oil", "us_market_close",
    ]].copy()
    engineered = build_features_for_stock(feature_input)
    if not engineered.empty:
        last_features = engineered.iloc[-1]
        technical["rsi_14"] = _num(last_features.get("rsi"))
        technical["atr_14"] = _num(last_features.get("atr"))
        technical["atr_pct"] = _num(last_features.get("atr_rel"))
        technical["trend_score_0_3"] = _num(last_features.get("trend_score"))
        technical["relative_strength_20d"] = _num(last_features.get("relative_strength_20d"))
        technical["us_return_20d_lagged"] = _num(last_features.get("us_ret_20d_lag1"))
        technical["crude_return_20d_lagged"] = _num(last_features.get("crude_ret_20d_lag1"))
    else:
        technical.update({key: None for key in (
            "rsi_14", "atr_14", "atr_pct", "trend_score_0_3", "relative_strength_20d",
            "us_return_20d_lagged", "crude_return_20d_lagged",
        )})

    financials = []
    for period_date, revenue, net_profit, eps in financial_rows:
        financials.append({
            "period": _iso(period_date), "revenue": _num(revenue),
            "net_profit": _num(net_profit), "eps": _num(eps),
        })
    latest_financials = financials[:4]
    ttm_eps = None if len(latest_financials) < 4 or any(row["eps"] is None for row in latest_financials) else sum(row["eps"] for row in latest_financials)
    trailing_pe = latest_close / ttm_eps if latest_close and ttm_eps and ttm_eps > 0 else None

    chart_frame = prices
    chart_bars = []
    for row in chart_frame.itertuples(index=False):
        chart_bars.append({
            "date": row.trade_date.date().isoformat(),
            "open": _num(row.open), "high": _num(row.high), "low": _num(row.low),
            "close": _num(row.close), "volume": _num(row.volume),
            "delivery_pct": (_num(row.delivery_pct) if _num(row.delivery_pct) and _num(row.delivery_pct) > 0 else None),
            "sma20": _num(row.sma20), "sma50": _num(row.sma50), "sma200": _num(row.sma200),
            "ema20": _num(row.ema20), "ema50": _num(row.ema50), "ema200": _num(row.ema200),
        })

    payload = {
        "code": code,
        "name": str(latest["sc_name"] or f"BSE {code}"),
        "exchange": "BSE",
        "price_source": "Stored BSE daily price history",
        "data_as_of": latest_date.isoformat(),
        "data_age_days": max(0, (date.today() - latest_date).days),
        "history_sessions": int(len(prices)),
        "price_bars": chart_bars,
        "summary": {
            "last_close": latest_close,
            "previous_close": previous_close,
            "change_1d": latest_close - previous_close if latest_close is not None and previous_close is not None else None,
            "return_1d": _safe_series_return(close, 1),
            "return_1w": _safe_series_return(close, 5),
            "return_1m": _safe_series_return(close, 21),
            "return_3m": _safe_series_return(close, 63),
            "return_6m": _safe_series_return(close, 126),
            "return_1y": _safe_series_return(close, 252),
            "high_52w": high_52w,
            "low_52w": low_52w,
            "distance_from_52w_high": latest_close / high_52w - 1 if latest_close and high_52w else None,
            "distance_from_52w_low": latest_close / low_52w - 1 if latest_close and low_52w else None,
            "volume": _num(latest["volume"]),
            "volume_average_20d": _num(latest["volume_avg20"]),
            "turnover_value": latest_close * _num(latest["volume"]) if latest_close is not None and _num(latest["volume"]) is not None else None,
            "ttm_eps_local": ttm_eps,
            "pe_local": trailing_pe,
        },
        "technical": technical,
        "financials": financials,
        "macro": {
            "india_vix": _num(latest["india_vix"]),
            "usd_inr": _num(latest["usd_inr"]),
            "nifty50_close": _num(latest["nifty50_close"]),
            "crude_oil": _num(latest["crude_oil"]),
            "us_market_close": _num(latest["us_market_close"]),
            **(macro_returns or {}),
        },
        "coverage": {
            "daily_price_rows": int(all_price_rows),
            "delivery_rows_with_values": int(delivery_rows),
            "local_financial_quarters": int(len(financials)),
            "local_financials_as_of": financials[0]["period"] if financials else None,
            "macro_as_of": latest_date.isoformat() if any(_num(latest[key]) is not None for key in (
                "india_vix", "usd_inr", "nifty50_close", "crude_oil", "us_market_close"
            )) else None,
        },
    }
    with _local_cache_lock:
        _local_cache[code] = (time.monotonic(), payload)
        _local_cache.move_to_end(code)
        while len(_local_cache) > LOCAL_CACHE_MAX_STOCKS:
            _local_cache.popitem(last=False)
    return _slice_local_payload(payload, period)


def _slice_local_payload(payload, period):
    days = RANGE_DAYS[period]
    bars = payload["price_bars"]
    if days is not None:
        cutoff = (date.fromisoformat(payload["data_as_of"]) - timedelta(days=days)).isoformat()
        bars = [bar for bar in bars if bar["date"] >= cutoff]
    return {**payload, "range": period, "price_bars": bars}
