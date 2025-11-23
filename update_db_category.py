# update_db_category.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # This SQL command adds the missing column
            conn.execute(text("ALTER TABLE product ADD COLUMN category VARCHAR(50)"))
            print("Successfully added 'category' column to 'product' table.")
        except Exception as e:
            print(f"Error: {e}")
            print("The column might already exist or there is a connection issue.")
            
        conn.commit()