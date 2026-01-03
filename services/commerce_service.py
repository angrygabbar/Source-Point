import time
from datetime import datetime
from extensions import db
from models.commerce import Product, Order, OrderItem, Cart, CartItem
from models.auth import User
from utils import send_email
import traceback
from sqlalchemy.orm import joinedload
from sqlalchemy import update

class CommerceService:
    @staticmethod
    def get_cart_details(user_id):
        """
        Fetches cart items with product details in a SINGLE query (Optimized).
        Returns a tuple: (list_of_item_dicts, total_amount, cart_object)
        """
        # Eager load 'items' and then 'product' for each item to avoid N+1 queries
        cart = Cart.query.options(
            joinedload(Cart.items).joinedload(CartItem.product)
        ).filter_by(user_id=user_id).first()

        cart_items_data = []
        total_amount = 0

        if cart and cart.items:
            for item in cart.items:
                if item.product:
                    subtotal = item.product.price * item.quantity
                    total_amount += subtotal
                    cart_items_data.append({
                        'id': item.id,
                        'product': item.product,
                        'quantity': item.quantity,
                        'subtotal': subtotal
                    })
        
        return cart_items_data, total_amount, cart

    @staticmethod
    def add_to_cart(user_id, product_id):
        product = Product.query.get(product_id)
        if not product:
            return False, "Product not found."
        
        # Check stock before adding
        if product.stock < 1:
            return False, "Product is out of stock."

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()

        item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if item:
            # Optional: Check if adding 1 more exceeds stock
            if item.quantity + 1 > product.stock:
                return False, f"Only {product.stock} items available."
            item.quantity += 1
        else:
            item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            db.session.add(item)
        
        db.session.commit()
        return True, f"{product.name} added to cart!"

    @staticmethod
    def remove_item(user_id, item_id):
        """Removes an item from the cart safely."""
        item = CartItem.query.get(item_id)
        if not item:
            return False, "Item not found."
        
        if item.cart.user_id != user_id:
            return False, "Unauthorized action."
            
        db.session.delete(item)
        db.session.commit()
        return True, "Item removed."

    @staticmethod
    def process_checkout(user_id, shipping_address, billing_address):
        """
        Atomic Checkout Process with Optimistic Locking.
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return None, "User not found."

            # Fetch Cart with Items & Products eagerly
            cart = Cart.query.options(
                joinedload(Cart.items).joinedload(CartItem.product)
            ).filter_by(user_id=user_id).first()

            if not cart or not cart.items:
                return None, "Your cart is empty."

            total_amount = 0
            order_items = []
            
            # --- ATOMIC STOCK CHECK & DEDUCTION ---
            for item in cart.items:
                product = item.product
                
                # OPTIMISTIC LOCKING: 
                # Update stock ONLY if stock >= quantity requested.
                # This prevents race conditions where 2 users buy the last item.
                stmt = (
                    update(Product)
                    .where(Product.id == product.id)
                    .where(Product.stock >= item.quantity)
                    .values(stock=Product.stock - item.quantity)
                    .execution_options(synchronize_session=False)
                )
                
                result = db.session.execute(stmt)
                
                if result.rowcount == 0:
                    # Rolling back because one item failed
                    db.session.rollback()
                    return None, f"Insufficient stock for {product.name}. Transaction cancelled."

                # Calculate cost (using the price at this exact moment)
                total_amount += product.price * item.quantity
                
                order_items.append(OrderItem(
                    product_name=product.name, 
                    quantity=item.quantity, 
                    price_at_purchase=product.price
                ))

            # --- CREATE ORDER ---
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
            db.session.flush() # Flush to get new_order.id

            # Link Items
            for oi in order_items:
                oi.order_id = new_order.id
                db.session.add(oi)
            
            # Clear Cart
            db.session.delete(cart)

            # FINAL COMMIT
            db.session.commit()

            # --- SEND NOTIFICATION (Async) ---
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