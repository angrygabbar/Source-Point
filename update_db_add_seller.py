from app import create_app, db
from sqlalchemy import text

app = create_app()

def add_seller_id_column():
    with app.app_context():
        try:
            # Check if column exists first to avoid errors
            with db.engine.connect() as conn:
                # This raw SQL adds the column and sets up the foreign key relationship
                conn.execute(text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES "user"(id)'))
                conn.commit()
                print("✅ Successfully added 'seller_id' column to 'order' table.")
        except Exception as e:
            print(f"❌ Error updating database: {e}")

if __name__ == "__main__":
    add_seller_id_column()