import base64
import hashlib
import hmac
import json
import time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from config import DEBUG_MODE, SECRET_KEY, SOURCEPOINT_SSO_REQUIRED, SOURCEPOINT_SSO_SECRET
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import subprocess
import sys
import ai_engine
import research_data
import scheduler_core
import portfolio_manager
import threading
import importlib

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def _decode_base64url(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _valid_sourcepoint_token(authorization):
    secret = SOURCEPOINT_SSO_SECRET
    if not secret or len(secret.encode("utf-8")) < 32:
        app.logger.error("SOURCEPOINT_SSO_SECRET must contain at least 32 bytes")
        return False

    if not authorization.startswith("Bearer "):
        return False

    try:
        token = authorization[7:]
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected_signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected_signature, _decode_base64url(encoded_signature)):
            raise ValueError("invalid signature")

        header = json.loads(_decode_base64url(encoded_header))
        payload = json.loads(_decode_base64url(encoded_payload))
        now = int(time.time())
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
        if (
            header.get("alg") != "HS256"
            or payload.get("iss") != "sourcepoint"
            or payload.get("aud") != "stock-ai"
            or payload.get("role") not in {"admin", "developer"}
            or not payload.get("sourcepoint_user_id")
            or issued_at > now + 30
            or expires_at <= now
            or expires_at - issued_at > 120
        ):
            raise ValueError("invalid claims")
    except (KeyError, TypeError, ValueError):
        return False

    return True


@app.before_request
def require_sourcepoint_token():
    """Require a short-lived SourcePoint token on every app route."""
    if request.endpoint == 'health' or not SOURCEPOINT_SSO_REQUIRED:
        return None
    if not SOURCEPOINT_SSO_SECRET or len(SOURCEPOINT_SSO_SECRET.encode("utf-8")) < 32:
        app.logger.error("SOURCEPOINT_SSO_SECRET must contain at least 32 bytes")
        return jsonify({"error": "Stock AI sign-in is not configured."}), 503
    if not _valid_sourcepoint_token(request.headers.get("Authorization", "")):
        return jsonify({"error": "Sign in through SourcePoint to continue."}), 401
    return None


@socketio.on('connect')
def authorize_socket_connection():
    """Apply the same gateway check to Socket.IO polling, which bypasses Flask hooks."""
    if not SOURCEPOINT_SSO_REQUIRED:
        return None
    if not _valid_sourcepoint_token(request.headers.get("Authorization", "")):
        return False

# Initialize Scheduler
sys_logger = scheduler_core.start_scheduler(socketio)
_training_lock = threading.Lock()
_training_running = False

# --- PAGE ROUTES ---
@app.route('/health', strict_slashes=False)
def health():
    return jsonify({"status": "ok"})


@app.route('/', strict_slashes=False)
def landing():
    # Landing Page (Sales Pitch)
    return render_template('landing.html')

@app.route('/dashboard', strict_slashes=False)
def dashboard():
    # The Main App (moved from /)
    status = ai_engine.get_market_status()
    signals = []
    try:
        conn = ai_engine.get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT to_regclass('public.daily_signals')")
            if cur.fetchone()[0]:
                q = """
                    SELECT sc_name, signal_type, confidence, target_price, sc_code, stop_loss 
                    FROM daily_signals 
                    WHERE signal_date = CURRENT_DATE 
                    ORDER BY confidence DESC 
                    LIMIT 10
                """
                cur.execute(q)
                signals = cur.fetchall()
            conn.close()
    except: pass
    return render_template('dashboard.html', status=status, signals=signals)

@app.route('/portfolio', strict_slashes=False)
def portfolio():
    holdings = portfolio_manager.get_portfolio_status()
    
    total_pnl = sum([h['pnl'] for h in holdings])
    total_invested = sum([h['buy_price'] * h['qty'] for h in holdings])
    total_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    summary = {
        "pnl": round(total_pnl, 2),
        "pct": round(total_pct, 2),
        "invested": round(total_invested, 2),
        "color": "text-green-400" if total_pnl >= 0 else "text-red-400"
    }
    return render_template('portfolio.html', holdings=holdings, summary=summary)

@app.route('/analysis', strict_slashes=False)
def analysis(): return render_template('analysis.html')

@app.route('/screener', strict_slashes=False)
def screener(): return render_template('screener.html')

@app.route('/admin', strict_slashes=False)
def admin(): return render_template('admin.html')

# --- API ROUTES ---
@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.json
    return jsonify(ai_engine.run_ai_prediction(data.get('code')))

