from app import create_app, db
from sqlalchemy import text

app = create_app()

def add_seller_id_columns():
    with app.app_context():
        print("Checking database columns...")
        try:
            with db.engine.connect() as conn:
                # --- 1. Fix PRODUCT Table (This fixes your current error) ---
                try:
                    # Start a transaction for the product table update
                    trans = conn.begin()
                    conn.execute(text('ALTER TABLE product ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES "user"(id)'))
                    trans.commit()
                    print("✅ Successfully added 'seller_id' column to 'product' table.")
                except Exception as e:
                    # If it fails (e.g., already exists), we catch it here
                    print(f"⚠️ Note on Product table: {e}")

                # --- 2. Fix ORDER Table (Ensuring this is also correct) ---
                try:
                    # Start a transaction for the order table update
                    trans = conn.begin()
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES "user"(id)'))
                    trans.commit()
                    print("✅ Successfully added 'seller_id' column to 'order' table.")
                except Exception as e:
                    print(f"⚠️ Note on Order table: {e}")
                    
        except Exception as e:
            print(f"❌ Critical Connection Error: {e}")

if __name__ == "__main__":
    add_seller_id_columns()