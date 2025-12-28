from sqlalchemy import text
from app import app, db

def fix_sqlite_db():
    print("Detected SQLite. Applying SQLite-specific fixes...")
    
    with app.app_context():
        with db.engine.connect() as conn:
            # SQLite does not support "ALTER COLUMN TYPE"
            # We will only ADD the missing columns so the app stops crashing.
            
            # 1. Get existing columns in "order" table
            print("Checking 'order' table...")
            try:
                # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
                result = conn.execute(text('PRAGMA table_info("order")'))
                existing_columns = {row[1] for row in result}
            except Exception as e:
                print(f"Error reading table info: {e}")
                return

            # 2. Define columns to add
            columns_to_add = [
                ("shipping_street", "TEXT"),
                ("shipping_city", "TEXT"),
                ("shipping_state", "TEXT"),
                ("shipping_zip", "TEXT"),
                ("shipping_country", "TEXT"),
                ("billing_address", "TEXT")
            ]

            # 3. Add them if missing
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    try:
                        # SQLite syntax for adding columns
                        sql = text(f'ALTER TABLE "order" ADD COLUMN {col_name} {col_type}')
                        conn.execute(sql)
                        print(f" [OK] Added column: {col_name}")
                    except Exception as e:
                        print(f" [ERROR] Could not add {col_name}: {e}")
                else:
                    print(f" [SKIP] {col_name} already exists.")

            conn.commit()
            print("\nSQLite Fix Complete. (Note: Type conversion to Numeric is skipped for SQLite as it is loosely typed)")

if __name__ == "__main__":
    fix_sqlite_db()