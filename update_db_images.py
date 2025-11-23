# update_db_images.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # Create the new ProductImage table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS product_image (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL,
                    image_url VARCHAR(500) NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES product (id)
                )
            """))
            print("Successfully created 'product_image' table.")
        except Exception as e:
            print(f"Error creating table: {e}")
            
        conn.commit()