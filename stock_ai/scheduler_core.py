from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import ai_engine
import daily_hunter
import macro_loader
import research_data
import datetime
import threading
import time

# Setup Logger to stream to Website
class WebLogger:
    def __init__(self, socketio):
        self.socketio = socketio

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        print(formatted_msg)
        if self.socketio:
            self.socketio.emit('log_message', {'data': formatted_msg})

def start_scheduler(socketio):
    logger = WebLogger(socketio)
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    
    # --- JOB DEFINITIONS ---

    def run_full_evening_cycle():
        """
        CHAIN REACTION:
        1. Macro Data -> 2. BSE Download -> 3. AI Hunter
        This ensures we never scan old data.
        """
        logger.log("🌙 Starting Evening Sequence...")
        
        # Step 1: Macro data. Keep going if the external macro provider is down;
        # a macro outage should not prevent the BSE end-of-day price refresh.
        try:
            logger.log("Step 1/3: Updating Macro Data...")
            macro_loader.fetch_macro_data()
        except Exception as e:
            logger.log(f"❌ Macro Failed: {e}")

        # Step 2: Prices
        try:
            logger.log("Step 2/3: Downloading BSE Bhavcopy...")
            logs = ai_engine.run_db_update_logic()
            for l in logs: logger.log(l)
        except Exception as e:
            logger.log(f"❌ DB Update Failed: {e}")
            return

        # Step 3: Hunter
        try:
            logger.log("Step 3/3: Releasing the Hunter...")
            # Run in a separate thread to not block the scheduler
            threading.Thread(target=daily_hunter.run_hunter_parallel).start()
            logger.log("🚀 Hunter process started in background.")
        except Exception as e:
            logger.log(f"❌ Hunter Failed: {e}")

    # --- SCHEDULE ---
    
    # 1. Morning Macro Update (9:15 AM - Market Open)
    scheduler.add_job(
        lambda: macro_loader.fetch_macro_data(), 
        trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=15),
        name="Morning Macro",
        id="morning_macro",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )

    # 2. Evening Cycle (Start at 6:45 PM)
    # This runs the full chain defined above
    scheduler.add_job(
        run_full_evening_cycle,
        trigger=CronTrigger(day_of_week='mon-fri', hour=18, minute=45),
        name="Evening Cycle",
        id="evening_market_sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )

    # Refresh profiles and statements already opened by the user. The batch is
    # paced and configurable because Yahoo's public API is unofficial and not
    # intended for bulk market-data redistribution.
    scheduler.add_job(
        lambda: research_data.refresh_cached_research(logger=logger.log),
        trigger=CronTrigger(day_of_week='mon-fri', hour=20, minute=15),
        name="Daily Company Research Refresh",
        id="daily_company_research_refresh",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    
    scheduler.start()
    logger.log("🤖 Scheduler online: macro 09:15, BSE prices 18:45, researched-company refresh 20:15 IST.")
    
    return logger
