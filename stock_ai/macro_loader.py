"""Refresh daily macro series used by the stock model.

Yahoo Finance is accessed through yfinance, an unofficial client. Missing
observations are carried forward for legacy consumers, but never backfilled
from a future date. The prediction feature builder separately lags series
that close after the Indian market.
"""

import logging
import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd
import psycopg2
import yfinance as yf
from psycopg2.extras import execute_values

try:
    from config import DB_CONN_STR
    DB_CONFIG = DB_CONN_STR
except ImportError:
    DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5435"

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=FutureWarning)

INDICATORS = {
    "^INDIAVIX": "india_vix",
    "INR=X": "usd_inr",
    "CL=F": "crude_oil",
    "^GSPC": "us_market_close",
    "^NSEI": "nifty50_close",
}
START_DATE = "2010-01-01"


def get_db_connection():
    return psycopg2.connect(DB_CONFIG)


def _effective_start_date(requested_start):
    if requested_start and requested_start != START_DATE:
        return requested_start
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(trade_date) FROM macro_indicators")
                latest_macro = cursor.fetchone()[0]
                cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
                latest_prices = cursor.fetchone()[0]
        finally:
            conn.close()
    except Exception:
        return START_DATE

    if latest_macro is None:
        return START_DATE
    if latest_prices and (latest_prices - latest_macro).days > 45:
        return (latest_macro - timedelta(days=45)).isoformat()
    return (date.today() - timedelta(days=45)).isoformat()


def _download_close(ticker, start_date=START_DATE):
    """Download one close series and normalize current yfinance column shapes."""
    data = yf.download(
        ticker,
        start=start_date,
        end=(date.today().isoformat()),
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=30,
        multi_level_index=False,
    )
    if data is None or data.empty:
        raise RuntimeError("provider returned no rows")

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        if ticker in close.columns:
            close = close[ticker]
        else:
            close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").rename(INDICATORS[ticker])
    if close.dropna().empty:
        raise RuntimeError("provider response had no usable close values")
    close.index = pd.to_datetime(close.index)
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close.index = close.index.normalize()
    return close[~close.index.duplicated(keep="last")]


def fetch_macro_data(start_date=START_DATE):
    """Refresh macro history idempotently; existing stock rows are untouched."""
    start_date = _effective_start_date(start_date)
    print("--- Refreshing macro-economic series ---", flush=True)
    print(f"[i] Requesting provider history from {start_date}.", flush=True)
    series = {}
    for ticker, column in INDICATORS.items():
        try:
            print(f"[+] Fetching {column} ({ticker})...", flush=True)
            data = _download_close(ticker, start_date)
            series[column] = data
            print(
                f"    {len(data):,} observations; latest "
                f"{data.index.max().date()} = {data.dropna().iloc[-1]:.4g}",
                flush=True,
            )
        except Exception as exc:
            print(f"[!] Could not refresh {column}: {exc}", flush=True)

    if not series:
        raise RuntimeError("No macro series could be downloaded; database was not changed")

    observed = pd.concat(series.values(), axis=1, sort=True).sort_index()
    observed = observed.replace([np.inf, -np.inf], np.nan)
    for column in INDICATORS.values():
        if column not in observed.columns:
            observed[column] = np.nan

    # US/FX/commodity daily closes become available after the Indian cash
    # session. Store them on the next calendar date so Friday's close is
    # available to Monday, while Friday only sees Thursday's close.
    delayed_columns = {
        "usd_inr": "usd_inr_available",
        "crude_oil": "crude_oil_available",
        "us_market_close": "us_market_close_available",
    }
    available_source_by_column = {
        available_column: source_column
        for source_column, available_column in delayed_columns.items()
    }
    availability = {}
    all_dates = observed.index
    for source_column, available_column in delayed_columns.items():
        actual = observed[source_column].dropna()
        actual.index = actual.index + pd.Timedelta(days=1)
        availability[available_column] = actual
        all_dates = all_dates.union(actual.index)

    all_dates = all_dates.sort_values()
    # Forward fill only. Backfilling would leak future observations into early dates.
    macro = observed.reindex(all_dates).sort_index().ffill().dropna(how="all")
    for column, values_by_date in availability.items():
        macro[column] = values_by_date.reindex(macro.index).ffill()

    values = []
    for index, row in macro.iterrows():
        values.append((
            index.date(),
            *[
                None if pd.isna(row.get(column)) else float(row[column])
                for column in INDICATORS.values()
            ],
            *[
                None if pd.isna(row.get(column)) else float(row[column])
                for column in delayed_columns.values()
            ],
        ))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_indicators (
                    trade_date DATE PRIMARY KEY,
                    india_vix NUMERIC(10, 2),
                    usd_inr NUMERIC(10, 2),
                    crude_oil NUMERIC(10, 2),
                    us_market_close NUMERIC(10, 2),
                    nifty50_close NUMERIC(10, 2),
                    usd_inr_available NUMERIC(10, 2),
                    crude_oil_available NUMERIC(10, 2),
                    us_market_close_available NUMERIC(10, 2)
                )
            """)
            cursor.execute("""
                ALTER TABLE macro_indicators
                ADD COLUMN IF NOT EXISTS crude_oil NUMERIC(10, 2)
            """)
            cursor.execute("""
                ALTER TABLE macro_indicators
                ADD COLUMN IF NOT EXISTS us_market_close NUMERIC(10, 2)
            """)
            cursor.execute("""
                ALTER TABLE macro_indicators
                ADD COLUMN IF NOT EXISTS nifty50_close NUMERIC(10, 2)
            """)
            for column in delayed_columns.values():
                cursor.execute(f"""
                    ALTER TABLE macro_indicators
                    ADD COLUMN IF NOT EXISTS {column} NUMERIC(10, 2)
                """)
            source_columns = list(INDICATORS.values())
            column_source = {
                **{column: column for column in source_columns},
                **available_source_by_column,
            }
            update_sql = ",\n".join(
                (
                    f"{column} = EXCLUDED.{column}"
                    if source_column in series
                    else f"{column} = COALESCE(EXCLUDED.{column}, macro_indicators.{column})"
                )
                for column, source_column in column_source.items()
            )
            execute_values(cursor, """
                INSERT INTO macro_indicators
                    (trade_date, india_vix, usd_inr, crude_oil, us_market_close, nifty50_close,
                     usd_inr_available, crude_oil_available, us_market_close_available)
                VALUES %s
                ON CONFLICT (trade_date) DO UPDATE SET
            """ + update_sql, values, page_size=500)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    latest = macro.index.max().date()
    print(f"✅ Refreshed {len(values):,} macro dates through {latest}.", flush=True)
    return {"rows": len(values), "latest_date": latest}


if __name__ == "__main__":
    fetch_macro_data()
