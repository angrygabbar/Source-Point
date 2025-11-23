# update_db.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add description column
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN description TEXT"))
            print("Added 'description' column.")
        except Exception as e:
            print(f"Could not add 'description': {e}")

        # Add image_url column
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN image_url VARCHAR(500)"))
            print("Added 'image_url' column.")
        except Exception as e:
            print(f"Could not add 'image_url': {e}")
            
        conn.commit()
        print("Database schema updated successfully.")