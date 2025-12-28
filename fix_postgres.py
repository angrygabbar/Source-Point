import os
from dotenv import load_dotenv

# 1. Force load .env before importing app
# This ensures DATABASE_URL is available so we don't fall back to SQLite
load_dotenv()

from sqlalchemy import text
from app import app, db

def fix_postgres_db():
    print("--- Starting PostgreSQL Fix ---")
    
    # Check what DB we are connecting to
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' in db_uri:
        print(f"CRITICAL WARNING: Config is still pointing to SQLite: {db_uri}")
        print("Please ensure your .env file has DATABASE_URL set.")
        return
    else:
        print("Connected to PostgreSQL.")

    with app.app_context():
        # Use isolation_level="AUTOCOMMIT" to allow structural changes
        with db.engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # --- 1. Fix 'order' table columns ---
            # "order" is a reserved keyword, so we quote it: "order"
            print("Fixing 'order' table columns...")
            columns_to_add = [
                ("shipping_street", "VARCHAR(200)"),
                ("shipping_city", "VARCHAR(100)"),
                ("shipping_state", "VARCHAR(100)"),
                ("shipping_zip", "VARCHAR(20)"),
                ("shipping_country", "VARCHAR(100)"),
                ("billing_address", "TEXT")
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    # Check existence
                    check_sql = text(f"SELECT 1 FROM information_schema.columns WHERE table_name='order' AND column_name='{col_name}'")
                    if conn.execute(check_sql).scalar():
                        print(f" - [SKIP] {col_name} already exists.")
                    else:
                        sql = text(f'ALTER TABLE "order" ADD COLUMN {col_name} {col_type}')
                        conn.execute(sql)
                        print(f" - [OK] Added {col_name}")
                except Exception as e:
                    print(f" - [ERROR] adding {col_name}: {e}")

            # --- 2. Fix Data Types (Float -> Numeric) ---
            print("Updating monetary columns to Numeric...")
            type_changes = [
                ("product", "price"),
                ("product", "mrp"),
                ("order", "total_amount"),
                ("invoice", "subtotal"),
                ("invoice", "tax"),
                ("invoice", "total_amount"),
                ("project", "budget"),
                ("transaction", "amount"),
            ]

            for table, col in type_changes:
                try:
                    table_ref = f'"{table}"' if table == "order" else table
                    sql = text(f'ALTER TABLE {table_ref} ALTER COLUMN {col} TYPE NUMERIC(10, 2) USING {col}::numeric')
                    conn.execute(sql)
                    print(f" - [OK] Updated {table}.{col}")
                except Exception as e:
                    print(f" - [WARN] Issue with {table}.{col}: {e}")

    print("\nPostgreSQL Fix Complete.")

if __name__ == "__main__":
    fix_postgres_db()