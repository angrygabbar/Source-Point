import psycopg2
from yahooquery import Ticker
import pandas as pd
import time
import warnings
import math

# Suppress warnings
warnings.filterwarnings("ignore")

# CONFIGURATION
DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5433"

# --- 🛑 RESUME CONFIGURATION ---
START_FROM_BATCH_INDEX = 4639
# ------------------------------

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONFIG)
        return conn
    except: return None

def get_active_equity_codes():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT DISTINCT sc_code 
        FROM daily_prices 
        WHERE sc_code BETWEEN 500000 AND 599999 
        AND trade_date >= '2024-01-01'
    """
    cursor.execute(query)
    codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sorted(codes)

def safe_float(val):
    if pd.isna(val) or val is None or math.isinf(float(val)):
        return 0
    return float(val)

def fetch_financials_batch():
    print(f"--- 💰 Resuming Financial Loader from Index {START_FROM_BATCH_INDEX} ---")
    
    all_codes = get_active_equity_codes()
    total_stocks = len(all_codes)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    BATCH_SIZE = 20
    
    for i in range(START_FROM_BATCH_INDEX, total_stocks, BATCH_SIZE):
        batch_codes = all_codes[i : i + BATCH_SIZE]
        yahoo_symbols = [f"{code}.BO" for code in batch_codes]
        
        print(f"\n[Batch {i}/{total_stocks}] Fetching...", end=" ", flush=True)
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                tickers = Ticker(yahoo_symbols, asynchronous=True)
                df_fin = tickers.income_statement(frequency='q', trailing=False)
                
                # --- BUG FIX STARTS HERE ---
                # 1. Handle String responses (Errors like "Too many requests")
                if isinstance(df_fin, str):
                    print(f"❌ Yahoo returned text error: '{df_fin}'")
                    # If it's a specific block, maybe wait longer
                    if "Too Many Requests" in df_fin:
                         time.sleep(60)
                    break 
                
                # 2. Handle Dict responses (Usually means no data found)
                if isinstance(df_fin, dict):
                    print(f"❌ No Data (Dict returned).")
                    break

                # 3. Handle Empty DataFrame
                if df_fin.empty:
                    print(f"❌ DataFrame Empty.")
                    break
                # --- BUG FIX ENDS HERE ---
                    
                count = 0
                df_fin = df_fin.reset_index()
                
                for index, row in df_fin.iterrows():
                    symbol = row.get('symbol', '')
                    if not symbol.endswith('.BO'): continue
                    
                    sc_code = symbol.replace('.BO', '')
                    period = row.get('asOfDate')
                    
                    rev = safe_float(row.get('TotalRevenue', row.get('OperatingRevenue', 0)))
                    profit = safe_float(row.get('NetIncome', row.get('NetIncomeCommonStockholders', 0)))
                    eps = safe_float(row.get('DilutedEPS', row.get('BasicEPS', 0)))

                    insert_query = """
                    INSERT INTO quarterly_financials (sc_code, period, revenue, net_profit, eps)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sc_code, period) DO UPDATE 
                    SET revenue = EXCLUDED.revenue,
                        net_profit = EXCLUDED.net_profit,
                        eps = EXCLUDED.eps;
                    """
                    cursor.execute(insert_query, (sc_code, period, rev, profit, eps))
                    count += 1
                
                conn.commit()
                print(f"✅ Saved {count} records.")
                time.sleep(2) 
                break 
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                conn.rollback()
                if attempt < max_retries - 1:
                    print("    ⏳ Network/API Error. Waiting 60s...")
                    time.sleep(60)
                else:
                    print("    ❌ Skipping batch after retries.")

    conn.close()
    print("\n🎉 COMPLETE.")

if __name__ == "__main__":
    fetch_financials_batch()