from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

def fix_database():
    with app.app_context():
        print("--- Checking Database Tables ---")
        
        # 1. Use SQLAlchemy to create any models that don't have tables yet
        try:
            # Importing models ensures SQLAlchemy knows about them
            from models import SellerInventory
            db.create_all()
            print("✅ Executed create_all() to generate missing tables.")
        except Exception as e:
            print(f"⚠️ Error during create_all: {e}")

        # 2. Verification & Manual Fallback
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'seller_inventory' in tables:
            print("✅ VERIFIED: 'seller_inventory' table exists.")
        else:
            print("⚠️ Table still missing. Attempting manual SQL creation...")
            try:
                with db.engine.connect() as conn:
                    trans = conn.begin()
                    # Manual SQL creation for PostgreSQL
                    sql = """
                    CREATE TABLE IF NOT EXISTS seller_inventory (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        stock INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(seller_id) REFERENCES "user" (id),
                        FOREIGN KEY(product_id) REFERENCES product (id)
                    );
                    """
                    conn.execute(text(sql))
                    trans.commit()
                    print("✅ Successfully created 'seller_inventory' table via SQL.")
            except Exception as e:
                print(f"❌ CRITICAL ERROR creating table: {e}")

if __name__ == "__main__":
    fix_database()