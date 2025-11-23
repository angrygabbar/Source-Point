# update_db_product_details.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add Brand
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN brand VARCHAR(100)"))
            print("Added 'brand' column.")
        except Exception as e:
            print(f"Skipped brand: {e}")

        # Add MRP (Market Price for discount display)
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN mrp FLOAT"))
            print("Added 'mrp' column.")
        except Exception as e:
            print(f"Skipped mrp: {e}")

        # Add Warranty
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN warranty VARCHAR(200)"))
            print("Added 'warranty' column.")
        except Exception as e:
            print(f"Skipped warranty: {e}")

        # Add Return Policy
        try:
            conn.execute(text("ALTER TABLE product ADD COLUMN return_policy VARCHAR(200)"))
            print("Added 'return_policy' column.")
        except Exception as e:
            print(f"Skipped return_policy: {e}")
            
        conn.commit()
        print("Database schema updated with new product details.")