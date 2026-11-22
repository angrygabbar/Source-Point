import psycopg2
import pandas as pd
import numpy as np
import requests
import zipfile
import io
import warnings
import math
import time
import random
import yfinance as yf
import logging
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import joblib
import os
import threading
from prediction_features import FEATURE_COLUMNS, LEGACY_FEATURE_COLUMNS, build_features_for_stock

# --- CONFIGURATION ---
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

try:
    from config import DB_CONN_STR
    DB_CONFIG = DB_CONN_STR
except ImportError:
    DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5433"

TICKER_OVERRIDES = {
    507685: "WIPRO.BO", 532540: "TCS.BO", 500325: "RELIANCE.BO",
    500180: "HDFCBANK.BO", 500209: "INFY.BO"
}

# --- AI MODEL LOADER ---
MODEL_PATH = os.getenv("MODEL_PATH", "models/stock_ai_brain_v3.pkl")
LEGACY_MODEL_PATH = "stock_ai_brain_v2.pkl"
GLOBAL_MODEL = None
ACTIVE_MODEL_PATH = None
_MODEL_LOCK = threading.RLock()


def reload_global_model():
    """Load the promoted model atomically; fall back to the packaged v2 model."""
    global GLOBAL_MODEL, ACTIVE_MODEL_PATH
    for model_path in (MODEL_PATH, LEGACY_MODEL_PATH):
        if not os.path.exists(model_path):
            continue
        try:
            candidate = joblib.load(model_path)
            with _MODEL_LOCK:
                GLOBAL_MODEL = candidate
                ACTIVE_MODEL_PATH = model_path
            print(f"[AI] ✅ Loaded Global Model: {model_path}")
            return True
        except Exception as exc:
            print(f"[AI] ⚠️ Model Load Error ({model_path}): {exc}")
    with _MODEL_LOCK:
        GLOBAL_MODEL = None
        ACTIVE_MODEL_PATH = None
    print("[AI] ℹ️ No model artifact found. Using fallback logic.")
    return False


