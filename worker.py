# Source Point/worker.py
from app import app, check_completed_tests
from apscheduler.schedulers.blocking import BlockingScheduler
from models import EMIPayment, User
from utils import send_email
from datetime import datetime, timedelta
import time

scheduler = BlockingScheduler()

def process_emi_reminders():
    with app.app_context():
        today = datetime.utcnow().date()
        
        pending_payments = EMIPayment.query.filter(
            EMIPayment.status == 'Pending',
            EMIPayment.reminder_sent == False
        ).all()

        count = 0
        for payment in pending_payments:
            days_remaining = (payment.due_date - today).days
            
            if days_remaining <= payment.reminder_days_before and days_remaining >= 0:
                borrower = payment.plan.borrower
                lender = payment.plan.lender
                
                # 1. Notify Borrower (To Pay)
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

                # 2. Notify Lender (To Expect Payment)
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
                
                payment.reminder_sent = True
                db.session.commit()
                count += 1
                
        if count > 0:
            print(f"[Worker] Sent reminders for {count} payments.")

# Misfire grace time ensures a missed job will still run if it's not too late
scheduler.add_job(check_completed_tests, 'interval', minutes=15, misfire_grace_time=60)
scheduler.add_job(process_emi_reminders, 'interval', hours=24) # Check once daily

print("Worker started, scheduling jobs...")

# The app context is needed for the database connection
with app.app_context():
    scheduler.start()