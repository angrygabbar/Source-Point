from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # Drop old tables to reset structure
            conn.execute(text("DROP TABLE IF EXISTS emi_payment CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS emi_plan CASCADE"))
            print("Dropped old tables.")

            # Create EMI Plan
            conn.execute(text("""
                CREATE TABLE emi_plan (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(150) NOT NULL,
                    total_principal FLOAT NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
                    is_active BOOLEAN DEFAULT TRUE,
                    borrower_id INTEGER NOT NULL,
                    lender_id INTEGER NOT NULL,
                    FOREIGN KEY (borrower_id) REFERENCES "user" (id),
                    FOREIGN KEY (lender_id) REFERENCES "user" (id)
                )
            """))
            print("Created new 'emi_plan' table.")

            # Create Payments Table with Installment Number
            conn.execute(text("""
                CREATE TABLE emi_payment (
                    id SERIAL PRIMARY KEY,
                    plan_id INTEGER NOT NULL,
                    installment_number INTEGER NOT NULL DEFAULT 1,
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
            print("Created 'emi_payment' table with installment_number.")
            
            conn.commit()
            print("Database structure updated successfully.")
        except Exception as e:
            print(f"Error: {e}")