import psycopg2
import pandas as pd
from datetime import datetime
try:
    from config import DB_CONN_STR
except ImportError:
    # Fallback if config is missing
    DB_CONN_STR = "dbname=stock_market user=admin host=localhost port=5433"

def init_db():
    """Initializes the PostgreSQL table if it doesn't exist."""
    try:
        conn = psycopg2.connect(DB_CONN_STR)
        cursor = conn.cursor()
        
        # Create Main Price Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            trade_date DATE,
            sc_code BIGINT,
            sc_name TEXT,
            open DECIMAL(10,2),
            high DECIMAL(10,2),
            low DECIMAL(10,2),
            close DECIMAL(10,2),
            volume BIGINT,
            delivery_pct DECIMAL(5,2) DEFAULT 0,
            PRIMARY KEY (trade_date, sc_code)
        );
        ''')
        
        # Create Macro Indicators Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS macro_indicators (
            trade_date DATE PRIMARY KEY,
            india_vix DECIMAL(10,2),
            usd_inr DECIMAL(10,2),
            crude_oil DECIMAL(10,2),
            us_market_close DECIMAL(10,2),
            nifty50_close DECIMAL(10,2)
        );
        ''')

        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS us_market_close DECIMAL(10,2);
        ''')

        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS crude_oil DECIMAL(10,2);
        ''')
        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS nifty50_close DECIMAL(10,2);
        ''')
        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS usd_inr_available DECIMAL(10,2);
        ''')
        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS crude_oil_available DECIMAL(10,2);
        ''')
        cursor.execute('''
        ALTER TABLE macro_indicators
        ADD COLUMN IF NOT EXISTS us_market_close_available DECIMAL(10,2);
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_signals (
            signal_date DATE NOT NULL,
            sc_code BIGINT NOT NULL,
            sc_name TEXT,
            signal_type TEXT,
            confidence DECIMAL(6,2),
            current_price DECIMAL(10,2),
            target_price DECIMAL(10,2),
            stop_loss DECIMAL(10,2),
            PRIMARY KEY (signal_date, sc_code)
        );
        ''')

        # Additive cache for optional company fundamentals fetched on demand.
        # BSE price history and existing financial rows remain untouched.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS external_stock_research_cache (
            sc_code BIGINT PRIMARY KEY,
            provider TEXT NOT NULL DEFAULT 'Yahoo Finance',
            yahoo_symbol TEXT,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB NOT NULL
        );
        ''')

        conn.commit()
        conn.close()
        print(f"[+] PostgreSQL Database initialized successfully.")
    except Exception as e:
        print(f"[-] DB Init Error: {e}")

def save_bhavcopy_to_db(csv_filename, date_obj):
    conn = psycopg2.connect(DB_CONN_STR)
    try:
        df = pd.read_csv(csv_filename)
        # Normalize headers
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Flexible Column Mapping
        rename_map = {
            'SC_CODE': 'sc_code', 'SC_NAME': 'sc_name',
            'OPEN': 'open', 'HIGH': 'high', 'LOW': 'low', 'CLOSE': 'close',
            'NO_OF_SHRES': 'volume', 'NET_TURNOV': 'turnover'
        }
        if 'NO_OF_SHRES' not in df.columns and 'TTLTRADGVOL' in df.columns:
            rename_map['TTLTRADGVOL'] = 'volume'
            
        df.rename(columns=rename_map, inplace=True)
        
        # Fill missing columns
        req_cols = ['sc_code', 'sc_name', 'open', 'high', 'low', 'close', 'volume']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            
        df = df[req_cols].copy()
        df['trade_date'] = date_obj.strftime("%Y-%m-%d")
        df['delivery_pct'] = 0 # Default
        
        # Bulk Insert
        data_values = [tuple(x) for x in df[['sc_code', 'sc_name', 'open', 'high', 'low', 'close', 'volume', 'delivery_pct', 'trade_date']].to_numpy()]
        
        query = """
        INSERT INTO daily_prices (sc_code, sc_name, open, high, low, close, volume, delivery_pct, trade_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (trade_date, sc_code) 
        DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume;
        """
        
        cursor = conn.cursor()
        cursor.executemany(query, data_values)
        conn.commit()
        print(f"[+] Saved {len(data_values)} rows for {date_obj.date()}.")
        
    except Exception as e:
        print(f"[-] Error saving to DB: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
