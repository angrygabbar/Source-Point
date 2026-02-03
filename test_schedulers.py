import sys
import os
import logging

# 1. Setup Logging to see output in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app import create_app
from worker import send_invoice_reminders_task, process_emi_reminders_task

def run_tests():
    # 3. Create App Context
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*50)
        print("🚀 STARTING MANUAL SCHEDULER TEST")
        print("="*50)

        # --- TEST 1: INVOICE REMINDERS ---
        print("\n[1/2] Testing Invoice Reminders (9 AM/5 PM Task)...")
        try:
            # This runs the logic directly (synchronously)
            send_invoice_reminders_task()
            print("✅ Invoice Task execution finished.")
        except Exception as e:
            print(f"❌ Invoice Task Failed: {e}")

        # --- TEST 2: EMI REMINDERS ---
        print("\n[2/2] Testing EMI Reminders (Daily 10 AM Task)...")
        try:
            # This checks the DB and queues tasks to Redis
            process_emi_reminders_task()
            print("✅ EMI Dispatcher execution finished.")
            print("   (Note: Actual emails are queued to the worker. Check worker logs.)")
        except Exception as e:
            print(f"❌ EMI Task Failed: {e}")

        print("\n" + "="*50)
        print("🎉 TESTS COMPLETED")
        print("="*50 + "\n")

if __name__ == "__main__":
    run_tests()