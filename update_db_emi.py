from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # 1. Create the Parent Plan Table
            print("Creating 'emi_plan' table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS emi_plan (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(150) NOT NULL,
                    total_principal FLOAT NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES "user" (id)
                )
            """))
            print("Successfully created 'emi_plan' table.")

            # 2. Create the Installments Table
            print("Creating 'emi_payment' table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS emi_payment (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER NOT NULL,
                    due_date DATE NOT NULL,
                    amount FLOAT NOT NULL,
                    description VARCHAR(200),
                    status VARCHAR(20) DEFAULT 'Pending',
                    reminder_days_before INTEGER DEFAULT 3,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    payment_date TIMESTAMP WITHOUT TIME ZONE,
                    FOREIGN KEY (plan_id) REFERENCES emi_plan (id) ON DELETE CASCADE
                )
            """))
            print("Successfully created 'emi_payment' table.")
            
            conn.commit()
            print("Database schema updated successfully.")
            
        except Exception as e:
            print(f"Error updating schema: {e}")
            # Optional: Rollback is automatic on exception context exit, but explicit helps debugging
            # conn.rollback()