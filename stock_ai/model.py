import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import logging

try:
    from config import DB_CONN_STR
except ImportError:
    DB_CONN_STR = "dbname=stock_market user=admin host=localhost port=5433"

class StockModel:
    def __init__(self):
        self.conn_str = DB_CONN_STR

    def get_conn(self):
        return psycopg2.connect(self.conn_str)

    def get_latest_trade_date(self):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(trade_date) FROM daily_prices")
                res = cur.fetchone()
                return res[0] if res else None

    def get_market_status(self, date):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sc_name, close, open 
                    FROM daily_prices 
                    WHERE trade_date = %s 
                    ORDER BY (close-open)/open DESC LIMIT 1
                """, (date,))
                g = cur.fetchone()
                
                nifty_val = 0
                try:
                    cur.execute("SELECT nifty50_close FROM macro_indicators WHERE trade_date = %s", (date,))
                    n_res = cur.fetchone()
                    if n_res: nifty_val = float(round(n_res[0], 2))
                except: pass
                
                return {
                    "date": str(date),
                    "top_gainer": g[0] if g else "N/A",
                    "gainer_price": float(g[1]) if g else 0.0,
                    "nifty_level": nifty_val
                }

    def get_top_signals(self, limit=8):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                # Returns Tuples to maintain compatibility with original dashboard templates
                cur.execute("""
                    SELECT sc_name, signal_type, confidence, target_price, sc_code, stop_loss 
                    FROM daily_signals 
                    WHERE signal_date = (SELECT MAX(signal_date) FROM daily_signals) 
                    ORDER BY confidence DESC LIMIT %s
                """, (limit,))
                return cur.fetchall()

    def get_price_history(self, sc_code):
        with self.get_conn() as conn:
            return pd.read_sql("""
                SELECT trade_date, open, high, low, close, volume 
                FROM daily_prices 
                WHERE sc_code = %s 
                ORDER BY trade_date ASC
            """, conn, params=[sc_code])

    def save_ai_signal(self, d):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO daily_signals 
                    (signal_date, sc_code, sc_name, signal_type, confidence, current_price, target_price, stop_loss)
                    VALUES (CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (signal_date, sc_code) 
                    DO UPDATE SET confidence = EXCLUDED.confidence, stop_loss = EXCLUDED.stop_loss
                """, (d['code'], d['name'], d['signal'], d['confidence'], d['current'], d['target'], d.get('stop_loss')))
                conn.commit()

    def get_portfolio_holdings(self):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM portfolio WHERE status = 'OPEN'")
                return cur.fetchall()

    def add_trade(self, code, name, price, qty):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio (sc_code, sc_name, buy_date, buy_price, quantity, status) 
                    VALUES (%s, %s, CURRENT_DATE, %s, %s, 'OPEN')
                """, (code, name, price, qty))
                conn.commit()

    def close_trade(self, tid):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE portfolio SET status = 'CLOSED' WHERE id = %s", (tid,))
                conn.commit()

    def search_assets(self, query, date):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sc_code, sc_name FROM daily_prices 
                    WHERE trade_date = %s AND (sc_name ILIKE %s OR CAST(sc_code AS TEXT) LIKE %s)
                    LIMIT 10
                """, (date, f"%{query}%", f"%{query}%"))
                return [{"code": r[0], "name": r[1]} for r in cur.fetchall()]