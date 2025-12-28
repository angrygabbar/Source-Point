import os
from sqlalchemy import text
from app import app, db

def fix_database():
    print(f"Connecting to database...")
    
    with app.app_context():
        # Use a connection with auto-commit for structural changes
        # (This avoids 'current transaction is aborted' errors)
        with db.engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # --- 1. Add Missing Columns to 'order' table ---
            # We wrap "order" in quotes because it is a reserved SQL keyword
            print("--- Fixing 'order' table columns ---")
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
                    # Check if column exists first to avoid errors
                    check_sql = text(f"SELECT 1 FROM information_schema.columns WHERE table_name='order' AND column_name='{col_name}'")
                    if conn.execute(check_sql).scalar():
                        print(f" [SKIP] Column '{col_name}' already exists.")
                    else:
                        # Add the column
                        sql = text(f'ALTER TABLE "order" ADD COLUMN {col_name} {col_type}')
                        conn.execute(sql)
                        print(f" [OK] Added column: {col_name}")
                except Exception as e:
                    print(f" [ERROR] Failed to add {col_name}: {e}")

            # --- 2. Update Column Types (Float -> Numeric) ---
            print("\n--- Updating Data Types to Numeric ---")
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
                    
                    # Run the type conversion
                    sql = text(f'ALTER TABLE {table_ref} ALTER COLUMN {col} TYPE NUMERIC(10, 2) USING {col}::numeric')
                    conn.execute(sql)
                    print(f" [OK] Updated {table}.{col} to Numeric")
                except Exception as e:
                    print(f" [WARN] Could not update {table}.{col}: {e}")

    print("\nDATABASE FIX COMPLETE.")

if __name__ == "__main__":
    fix_database()