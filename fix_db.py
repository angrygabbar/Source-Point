from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking database columns...")
    
    with db.engine.connect() as conn:
        transaction = conn.begin()
        try:
            # 1. Add seller_id to 'product' table if missing
            try:
                conn.execute(text('ALTER TABLE product ADD COLUMN seller_id INTEGER REFERENCES "user" (id)'))
                print("SUCCESS: Added 'seller_id' to 'product' table.")
            except Exception as e:
                if 'already exists' in str(e):
                    print("INFO: 'seller_id' already exists in 'product' table.")
                else:
                    print(f"ERROR updating product table: {e}")

            # 2. Add seller_id to 'order' table if missing
            # Note: "order" is often a reserved keyword, so we quote it just in case, 
            # though SQLAlchemy usually handles table naming.
            try:
                conn.execute(text('ALTER TABLE "order" ADD COLUMN seller_id INTEGER REFERENCES "user" (id)'))
                print("SUCCESS: Added 'seller_id' to 'order' table.")
            except Exception as e:
                # Try without quotes if the above fails (depends on exact table name casing in PG)
                try:
                    conn.execute(text('ALTER TABLE order ADD COLUMN seller_id INTEGER REFERENCES "user" (id)'))
                    print("SUCCESS: Added 'seller_id' to 'order' table.")
                except Exception as inner_e:
                    if 'already exists' in str(inner_e) or 'already exists' in str(e):
                        print("INFO: 'seller_id' already exists in 'order' table.")
                    else:
                        print(f"ERROR updating order table: {inner_e}")

            transaction.commit()
            print("Database update routine completed.")
            
        except Exception as e:
            transaction.rollback()
            print(f"CRITICAL ERROR during transaction: {e}")