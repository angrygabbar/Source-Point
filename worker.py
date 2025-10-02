# Source Point/worker.py
from app import app, check_completed_tests
from apscheduler.schedulers.blocking import BlockingScheduler
import time

scheduler = BlockingScheduler()
# Misfire grace time ensures a missed job will still run if it's not too late
scheduler.add_job(check_completed_tests, 'interval', minutes=15, misfire_grace_time=60)

print("Worker started, scheduling jobs...")

# The app context is needed for the database connection
with app.app_context():
    scheduler.start()