reload_global_model()

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONFIG)
        conn.set_session(isolation_level=psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        cursor = conn.cursor()
        cursor.execute("SET max_parallel_workers_per_gather = 0;")
        conn.commit()
        cursor.close()
        return conn
    except: return None

# --- SEARCH ASSETS ---
def search_assets(query):
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        res = cursor.fetchone()
        latest_date = res[0] if res else None
        if not latest_date: return []

        search_term = f"%{query}%"
        q = "SELECT sc_code, sc_name FROM daily_prices WHERE trade_date = %s AND (sc_name ILIKE %s OR CAST(sc_code AS TEXT) LIKE %s) LIMIT 10"
        cursor.execute(q, (latest_date, search_term, search_term))
        results = [{"code": r[0], "name": r[1]} for r in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        print(f"[Search Error] {e}")
        return []

# --- DASHBOARD STATS ---
def get_market_status():
    conn = get_db_connection()
    if not conn: return {"date": "Offline", "top_gainer": "--", "gainer_price": 0, "nifty_level": "N/A"}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        res = cursor.fetchone()
        last_date = res[0] if res else None
        
        # Try LIVE Nifty first via Yahoo Finance
        nifty_val = "N/A"
        try:
            nifty_info = yf.Ticker("^NSEI").fast_info
            if nifty_info and nifty_info.last_price:
                nifty_val = float(round(nifty_info.last_price, 2))
        except:
            # Fallback to DB
            try:
                cursor.execute("SELECT nifty50_close FROM macro_indicators WHERE trade_date = %s", (last_date,))
                res = cursor.fetchone()
                if res: nifty_val = float(round(res[0], 2))
            except: pass

        cursor.execute("SELECT sc_name, close, open FROM daily_prices WHERE trade_date = %s ORDER BY (close-open)/open DESC LIMIT 1", (last_date,))
        gainer = cursor.fetchone()
        conn.close()
        return {
            "date": str(last_date),
            "top_gainer": gainer[0] if gainer else "N/A",
            "gainer_price": float(gainer[1]) if gainer else 0.0,
            "nifty_level": nifty_val
        }
    except: return {"date": "Error", "top_gainer": "--", "gainer_price": 0, "nifty_level": "N/A"}

# --- LIVE QUOTE ---
def get_live_quote(code):
    try:
        code_int = int(code) if str(code).isdigit() else None
        ticker = TICKER_OVERRIDES.get(code_int, f"{code}.BO" if str(code).isdigit() else code)
        stock = yf.Ticker(ticker)
        try:
            current = stock.fast_info.last_price
            prev_close = stock.fast_info.previous_close
        except: current = None

        if (current is None or str(current) == 'nan') and code_int:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT sc_name FROM daily_prices WHERE sc_code = %s", (code_int,))
                    res = cursor.fetchone()
                    if res:
                        ticker = res[0].split()[0].replace(',', '').upper() + ".BO"
                        stock = yf.Ticker(ticker)
                        current = stock.fast_info.last_price
                        prev_close = stock.fast_info.previous_close
                except: pass
                finally: conn.close()

        if current is None or prev_close is None: return None
        change = current - prev_close
        return {
            "price": float(round(current, 2)),
            "change": float(round(change, 2)),
            "pct": float(round((change / prev_close) * 100, 2)),
            "color": "green" if change >= 0 else "red"
        }
    except: return None

def get_market_indices():
    indices = {
        "^BSESN": "SENSEX",
        "^NSEI": "NIFTY 50",
        "^NSEBANK": "BANK NIFTY",
        "^INDIAVIX": "INDIA VIX",
        "^CNXIT": "NIFTY IT",
        "GC=F": "GOLD",
        "CL=F": "CRUDE OIL",
        "INR=X": "USD/INR",
    }
    data = []
    for ticker, name in indices.items():
        try:
            info = yf.Ticker(ticker).fast_info
            current = info.last_price
            prev = info.previous_close
            if current and prev:
                change = current - prev
                # VIX is inverse — rising VIX = red (fear), falling VIX = green (calm)
                if name == "INDIA VIX":
                    color = "text-red-400" if change >= 0 else "text-green-400"
                else:
                    color = "text-green-400" if change >= 0 else "text-red-400"
                data.append({
                    "name": name,
                    "price": float(round(current, 2)),
                    "change": float(round(change, 2)),
                    "pct": float(round((change / prev) * 100, 2)),
                    "color": color
                })
        except: continue
    return data

# --- AI PREDICTION (QUANT FUSION LOGIC v5.1) ---
def prepare_features(df, extra_data=None):
    """Compatibility wrapper around the shared training/serving features."""
    if extra_data:
        df = df.copy()
        aliases = {
            "vix": "india_vix",
            "usd_inr": "usd_inr",
            "eps": "eps",
        }
        for source, target in aliases.items():
            if source in extra_data:
                df[target] = extra_data[source]
    return build_features_for_stock(df)

def run_ai_prediction(code):
    if not code: return None
    conn = get_db_connection()
    if not conn: return None
    try:
        q = """
            SELECT p.trade_date, p.open, p.high, p.low, p.close, p.volume,
                   m.india_vix, m.usd_inr, m.nifty50_close, m.crude_oil,
                   m.us_market_close, m.usd_inr_available, m.crude_oil_available,
                   m.us_market_close_available, f.eps, f.eps_ttm, f.financial_period
            FROM (
                SELECT trade_date, sc_code, open, high, low, close, volume
                FROM daily_prices
                WHERE sc_code = %s
                ORDER BY trade_date DESC
                LIMIT 900
            ) p
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
            ORDER BY p.trade_date ASC
        """
        try:
            df = pd.read_sql(q, conn, params=[code])
        finally:
            conn.close()

        if len(df) < 200:
            return None

        # Use the same causal feature builder that generated the training rows.
        df = prepare_features(df)
        if df.empty:
            return None
        latest = df.iloc[[-1]].copy()

        current_vix = float(latest["vix_level"].iloc[0])
        latest_eps_ttm = (
            float(latest["eps_ttm"].iloc[0])
            if "eps_ttm" in latest and pd.notna(latest["eps_ttm"].iloc[0])
            else 0.0
        )
        current_price = float(latest['close'].values[0])
        buy_probability = 0.0
        confidence_basis = "heuristic_not_calibrated"
        buy_threshold = 0.60
        strong_buy_threshold = 0.75

        # --- PROBABILITY PREDICTION ---
        with _MODEL_LOCK:
            model = GLOBAL_MODEL
        if model:
            try:
                buy_threshold = float(getattr(model, "buy_threshold", buy_threshold))
                strong_buy_threshold = float(getattr(model, "strong_buy_threshold", strong_buy_threshold))
                model_features = getattr(model, "feature_columns", LEGACY_FEATURE_COLUMNS)
                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(latest[model_features])[0]
                    classes = list(getattr(model, "classes_", [0, 1]))
                    buy_probability = float(probs[classes.index(1)])
                    confidence_basis = (
                        "calibrated_model"
                        if model.__class__.__name__ == "CalibratedProbabilityModel"
                        else "legacy_model_not_calibrated"
                    )
                else:
                    pred = model.predict(latest[model_features])[0]
                    buy_probability = 0.9 if pred == 1 else 0.1
                    confidence_basis = "legacy_model_not_calibrated"
            except Exception as e:
                print(f"Prediction Error: {e}")
                return None
        else:
            # Rule-Based Fallback (Updated with Trend Score)
            trend = latest['trend_score'].values[0]
            rsi = latest['rsi'].values[0]
            
            if trend == 3 and rsi < 70: buy_probability = 0.85
            elif trend == 0: buy_probability = 0.10
            elif rsi < 30: buy_probability = 0.60
            else: buy_probability = 0.40

        # --- SMART SIGNAL LOGIC ---
        # Get ATR for dynamic targets
        atr_val = float(latest['atr'].values[0])
        
        target_price = current_price + (1.5 * atr_val)
        stop_loss = current_price - (1.0 * atr_val)
        
        if confidence_basis != "calibrated_model":
            signal = "UNVALIDATED SCORE"
        elif buy_probability >= strong_buy_threshold:
            signal = "STRONG BUY 🚀"
        elif buy_probability >= buy_threshold:
            signal = "BUY 🟢"
        elif buy_probability <= 0.25:
            signal = "SELL 🔴"
        else:
            signal = "HOLD ⚪"
            
        est_return = f"{round(((target_price - current_price)/current_price)*100, 1)}%"
        data_as_of = pd.Timestamp(latest["trade_date"].iloc[0]).date()
        data_age_days = max(0, (pd.Timestamp.now().normalize() - pd.Timestamp(data_as_of)).days)
        if data_age_days > 5:
            signal = "STALE DATA • NO SIGNAL"
        financial_period_value = latest.get("financial_period")
        financial_period = None
        if financial_period_value is not None and pd.notna(financial_period_value.iloc[0]):
            financial_period = pd.Timestamp(financial_period_value.iloc[0]).date().isoformat()
        model_label = (
            f"{getattr(model, 'model_version', 'Calibrated model')}"
            + (f" · trained through {model.trained_through}" if getattr(model, "trained_through", None) else "")
            if confidence_basis == "calibrated_model"
            else "Legacy v2 (unvalidated)"
            if confidence_basis == "legacy_model_not_calibrated"
            else "Heuristic fallback"
        )
        validation = getattr(model, "validation_metrics", {}) if model else {}
        validation_summary = {
            key: validation[key]
            for key in (
                "holdout_start", "holdout_end", "average_precision", "positive_rate",
                "brier", "baseline_brier", "signal_precision", "signal_coverage",
                "mean_net_return", "round_trip_cost_bps", "training_stock_count",
            )
            if key in validation
        }

        return {
            "name": f"Stock {code}",
            "current": round(current_price, 2),
            "target": round(target_price, 2),
            "stop_loss": round(stop_loss, 2),
            "signal": signal,
            "confidence": round(float(buy_probability) * 100, 1), 
            "confidence_basis": confidence_basis,
            "model_label": model_label,
            "model_path": ACTIVE_MODEL_PATH,
            "model_validation": validation_summary,
            "data_as_of": data_as_of.isoformat(),
            "data_age_days": int(data_age_days),
            "history_sessions": int(len(df)),
            "financial_period": financial_period,
            "buy_threshold": round(buy_threshold * 100, 1),
            "strong_buy_threshold": round(strong_buy_threshold * 100, 1),
            "est_return": est_return,
            "eps": float(round(latest_eps_ttm, 2)),
            "vix": float(round(current_vix, 2)),
            "chart": {
                "dates": df['trade_date'].dt.strftime('%Y-%m-%d').tail(50).tolist(),
                "prices": [float(x) for x in df['close'].tail(50).tolist()],
                "rsi": [float(x) for x in df['rsi'].tail(50).fillna(50).tolist()]
            }
        }
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return None

# --- MARKET SCREENER (Matches Daily Hunter) ---
def run_market_scan(filter_type='RSI_OVERSOLD'):
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        res = cursor.fetchone()
        latest_date = res[0]
        if not latest_date: return []

        df = pd.read_sql(f"SELECT sc_code, sc_name, close, volume FROM daily_prices WHERE trade_date = '{latest_date}' AND close > 10 ORDER BY volume DESC LIMIT 500", conn)
        results = []
        for _, row in df.iterrows():
            try:
                code = row['sc_code']
                df_hist = pd.read_sql(f"SELECT close, volume FROM daily_prices WHERE sc_code = {code} ORDER BY trade_date DESC LIMIT 200", conn)
                if len(df_hist) < 50: continue
                closes = df_hist['close'].iloc[::-1]
                
                # Simple Calcs for Screener
                rsi = RSIIndicator(close=closes, window=14).rsi().iloc[-1]
                
                match = False
                if filter_type == 'RSI_OVERSOLD' and rsi < 35: match = True
                elif filter_type == 'BULLISH_MOMENTUM' and 60 < rsi < 80: match = True
                
                if match: results.append({"code": int(code), "name": row['sc_name'], "price": row['close'], "metric": round(rsi, 1), "reason": filter_type})
            except: continue
        conn.close()
        return results
    except: 
        conn.close()
        return []

# --- DB UPDATER: REVERSE SCAN + NEW UDiFF MAPPING ---

def run_db_update_logic():
    conn = get_db_connection()
    if not conn: return ["Error: DB Connection failed"]

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
            res = cursor.fetchone()
            last_db_date = res[0] if res else None
    except Exception as e:
        return [f"Error reading latest database date: {str(e)[:120]}"]
    finally:
        conn.close()
    
    today = datetime.now().date()
    if last_db_date is None:
        scan_start = today - timedelta(days=14)
    elif (today - last_db_date).days <= 30:
        # Recheck a short overlap for corrections and scan forward to today.
        # The previous one-year scan retried every exchange holiday on every
        # run and made routine daily updates needlessly slow.
        scan_start = max(last_db_date - timedelta(days=7), today - timedelta(days=14))
    else:
        # If the database is genuinely behind, continue catch-up from the day
        # after its latest stored session rather than skipping the missing span.
        scan_start = last_db_date + timedelta(days=1)

    conn = get_db_connection()
    if not conn:
        return ["Error: DB connection failed while checking missing trade dates"]
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT calendar_day::date
                FROM generate_series(%s::date, %s::date, interval '1 day') AS dates(calendar_day)
                WHERE EXTRACT(ISODOW FROM calendar_day) < 6
                ORDER BY calendar_day DESC
            """, (scan_start, today))
            dates_to_check = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        return [f"Error finding missing trade dates: {str(e)[:120]}"]
    finally:
        conn.close()

    if not dates_to_check:
        return ["✅ No missing weekdays in the recent update window."]

    logs = [
        f"ℹ️ Refreshing {len(dates_to_check)} BSE weekdays from {scan_start} through {today} "
        f"(latest stored date: {last_db_date or 'none'})."
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx',
        'Accept': 'text/csv,application/octet-stream,application/zip,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    })
    consecutive_html_days = 0

    for current_date in dates_to_check:
        d_str_full = current_date.strftime("%Y%m%d") # 20260114
        
        urls = [f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{d_str_full}_F_0000.CSV"]

        day_df = None
        html_response_seen = False
        stop_for_access = False
        time.sleep(random.uniform(2, 3)) 
        
        for url in urls:
            try:
                r = session.get(url, timeout=(10, 30))
                if r.status_code == 404:
                    continue
                if r.status_code in (401, 403, 429):
                    logs.append(f"⛔ BSE returned HTTP {r.status_code} for {d_str_full}; stopping the update.")
                    stop_for_access = True
                    break
                if r.status_code != 200:
                    logs.append(f"⚠️ BSE returned HTTP {r.status_code} for {d_str_full}")
                    continue

                content_type = r.headers.get('Content-Type', '').lower()
                body_start = r.content.lstrip()[:32].lower()
                is_html = ('text/html' in content_type or 'application/xhtml+xml' in content_type
                           or body_start.startswith(b'<!doctype html') or body_start.startswith(b'<html'))
                if is_html:
                    html_response_seen = True
                    logs.append(f"⚠️ BSE returned an HTML page instead of a data file for {d_str_full}")
                    continue

                try:
                    is_zip = 'zip' in content_type or r.content.startswith(b'PK') or url.upper().endswith('.ZIP')
                    if is_zip:
                        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
                            csv_files = [name for name in archive.namelist() if not name.endswith('/')]
                            if not csv_files:
                                raise ValueError("ZIP contains no files")
                            with archive.open(csv_files[0]) as csv_file:
                                df = pd.read_csv(csv_file)
                    else:
                        df = pd.read_csv(io.BytesIO(r.content))
                except Exception as e:
                    logs.append(f"⚠️ Could not parse BSE file for {d_str_full}: {str(e)[:100]}")
                    continue

                df.columns = [str(column).upper().strip() for column in df.columns]
                rename_map = {
                    'SC_CODE': 'sc_code', 'SC_NAME': 'sc_name',
                    'OPEN': 'open', 'HIGH': 'high', 'LOW': 'low', 'CLOSE': 'close',
                    'NO_OF_SHRES': 'volume', 'TTLTRADGVOL': 'volume',
                    'NET_TURNOV': 'turnover', 'DELIV_PER': 'delivery_pct',
                    'FININSTRMID': 'sc_code', 'FININSTRMNM': 'sc_name',
                    'OPNPRIC': 'open', 'HGHPRIC': 'high', 'LWPRIC': 'low',
                    'CLSPRIC': 'close'
                }
                for source_column, target_column in rename_map.items():
                    if source_column in df.columns and target_column not in df.columns:
                        df = df.rename(columns={source_column: target_column})
                if 'delivery_pct' not in df.columns:
                    df['delivery_pct'] = 0

                required = ['sc_code', 'sc_name', 'open', 'high', 'low', 'close', 'volume', 'delivery_pct']
                missing_columns = [column for column in required if column not in df.columns]
                if missing_columns:
                    logs.append(f"⚠️ BSE columns missing for {d_str_full}: {', '.join(missing_columns)}")
                    continue

                numeric_columns = ['sc_code', 'open', 'high', 'low', 'close', 'volume', 'delivery_pct']
                for column in numeric_columns:
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                df = df.dropna(subset=['sc_code', 'sc_name', 'open', 'high', 'low', 'close', 'volume'])
                if df.empty:
                    logs.append(f"⚠️ BSE file had no usable equity rows for {d_str_full}")
                    continue

                df['sc_code'] = df['sc_code'].astype('int64')
                df['volume'] = df['volume'].astype('int64')
                df['delivery_pct'] = df['delivery_pct'].fillna(0)
                day_df = df[['sc_code', 'sc_name', 'open', 'high', 'low', 'close', 'volume', 'delivery_pct']].copy()
                break
            except Exception as e:
                logs.append(f"⚠️ BSE request failed for {d_str_full}: {str(e)[:100]}")
                continue

        if stop_for_access:
            break

        if day_df is None:
            logs.append(f"➖ Checked {d_str_full} (No Data)")
            if html_response_seen:
                consecutive_html_days += 1
                if consecutive_html_days >= 3:
                    logs.append("⛔ BSE returned HTML instead of BhavCopy files for 3 consecutive dates; stopped the update.")
                    break
            else:
                consecutive_html_days = 0
            continue

        consecutive_html_days = 0
        data_values = [
            (int(code), str(name), float(open_price), float(high_price), float(low_price),
             float(close_price), int(volume), float(delivery_pct), current_date)
            for code, name, open_price, high_price, low_price, close_price, volume, delivery_pct
            in day_df.itertuples(index=False, name=None)
        ]
        insert_sql = """
            INSERT INTO daily_prices
                (sc_code, sc_name, open, high, low, close, volume, delivery_pct, trade_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, sc_code) DO UPDATE SET
                sc_name = EXCLUDED.sc_name,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                delivery_pct = EXCLUDED.delivery_pct;
        """
        write_conn = get_db_connection()
        if not write_conn:
            logs.append(f"❌ Database connection failed while saving {d_str_full}; stopped the update.")
            break
        try:
            with write_conn.cursor() as write_cursor:
                write_cursor.executemany(insert_sql, data_values)
            write_conn.commit()
            logs.append(f"✅ Downloaded: {d_str_full} ({len(data_values)} rows)")
        except Exception as e:
            write_conn.rollback()
            logs.append(f"❌ Database write failed for {d_str_full}: {str(e)[:120]}; stopped the update.")
            break
        finally:
            write_conn.close()

    session.close()
    return logs