@app.route('/api/research/<int:code>', methods=['GET'])
def api_stock_research(code):
    try:
        payload = research_data.get_local_research(code, request.args.get('range', '1y'))
        if payload is None:
            return jsonify({"error": "No BSE price history found for this code."}), 404
        return jsonify(payload)
    except Exception as exc:
        app.logger.exception("Detailed stock research failed for %s", code)
        return jsonify({"error": "Detailed stock research is temporarily unavailable."}), 500

@app.route('/api/research/<int:code>/external', methods=['GET'])
def api_external_stock_research(code):
    refresh = request.args.get('refresh', '').lower() in {'1', 'true', 'yes'}
    return jsonify(research_data.get_external_research(code, refresh=refresh))

@app.route('/api/live_price', methods=['POST'])
def api_live_price():
    data = request.json
    return jsonify(ai_engine.get_live_quote(data.get('code')))

@app.route('/api/market_indices', methods=['GET'])
def api_indices():
    return jsonify(ai_engine.get_market_indices())

@app.route('/api/scan_market', methods=['GET'])
def api_scan():
    filter_type = request.args.get('filter', 'RSI_OVERSOLD')
    return jsonify(ai_engine.run_market_scan(filter_type))

@app.route('/api/market_status', methods=['GET'])
def api_market_status():
    return jsonify(ai_engine.get_market_status())

@app.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('q', '')
    if len(query) < 2: return jsonify([])
    return jsonify(ai_engine.search_assets(query))

# --- TRADING ROUTES ---
@app.route('/api/buy_stock', methods=['POST'])
def api_buy():
    data = request.json
    qty = data.get('qty', 10)
    sl = data.get('stop_loss', 0)
    return jsonify(portfolio_manager.add_trade(data['code'], data['name'], data['price'], qty, sl))

@app.route('/api/sell_stock', methods=['POST'])
def api_sell():
    data = request.json
    return jsonify(portfolio_manager.close_trade(data['id']))

# --- SYSTEM TRIGGERS ---
@app.route('/api/trigger_update', methods=['POST'])
def trigger_update():
    def run_task():
        sys_logger.log("⚡ Manual Update Triggered...")
        logs = ai_engine.run_db_update_logic()
        for l in logs: sys_logger.log(l)
        sys_logger.log("⚡ Update Finished.")
    threading.Thread(target=run_task).start()
    return jsonify({"status": "Started"})

@app.route('/api/trigger_hunter', methods=['POST'])
def trigger_hunter():
    def run_task():
        sys_logger.log("⚡ Manual Hunter Triggered...")
        try:
            import daily_hunter
            importlib.reload(daily_hunter)
            daily_hunter.run_hunter_parallel()
            sys_logger.log("⚡ Hunter Finished.")
        except Exception as e:
            sys_logger.log(f"Hunter Error: {e}")
    threading.Thread(target=run_task).start()
    return jsonify({"status": "Started"})

# --- UPDATED: TRAINING TRIGGER ---
@app.route('/api/trigger_training', methods=['POST'])
def trigger_training():
    global _training_running
    with _training_lock:
        if _training_running:
            return jsonify({"status": "Already running"}), 409
        _training_running = True

    def run_training_process():
        global _training_running
        sys_logger.log("🧠 Manual Training Triggered...")
        try:
            process = subprocess.Popen(
                [sys.executable, "-u", "training_process.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            result = None
            for line in process.stdout:
                message = line.rstrip()
                if message.startswith("TRAINING_RESULT="):
                    try:
                        result = json.loads(message.split("=", 1)[1])
                    except json.JSONDecodeError as exc:
                        sys_logger.log(f"Could not read training result: {exc}")
                elif message:
                    sys_logger.log(message)
            exit_code = process.wait()
            if exit_code:
                sys_logger.log(
                    f"❌ Isolated training process exited with code {exit_code}; "
                    "the active model was left unchanged."
                )
                return
            if result and result.get("promoted"):
                if ai_engine.reload_global_model():
                    sys_logger.log("✅ Validated model promoted and loaded for new predictions.")
                else:
                    sys_logger.log("⚠️ Model passed validation but could not be loaded.")
            else:
                sys_logger.log("ℹ️ No new model was promoted; the active model remains unchanged.")
        except Exception as e:
            sys_logger.log(f"❌ Training CRASHED: {str(e)}")
        finally:
            with _training_lock:
                _training_running = False

    threading.Thread(target=run_training_process, daemon=True).start()
    return jsonify({"status": "Started"}), 202

if __name__ == '__main__':
    socketio.run(app, debug=DEBUG_MODE, port=5001, host='0.0.0.0', allow_unsafe_werkzeug=True)
