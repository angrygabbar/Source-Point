import time
from datetime import datetime
from extensions import db
from models.commerce import Product, Order, OrderItem, Cart, CartItem
from models.auth import User
from utils import send_email
import traceback

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
            db.session.commit()

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
        Atomic Checkout Process with Email Notification.
        """
        try:
            # 1. Fetch User
            user = User.query.get(user_id)
            if not user:
                return None, "User not found."

            cart = Cart.query.filter_by(user_id=user_id).first()
            if not cart or not cart.items:
                return None, "Your cart is empty."

            total_amount = 0
            order_items = []
            
            # 2. Validation & Calculation
            for item in cart.items:
                product = Product.query.get(item.product_id)
                if product.stock < item.quantity:
                    return None, f"Insufficient stock for {product.name}. Only {product.stock} left."
                
                total_amount += product.price * item.quantity
                product.stock -= item.quantity
                
                order_items.append(OrderItem(
                    product_name=product.name, 
                    quantity=item.quantity, 
                    price_at_purchase=product.price
                ))

            # 3. Create Order
            order_number = f"ORD-{int(time.time())}-{user_id}"
            
            # --- FIX: Insert into 'shipping_address' (the column we just restored) ---
            new_order = Order(
                order_number=order_number, 
                user_id=user_id, 
                total_amount=total_amount,
                shipping_address=shipping_address,  # Corrected column mapping
                billing_address=billing_address, 
                status='Order Placed'
            )
            db.session.add(new_order)
            db.session.flush()

            # 4. Link Items
            for oi in order_items:
                oi.order_id = new_order.id
                db.session.add(oi)
            
            # 5. Clear Cart
            db.session.delete(cart)

            # 6. COMMIT TRANSACTION
            db.session.commit()

            # 7. SEND NOTIFICATION
            try:
                send_email(
                    to=user.email,
                    subject=f"Order Confirmation: {new_order.order_number}",
                    template="mail/order_status_update.html",
                    buyer_name=user.username,
                    order_number=new_order.order_number,
                    status="Order Placed",
                    order_date=datetime.utcnow().strftime('%B %d, %Y'),
                    total_amount=new_order.total_amount,
                    shipping_address=shipping_address,
                    now=datetime.utcnow()
                )
            except Exception as e:
                print(f"Failed to send order email: {e}")
                traceback.print_exc()

            return new_order, "Order placed successfully! Confirmation email sent."

        except Exception as e:
            db.session.rollback()
            print(f"Checkout Error: {e}")
            traceback.print_exc()
            return None, "An error occurred during checkout. Please try again."