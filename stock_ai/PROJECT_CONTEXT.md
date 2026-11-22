# 🚀 StockAi: Quantum Hedge Fund OS (v5.0)
**System Architecture & Developer Context**

## 1. Project Overview
StockAi is a professional-grade algorithmic trading system for the Indian Stock Market (BSE/NSE). It has evolved into a fully autonomous **"Quant Fusion" Hedge Fund OS** (v5.0). Unlike previous versions that relied solely on Technical Analysis, v5.0 integrates **Macro-Economics** (VIX, USD/INR) and **Fundamentals** (EPS, PE Ratio) into a unified **XGBoost Prediction Engine**. The system runs 24/7, scanning 5,000+ stocks to generate high-precision "Strong Buy" signals based on Probability Scores (>75%).

## 2. Technical Stack
* **Core Language:** Python 3.11
* **Web Server:** Flask + Flask-SocketIO (Async Threading)
* **Database:** PostgreSQL (Port 5433)
* **AI/ML:** **XGBoost** (Primary) / Gradient Boosting (Fallback) + Scikit-Learn
* **Data Sources:** * **Live:** Yahoo Finance (Real-Time API)
    * **Historical:** BSE Bhavcopy (UDiFF 2026 Format) via "Reverse Scan" Engine
* **Frontend:** HTML5, TailwindCSS (Dark/Glassmorphism Theme), Chart.js
* **Automation:** APScheduler (Background Jobs), Multiprocessing (Parallel CPU Scanning)

---

## 3. Database Schema (PostgreSQL)
*Database: `stock_market`*

### A. `daily_prices` (Technical Data)
*Historical OHLCV data for 5,000+ stocks.*
| Column | Type | Description |
| :--- | :--- | :--- |
| `sc_code` | BIGINT | BSE Code (e.g., 500325) |
| `sc_name` | TEXT | Company Name |
| `trade_date` | DATE | Trading Date |
| `close`, `volume` | DECIMAL | Price & Volume |
| `delivery_pct` | DECIMAL | **Smart Money** (% taken as delivery) |

### B. `quarterly_financials` (Fundamental Data)
*Earnings reports to filter "Junk" stocks.*
| Column | Type | Description |
| :--- | :--- | :--- |
| `sc_code` | BIGINT | Stock Code |
| `period` | DATE | Quarter End Date |
| `net_profit` | NUMERIC | Net Profit (Rs.) |
| `eps` | DECIMAL | Earnings Per Share (Used for PE Ratio) |

### C. `daily_signals` (AI Hunter Results)
*Stores high-confidence buy signals found by the Auto-Scanner.*
| Column | Type | Description |
| :--- | :--- | :--- |
| `signal_date` | DATE | Date of Signal |
| `sc_code` | BIGINT | Stock Code |
| `signal_type` | TEXT | e.g., "STRONG BUY 🚀" |
| `confidence` | DECIMAL | **True Probability** (75%+) |
| `target_price` | DECIMAL | 5-Day Prediction |

### D. `macro_indicators` (Market Weather)
*New in v5.0: Stores context for the AI.*
| Column | Type | Description |
| :--- | :--- | :--- |
| `trade_date` | DATE | Date |
| `india_vix` | DECIMAL | Market Fear Index |
| `usd_inr` | DECIMAL | Currency Strength |

---

## 4. Core System Components

### 🧠 `ai_engine.py` (The Brain)
* **Quant Fusion Logic:** Combines Technicals (RSI, Vol Shock) + Macro (VIX) + Fundamentals (PE Ratio).
* **Smart Downloader (v2026):**
    * Uses **"Reverse Scan"** (Today → Past) to bypass BSE 404 Firewalls.
    * Supports new **UDiFF Format** (`FinInstrmId`, `OpnPric`) mapping.
    * Implements **"Human Mode"** with session persistence and randomized delays.
* **Signal Precision:** Uses `predict_proba()` to filter signals. Only triggers if Confidence > 75%.

### 🏹 `daily_hunter.py` (The Scanner)
* **Parallel Processing:** Uses `multiprocessing.Pool` to scan 5,000 stocks in <10 mins.
* **Type Safety:** Explicitly sanitizes NumPy types (`float32`) to standard Python `float` to prevent DB crashes.
* **Logic:** Saves stocks to `daily_signals` only if the AI model is "High Conviction".

### 🎓 `train_model.py` (The Teacher)
* **Algorithm:** **XGBoost Classifier** (with Auto-Fallback to Sklearn Gradient Boosting).
* **Strategy:** "Quant Fusion" - Trains on a merged dataset of Price, VIX, and EPS.
* **Sanitization:** Automatically handles Infinity (`inf`) values and missing data during training.

### 💼 `portfolio_manager.py` (The Ledger)
* **Logic:** Handles `add_trade()` and `close_trade()`.
* **P&L:** Calculates live Profit/Loss by comparing `buy_price` vs. Real-Time Yahoo Price.

### ⏱️ `scheduler_core.py` (The Autopilot)
* **9:00 AM:** Updates Macro Data (VIX, Oil).
* **6:30 PM:** Trigger BSE "Reverse Scan" Downloader.
* **7:00 PM:** Runs AI Hunter (XGBoost Inference).
* **Console:** Streams logs to the web UI via SocketIO.

---

## 5. AI Architecture (v5.0 Quant Fusion)

The AI no longer looks at a stock in isolation. It evaluates the "Three Pillars":

1.  **Technical (Price Action):**
    * **Volume Shock:** Is institutional money entering?
    * **RSI/Bollinger:** Is it oversold?
    * **Trend:** Is it above the 50-day SMA?

2.  **Fundamental (Value):**
    * **PE Ratio:** Is the stock cheap relative to earnings? (Derived from `quarterly_financials`).
    * **EPS Growth:** Is the company growing?

3.  **Macro (Context):**
    * **India VIX:** Is the market in "Panic Mode"? (If VIX > 25, signals are suppressed).
    * **USD/INR:** Currency trend impact.

**Decision Logic:**
* Probability < 60% → **HOLD ⚪**
* Probability 60-74% → **BUY 🟢** (Weak Signal)
* Probability ≥ 75% → **STRONG BUY 🚀** (High Conviction)

---

## 6. How to Run
1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    brew install libomp  # Required for XGBoost on Mac
    ```
2.  **Start System:**
    ```bash
    SOURCEPOINT_SSO_REQUIRED=false python3 app.py
    ```
    *(Runs on Port 5001)*
3.  **Access:** `http://127.0.0.1:5001`

The standalone command above is for local development. The SourcePoint deployment keeps SSO required and only exposes Stock AI through its role-checked gateway.
