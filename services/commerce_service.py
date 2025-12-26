import time
from extensions import db
from models.commerce import Product, Order, OrderItem, Cart, CartItem

class CommerceService:
    @staticmethod
    def add_to_cart(user_id, product_id):
        product = Product.query.get(product_id)
        if not product:
            return False, "Product not found."
        if product.stock < 1:
            return False, "Product is out of stock."

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit() # Commit to get cart.id

        item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if item:
            item.quantity += 1
        else:
            item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            db.session.add(item)
        
        db.session.commit()
        return True, f"{product.name} added to cart!"

    @staticmethod
    def process_checkout(user_id, shipping_address, billing_address):
        """
        Atomic Checkout Process.
        Either EVERYTHING succeeds (Order created, Stock deducted, Cart cleared),
        or NOTHING happens.
        """
        try:
            cart = Cart.query.filter_by(user_id=user_id).first()
            if not cart or not cart.items:
                return None, "Your cart is empty."

            total_amount = 0
            order_items = []
            
            # 1. Validation & Calculation loop
            for item in cart.items:
                product = Product.query.get(item.product_id)
                
                # Race Condition Check: Ensure stock exists NOW
                if product.stock < item.quantity:
                    return None, f"Insufficient stock for {product.name}. Only {product.stock} left."
                
                total_amount += product.price * item.quantity
                
                # 2. Update Inventory (In Memory)
                product.stock -= item.quantity
                
                # 3. Prepare Order Item
                order_items.append(OrderItem(
                    product_name=product.name, 
                    quantity=item.quantity, 
                    price_at_purchase=product.price
                ))

            # 4. Create Order
            order_number = f"ORD-{int(time.time())}-{user_id}"
            new_order = Order(
                order_number=order_number, 
                user_id=user_id, 
                total_amount=total_amount,
                shipping_address=shipping_address, 
                billing_address=billing_address, 
                status='Order Placed'
            )
            db.session.add(new_order)
            db.session.flush() # Generate ID without committing

            # 5. Link Items
            for oi in order_items:
                oi.order_id = new_order.id
                db.session.add(oi)
            
            # 6. Clear Cart
            db.session.delete(cart)

            # 7. COMMIT TRANSACTION
            db.session.commit()
            return new_order, "Order placed successfully!"

        except Exception as e:
            db.session.rollback() # CRITICAL: Undo everything if error
            print(f"Checkout Error: {e}")
            return None, "An error occurred during checkout. Please try again."