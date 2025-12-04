from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # Change product.image_url to TEXT to support Base64 strings
            conn.execute(text("ALTER TABLE product ALTER COLUMN image_url TYPE TEXT"))
            print("Altered 'product.image_url' to TEXT.")
            
            # Also update the child table product_image just in case
            conn.execute(text("ALTER TABLE product_image ALTER COLUMN image_url TYPE TEXT"))
            print("Altered 'product_image.image_url' to TEXT.")
            
        except Exception as e:
            print(f"Error updating schema: {e}")
            
        conn.commit()
        print("Database schema updated successfully.")