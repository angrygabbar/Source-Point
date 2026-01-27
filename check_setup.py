import sys
from app import create_app
from extensions import db, cache
from models.auth import User
from sqlalchemy import text

app = create_app()

def check_environment():
    print("--- DIAGNOSTIC START ---")
    with app.app_context():
        # 1. Check Database Connection
        try:
            db.session.execute(text('SELECT 1'))
            print("[PASS] Database Connection")
        except Exception as e:
            print(f"[FAIL] Database Connection: {e}")
            return

        # 2. Check User Table
        try:
            user_count = User.query.count()
            print(f"[PASS] User Table Exists (Count: {user_count})")
        except Exception as e:
            print(f"[FAIL] User Table Missing or Schema Error: {e}")
            print("       Run 'flask db upgrade' or 'flask init-db'")
            return

        # 3. Check Redis/Cache
        try:
            cache.set('test_key', 'test_value')
            val = cache.get('test_key')
            if val == 'test_value':
                print("[PASS] Redis/Cache Connection")
            else:
                print("[FAIL] Redis Connected but Value Mismatch")
        except Exception as e:
            print(f"[WARN] Redis Connection Failed: {e}")
            print("       Login may be slow, but shouldn't crash with the new app.py.")

    print("--- DIAGNOSTIC COMPLETE ---")

if __name__ == "__main__":
    check_environment()