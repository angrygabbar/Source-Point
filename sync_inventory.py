from app import app
from extensions import db
from models import User, Product, SellerInventory

def sync_existing_products_to_inventory():
    """
    Loops through all Products. 
    If a Product is owned by a Seller (seller_id is not None),
    ensure there is a corresponding SellerInventory record.
    """
    with app.app_context():
        print("--- Starting Inventory Sync ---")
        
        # 1. Fetch all products that are 'owned' by a specific seller
        seller_products = Product.query.filter(Product.seller_id.isnot(None)).all()
        
        print(f"Found {len(seller_products)} products owned by sellers.")
        
        added_count = 0
        updated_count = 0
        
        for product in seller_products:
            # Check if an inventory record already exists
            inventory_record = SellerInventory.query.filter_by(
                seller_id=product.seller_id, 
                product_id=product.id
            ).first()
            
            if inventory_record:
                # OPTIONAL: Sync stock count if needed (e.g., if Product.stock is the master truth)
                # inventory_record.stock = product.stock 
                # updated_count += 1
                pass
            else:
                # Create missing inventory record
                print(f"Creating inventory for Seller {product.seller_id} - Product: {product.name}")
                new_inventory = SellerInventory(
                    seller_id=product.seller_id,
                    product_id=product.id,
                    stock=product.stock  # Initialize with the product's current stock
                )
                db.session.add(new_inventory)
                added_count += 1
        
        db.session.commit()
        print("--------------------------------")
        print(f"Sync Complete.")
        print(f"New Allocations Created: {added_count}")
        print("--------------------------------")

if __name__ == "__main__":
    sync_existing_products_to_inventory()