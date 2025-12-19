import os
from flask import Flask
from extensions import db
from sqlalchemy import text

# --- CONFIGURATION ---
# We need to recreate the minimal app context to connect to the DB
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def fix_database():
    """
    Manually adds the missing 'seller_id' columns to the 'product' and 'order' tables.
    """
    print("--- STARTING DATABASE SCHEMA FIX ---")
    
    with app.app_context():
        # Open a connection to the database
        with db.engine.connect() as conn:
            # We use a transaction to ensure safety
            trans = conn.begin()
            try:
                # 1. Fix 'product' table
                print("Checking 'product' table...")
                try:
                    # Attempt to add the column. If it exists, this will fail safely.
                    conn.execute(text('ALTER TABLE product ADD COLUMN seller_id INTEGER REFERENCES "user" (id)'))
                    print("SUCCESS: Added 'seller_id' to 'product' table.")
                except Exception as e:
                    if 'already exists' in str(e):
                        print("INFO: 'seller_id' already exists in 'product' table.")
                    else:
                        print(f"WARNING: Could not update 'product' table. Error: {e}")

                # 2. Fix 'order' table
                # Note: 'order' is a reserved word in SQL, so we must quote it as "order"
                print("Checking 'order' table...")
                try:
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN seller_id INTEGER REFERENCES "user" (id)'))
                    print("SUCCESS: Added 'seller_id' to 'order' table.")
                except Exception as e:
                    if 'already exists' in str(e):
                        print("INFO: 'seller_id' already exists in 'order' table.")
                    else:
                        print(f"WARNING: Could not update 'order' table. Error: {e}")

                trans.commit()
                print("--- DATABASE FIX COMPLETED SUCCESSFULLY ---")
                print("You can now restart your application.")
                
            except Exception as e:
                trans.rollback()
                print(f"CRITICAL ERROR: Transaction failed. Changes rolled back. Error: {e}")

if __name__ == "__main__":
    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL'):
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("Please ensure you run this script in an environment where .env is loaded or variables are set.")
    else:
        fix_database()