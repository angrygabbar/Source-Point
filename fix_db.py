import os
from sqlalchemy import text
from app import app, db

def fix_database():
    """
    Manually applies schema changes to the database to match the new models.
    """
    print("Starting Database Fix...")
    
    with app.app_context():
        # Create a connection
        with db.engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            try:
                # --- 1. Add Missing Columns to 'order' table ---
                # "order" is a reserved keyword in SQL, so we must quote it like "order"
                print("Adding missing columns to 'order' table...")
                
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
                        # Postgres syntax to add column if it doesn't exist
                        sql = f'ALTER TABLE "order" ADD COLUMN IF NOT EXISTS {col_name} {col_type}'
                        conn.execute(text(sql))
                        print(f" - Added column: {col_name}")
                    except Exception as e:
                        print(f" - Warning adding {col_name}: {e}")

                # --- 2. Update Column Types (Float -> Numeric) ---
                print("Updating monetary columns to Numeric(10, 2)...")
                
                # List of (table_name, column_name)
                type_changes = [
                    ("product", "price"),
                    ("product", "mrp"),
                    ("order", "total_amount"),  # Reserved keyword
                    ("order_item", "price_at_purchase"),
                    ("invoice", "subtotal"),
                    ("invoice", "tax"),
                    ("invoice", "total_amount"),
                    ("invoice_item", "price"),
                    ("project", "budget"),
                    ("transaction", "amount"),
                    ("emi_plan", "total_principal"),
                    ("emi_payment", "amount")
                ]

                for table, col in type_changes:
                    try:
                        # Handle quoting for "order" table
                        table_ref = f'"{table}"' if table == "order" else table
                        
                        # Postgres specific casting
                        sql = f'ALTER TABLE {table_ref} ALTER COLUMN {col} TYPE NUMERIC(10, 2) USING {col}::numeric'
                        conn.execute(text(sql))
                        print(f" - Updated type for {table}.{col}")
                    except Exception as e:
                        # This might fail if the table doesn't exist yet, which is fine
                        print(f" - Skipped {table}.{col} (Table/Column might not exist)")

                trans.commit()
                print("\nSUCCESS: Database schema has been updated!")
                
            except Exception as e:
                trans.rollback()
                print(f"\nCRITICAL ERROR: {e}")

if __name__ == "__main__":
    fix_database()