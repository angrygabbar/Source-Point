import sys
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def fix_message_column():
    print("--- FIXING DATABASE SCHEMA ---")
    with app.app_context():
        try:
            # 1. Check if column exists
            print("[INFO] Checking 'message' table...")
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='message' AND column_name='read'")
            result = db.session.execute(check_sql).fetchone()
            
            if result:
                print("[INFO] Column 'read' already exists. No action needed.")
            else:
                # 2. Add the column if missing
                print("[ACTION] Adding missing column 'read' to 'message' table...")
                # We use double quotes "read" to ensure SQL safety, though Postgres is usually lenient
                alter_sql = text('ALTER TABLE message ADD COLUMN "read" BOOLEAN DEFAULT FALSE')
                db.session.execute(alter_sql)
                db.session.commit()
                print("[SUCCESS] Column added successfully.")
                
        except Exception as e:
            print(f"[ERROR] Failed to update database: {e}")
            db.session.rollback()
            
    print("--- FIX COMPLETE ---")

if __name__ == "__main__":
    fix_message_column()