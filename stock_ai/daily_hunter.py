import psycopg2
import pandas as pd
from ai_engine import run_ai_prediction
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count

# CONFIGURATION
try:
    from config import DB_CONN_STR
    DB_CONFIG = DB_CONN_STR
except ImportError:
    DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5433"

def get_db_connection():
    try:
        return psycopg2.connect(DB_CONFIG)
    except: return None

def get_active_stocks():
    conn = get_db_connection()
    if not conn:
        print("❌ DB Connection Failed in get_active_stocks")
        return []
    
    cursor = conn.cursor()
    print("--- 🔍 Selecting Prime Stocks for Scanning ---")
    
    q = """
        SELECT sc_code, sc_name
        FROM daily_prices
        WHERE trade_date = (SELECT MAX(trade_date) FROM daily_prices)
          AND close > 20
          AND volume > 10000
        ORDER BY close * volume DESC NULLS LAST
        LIMIT 500
    """
    cursor.execute(q)
    results = cursor.fetchall()
    conn.close()
    return results

def save_signal(data):
    try:
        conn = get_db_connection()
        if not conn: return "❌ DB Error during save"
        
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # ADDED stop_loss to the INSERT
        q = """
            INSERT INTO daily_signals 
            (signal_date, sc_code, sc_name, signal_type, confidence, current_price, target_price, stop_loss)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (signal_date, sc_code) DO UPDATE 
            SET confidence = EXCLUDED.confidence,
                target_price = EXCLUDED.target_price,
                stop_loss = EXCLUDED.stop_loss
        """
        cursor.execute(q, (
            today, data['code'], data['name'], data['signal'], 
            data['confidence'], data['current'], data['target'], data['stop_loss']
        ))
        conn.commit()
        conn.close()
        return f"✅ SIGNAL SAVED: {data['name']} [{data['signal']}] Target: {data['target']} SL: {data['stop_loss']}"
    except Exception as e:
        return f"Error saving {data['name']}: {e}"

def analyze_single_stock(stock_tuple):
    """
    Worker function to analyze one stock.
    Returns result dict if BUY found, else None.
    """
    code, name = stock_tuple
    try:
        # Run AI Analysis
        pred = run_ai_prediction(code)
        
        # Check if it's a high-quality BUY signal
        if (
            pred
            and pred.get("confidence_basis") == "calibrated_model"
            and "BUY" in pred["signal"]
        ):
            
            # Extract Stop Loss (Default to 5% below if missing)
            sl = pred.get('stop_loss', pred['current'] * 0.95)
            
            return {
                'code': code,
                'name': name,
                'signal': str(pred['signal']),
                'confidence': float(pred['confidence']),
                'current': float(pred['current']),
                'target': float(pred['target']),
                'stop_loss': float(sl) # <--- CAPTURE STOP LOSS
            }
    except Exception as e:
        pass
    return None

def run_hunter_parallel():
    start_time = time.time()
    stocks = get_active_stocks()
    total_stocks = len(stocks)
    
    if total_stocks == 0:
        print("⚠️ No stocks found. Check your database data.")
        return

    # Use all available CPU cores
    # Leave capacity for PostgreSQL and the web process; each candidate now
    # needs only its recent indicator window, but concurrent DB scans add up.
    cores = min(4, max(1, cpu_count() // 2))
    print(f"[i] Found {total_stocks} active candidates.")
    print(f"[⚡] Engaging {cores} CPU Cores for Parallel Scanning...")
    
    hits = 0
    processed = 0
    
    # Create a Pool of workers
    # chunksize=20 optimizes passing data to processes
    with Pool(processes=cores) as pool:
        for result in pool.imap_unordered(analyze_single_stock, stocks, chunksize=20):
            processed += 1
            
            if result:
                msg = save_signal(result)
                print(f"\n{msg}") 
                hits += 1
                
            # Progress bar every 50 stocks
            if processed % 50 == 0:
                pct = round((processed / total_stocks) * 100, 1)
                elapsed = round(time.time() - start_time)
                print(f"\r    🚀 Progress: {pct}% ({processed}/{total_stocks}) | Found: {hits} | Time: {elapsed}s", end="")

    print("\n" + "="*50)
    print(f"🎉 HUNT COMPLETE in {round(time.time() - start_time)} seconds.")
    print(f"🎯 Total High-Quality Signals Found: {hits}")

if __name__ == "__main__":
    run_hunter_parallel()
