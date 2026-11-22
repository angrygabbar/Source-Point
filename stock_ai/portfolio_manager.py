import psycopg2
import pandas as pd
from datetime import datetime
import ai_engine
from concurrent.futures import ThreadPoolExecutor

# Try to use shared config, else default
try:
    from config import DB_CONN_STR
    DB_CONFIG = DB_CONN_STR
except:
    DB_CONFIG = "dbname=stock_market user=admin host=localhost port=5433"

def get_db_connection():
    try:
        return psycopg2.connect(DB_CONFIG)
    except: return None

# UPDATED: Now supports Stop Loss (sl)
def add_trade(code, name, price, qty, sl=0):
    conn = get_db_connection()
    if not conn: return {"status": "error", "msg": "DB Connection Failed"}
    
    try:
        cursor = conn.cursor()
        
        # Ensure table exists with stop_loss column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY,
                sc_code BIGINT,
                sc_name TEXT,
                buy_date DATE,
                buy_price DECIMAL(10,2),
                quantity INT,
                status TEXT DEFAULT 'OPEN',
                stop_loss DECIMAL(10,2) DEFAULT 0
            );
        """)
        
        # Check if stop_loss column exists (for older tables)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='portfolio' AND column_name='stop_loss'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE portfolio ADD COLUMN stop_loss DECIMAL(10,2) DEFAULT 0")
        
        today = datetime.now().strftime('%Y-%m-%d')
        q = """
            INSERT INTO portfolio (sc_code, sc_name, buy_date, buy_price, quantity, status, stop_loss)
            VALUES (%s, %s, %s, %s, %s, 'OPEN', %s)
        """
        cursor.execute(q, (code, name, price, qty, sl))
        conn.commit()
        return {"status": "success", "msg": f"Bought {qty} shares of {name}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        conn.close()

def close_trade(trade_id):
    conn = get_db_connection()
    if not conn: return {"status": "error", "msg": "DB Connection Failed"}
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE portfolio SET status = 'CLOSED' WHERE id = %s", (trade_id,))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        conn.close()

# --- HELPER FOR PARALLEL FETCHING ---
def fetch_live_price_wrapper(row):
    """Fetches price and merges it back into the row dict"""
    try:
        live_data = ai_engine.get_live_quote(row['sc_code'])
        current_price = live_data['price'] if live_data else row['buy_price']
        
        invested = float(row['buy_price']) * int(row['quantity'])
        current_val = float(current_price) * int(row['quantity'])
        pnl = current_val - invested
        pnl_pct = (pnl / invested) * 100 if invested != 0 else 0
        
        return {
            "id": int(row['id']),
            "code": int(row['sc_code']),
            "name": row['sc_name'],
            "buy_price": float(row['buy_price']),
            "current_price": float(current_price),
            "qty": int(row['quantity']),
            "pnl": float(round(pnl, 2)),
            "pnl_pct": float(round(pnl_pct, 2)),
            "stop_loss": float(row.get('stop_loss', 0) or 0),
            "color": "text-green-400" if pnl >= 0 else "text-red-400"
        }
    except:
        return None

def get_portfolio_status():
    conn = get_db_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT to_regclass('public.portfolio')")
        if cursor.fetchone()[0] is None: return []

        # Read as Dict to easier manipulation
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM portfolio WHERE status = 'OPEN'")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows: return []
        
        # --- PARALLEL EXECUTION (Speed Boost) ---
        # Instead of waiting for one request to finish before starting the next,
        # we launch them all at once.
        portfolio_data = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_live_price_wrapper, rows)
            
        # Collect non-None results
        portfolio_data = [r for r in results if r is not None]
            
        return portfolio_data
    except Exception as e:
        print(f"Portfolio Error: {e}")
        return []