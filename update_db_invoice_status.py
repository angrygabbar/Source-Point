from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # Add status column with default value 'Unpaid'
            conn.execute(text("ALTER TABLE invoice ADD COLUMN status VARCHAR(20) DEFAULT 'Unpaid'"))
            print("Added 'status' column to 'invoice' table.")
            
            # Ensure existing records are marked Unpaid
            conn.execute(text("UPDATE invoice SET status = 'Unpaid' WHERE status IS NULL"))
        except Exception as e:
            print(f"Error (column might already exist): {e}")
            
        conn.commit()
        print("Database schema updated.")