from app import app
from extensions import db, bcrypt
from models import User, Product, SellerInventory

def seed_data():
    with app.app_context():
        print("--- Checking Data Integrity ---")

        # 1. Ensure there is a Seller
        seller = User.query.filter_by(role='seller').first()
        if not seller:
            print("No seller found. Creating 'Test Seller'...")
            hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
            seller = User(username='Test Seller', email='seller@test.com', 
                          password_hash=hashed_pw, role='seller', is_approved=True)
            db.session.add(seller)
            db.session.commit()
        else:
            print(f"Found Seller: {seller.username}")

        # 2. Ensure there is a Product
        product = Product.query.first()
        if not product:
            print("No product found. Creating 'Test Product'...")
            product = Product(product_code='TEST001', name='Test Laptop', stock=50, price=50000.0)
            db.session.add(product)
            db.session.commit()
        
        # 3. Link Product to Seller
        product.seller_id = seller.id
        db.session.commit()
        print(f"Linked '{product.name}' to Seller '{seller.username}'")

        # 4. Create Inventory Record
        inv = SellerInventory.query.filter_by(seller_id=seller.id, product_id=product.id).first()
        if not inv:
            print("Creating Inventory Record...")
            inv = SellerInventory(seller_id=seller.id, product_id=product.id, stock=10)
            db.session.add(inv)
            db.session.commit()
        else:
            print("Inventory record already exists.")

        print("\nSUCCESS! Data seeded. You should now see this in the Admin Panel.")

if __name__ == "__main__":
    seed_data()