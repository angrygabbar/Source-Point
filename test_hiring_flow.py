import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models.auth import User
from models.learning import ProblemStatement
from worker import check_hiring_events_task
from enums import UserRole

def run_test():
    app = create_app()
    with app.app_context():
        print("\n" + "="*50)
        print("🚀 STARTING HIRING SCHEDULER TEST")
        print("="*50)
        
        # --- 1. SETUP TEST DATA ---
        # Ensure we have a problem statement to assign
        problem = ProblemStatement.query.first()
        if not problem:
            print("   [Setup] Creating dummy problem statement...")
            problem = ProblemStatement(title="Test Algorithm", description="Solve X", created_by_id=1)
            db.session.add(problem)
            db.session.commit()
            
        # Find or create a dummy candidate for testing
        candidate_email = "test_candidate_automation@example.com"
        candidate = User.query.filter_by(email=candidate_email).first()
        
        if not candidate:
            print("   [Setup] Creating dummy candidate...")
            candidate = User(
                username="TestCandidateBot", 
                email=candidate_email, 
                password_hash="dummy_hash",
                role=UserRole.CANDIDATE.value,
                is_approved=True
            )
            db.session.add(candidate)
            db.session.commit()

        # --- TEST CASE A: 2-HOUR REMINDER ---
        print("\n[Test 1/2] Verifying '2-Hour Reminder' logic...")
        
        # SCENARIO: Test starts in 1 hour and 50 minutes (Inside the 2-hour window)
        now = datetime.utcnow()
        candidate.assigned_problem = problem
        candidate.test_start_time = now + timedelta(minutes=110) 
        candidate.test_end_time = now + timedelta(hours=3)
        candidate.reminder_sent = False  # Reset flag
        db.session.commit()
        
        print(f"   -> Setup: Test starts at {candidate.test_start_time} (approx 1h 50m from now)")
        print(f"   -> Setup: 'reminder_sent' is currently {candidate.reminder_sent}")
        
        # RUN THE WORKER TASK MANUALLY
        print("   -> Running scheduler task...")
        check_hiring_events_task()
        
        # VERIFY
        db.session.refresh(candidate)
        if candidate.reminder_sent:
            print("   ✅ SUCCESS: Reminder email sent & flag updated to True.")
        else:
            print("   ❌ FAILURE: Reminder flag did not update.")


        # --- TEST CASE B: AUTO-COMPLETION ---
        print("\n[Test 2/2] Verifying 'Auto-Completion' logic...")
        
        # SCENARIO: Test ended 10 minutes ago
        candidate.test_end_time = now - timedelta(minutes=10)
        candidate.test_completed = False # Reset flag
        db.session.commit()
        
        print(f"   -> Setup: Test ended at {candidate.test_end_time} (10 mins ago)")
        print(f"   -> Setup: 'test_completed' is currently {candidate.test_completed}")
        
        # RUN THE WORKER TASK MANUALLY
        print("   -> Running scheduler task...")
        check_hiring_events_task()
        
        # VERIFY
        db.session.refresh(candidate)
        if candidate.test_completed:
            print("   ✅ SUCCESS: Test marked as completed & admin notified.")
        else:
            print("   ❌ FAILURE: Test completion flag did not update.")

        # CLEANUP (Optional)
        # db.session.delete(candidate)
        # db.session.commit()

        print("\n" + "="*50)
        print("🎉 TEST RUN COMPLETE")
        print("="*50 + "\n")

if __name__ == "__main__":
    run_test()