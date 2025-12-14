from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE job_application ADD COLUMN resume_url VARCHAR(500)"))
            print("Successfully added 'resume_url' column to 'job_application' table.")
        except Exception as e:
            print(f"Error (column might already exist): {e}")
            
        conn.commit()