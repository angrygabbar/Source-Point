# update_db_activity_log.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    details TEXT,
                    ip_address VARCHAR(50),
                    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
                    FOREIGN KEY (user_id) REFERENCES "user" (id)
                )
            """))
            print("Successfully created 'activity_log' table.")
        except Exception as e:
            print(f"Error creating table: {e}")
            
        conn.commit()