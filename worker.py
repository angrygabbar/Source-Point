# Source Point/worker.py
from app import app, check_completed_tests
from apscheduler.schedulers.blocking import BlockingScheduler
from models import EMIPayment
from utils import send_email
from datetime import datetime
import time

scheduler = BlockingScheduler()
BATCH_SIZE = 100  # Process 100 emails at a time to save RAM

def process_emi_reminders():
    """
    Scalable worker task that processes reminders in batches.
    """
    with app.app_context():
        today = datetime.utcnow().date()
        print(f"[Worker] Starting EMI Check for {today}...")

        processed_count = 0
        
        while True:
            # Fetch a batch of pending reminders
            # We check reminder_sent=False so the list shrinks as we process
            batch = EMIPayment.query.filter(
                EMIPayment.status == 'Pending',
                EMIPayment.reminder_sent == False
            ).limit(BATCH_SIZE).all()

            if not batch:
                break  # No more records to process

            for payment in batch:
                try:
                    days_remaining = (payment.due_date - today).days
                    
                    # Only send if within the reminder window (e.g., 3 days before)
                    if 0 <= days_remaining <= payment.reminder_days_before:
                        borrower = payment.plan.borrower
                        lender = payment.plan.lender
                        
                        # 1. Notify Borrower
                        if borrower and borrower.email:
                            send_email(
                                to=borrower.email,
                                subject=f"Payment Reminder: {payment.description}",
                                template="mail/emi_reminder_borrower.html",
                                user=borrower,
                                lender=lender,
                                payment=payment,
                                days_remaining=days_remaining
                            )

                        # 2. Notify Lender
                        if lender and lender.email:
                            send_email(
                                to=lender.email,
                                subject=f"Incoming Payment Reminder: {payment.description}",
                                template="mail/emi_reminder_lender.html",
                                user=lender,
                                borrower=borrower,
                                payment=payment,
                                days_remaining=days_remaining
                            )
                        
                        # Mark as sent so it doesn't get picked up in the next loop/run
                        payment.reminder_sent = True
                        processed_count += 1
                
                except Exception as e:
                    print(f"[Worker Error] ID {payment.id}: {e}")
                    # Continue to next payment even if one fails

            # Commit the batch
            db.session.commit()
            print(f"[Worker] Batch processed. Total so far: {processed_count}")
            
            # Small sleep to yield CPU if running heavy loads
            time.sleep(0.5)

        if processed_count > 0:
            print(f"[Worker] Job Complete. Sent {processed_count} reminders.")

# Schedule Jobs
# Misfire grace time ensures a missed job will still run if it's not too late
scheduler.add_job(check_completed_tests, 'interval', minutes=15, misfire_grace_time=60)
scheduler.add_job(process_emi_reminders, 'interval', hours=24) # Run once daily

print("Worker started (Batch Mode)...")

if __name__ == "__main__":
    # The app context is needed for the database connection
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass