# update_db_order.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE \"order\" ADD COLUMN billing_address TEXT"))
            print("Added 'billing_address' column to 'order' table.")
        except Exception as e:
            print(f"Error (column might exist): {e}")
            
        # Optionally update default status logic if needed, mainly handled in python default
        conn.commit()
        print("Database schema updated.")