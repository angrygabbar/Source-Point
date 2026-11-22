import joblib
import pandas as pd
import psycopg2
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from sklearn.ensemble import GradientBoostingRegressor
try:
    from config import DB_CONN_STR
except ImportError:
    DB_CONN_STR = "dbname=stock_market user=admin host=localhost port=5433"

MODEL_FILE = "model_v1.pkl"

def train_model():
    print("⏳ Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_CONN_STR)
    
    # 1. Fetch Data
    # We select top 300 stocks to ensure high quality training data
    print("⏳ Fetching 3 years of data for top 300 stocks...")
    q = """
    SELECT * FROM daily_prices 
    WHERE sc_code IN (
        SELECT sc_code FROM daily_prices 
        GROUP BY sc_code 
        HAVING COUNT(*) > 500
        ORDER BY AVG(volume) DESC
        LIMIT 300
    )
    AND trade_date > CURRENT_DATE - INTERVAL '3 years'
    ORDER BY sc_code, trade_date ASC
    """
    
    df = pd.read_sql(q, conn)
    conn.close()
    
    if df.empty:
        print("❌ Error: No data found. Migration might have failed or table is empty.")
        return

    print(f"📊 Processing {len(df)} rows...")

    # 2. Feature Engineering
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values(['sc_code', 'trade_date'])
    
    # Indicators
    df['rsi'] = df.groupby('sc_code')['close'].transform(lambda x: RSIIndicator(close=x, window=14).rsi())
    df['sma_50'] = df.groupby('sc_code')['close'].transform(lambda x: SMAIndicator(close=x, window=50).sma_indicator())
    df['macd'] = df.groupby('sc_code')['close'].transform(lambda x: MACD(close=x).macd_diff())
    df['pct_change'] = df.groupby('sc_code')['close'].pct_change()
    
    # 3. LAG FEATURES (Predict Tomorrow using Today's Data)
    # We shift features forward by 1 so "Row X" contains "Row X-1" data
    # This prevents the AI from "peeking" at the close price of the day it is trying to predict
    df['rsi_lag1'] = df.groupby('sc_code')['rsi'].shift(1)
    df['macd_lag1'] = df.groupby('sc_code')['macd'].shift(1)
    df['pct_lag1'] = df.groupby('sc_code')['pct_change'].shift(1)
    
    # 4. Target (Return 5 days from now)
    df['future_close'] = df.groupby('sc_code')['close'].shift(-5)
    df['target'] = (df['future_close'] / df['close']) - 1
    
    df_clean = df.dropna()
    print(f"🧠 Training on {len(df_clean)} samples...")
    
    # Train
    features = ['rsi_lag1', 'macd_lag1', 'pct_lag1']
    model = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
    model.fit(df_clean[features], df_clean['target'])
    
    joblib.dump(model, MODEL_FILE)
    print(f"✅ Model trained and saved to {MODEL_FILE}")

if __name__ == "__main__":
    train_model()