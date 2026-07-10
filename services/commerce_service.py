import time
from datetime import datetime
from extensions import db
from models.commerce import Product, Order, OrderItem, Cart, CartItem, SellerInventory
from models.auth import User
from utils import send_email
import traceback
from sqlalchemy.orm import joinedload
from sqlalchemy import update
from enums import OrderStatus
# --- FIX: Correct Import Path for StaleDataError ---
from sqlalchemy.orm.exc import StaleDataError 

ORDER_STATUS_CHOICES = [
    (OrderStatus.PLACED.value, "Placed"),
    (OrderStatus.ACCEPTED.value, "Accepted"),
    (OrderStatus.PAYMENT_RECEIVED.value, "Payment Received"),
    (OrderStatus.PACKED.value, "Packed"),
    (OrderStatus.DISPATCHED.value, "Dispatched"),
    (OrderStatus.SHIPPED.value, "Shipped"),
    (OrderStatus.IN_TRANSIT.value, "In Transit"),
    (OrderStatus.OUT_FOR_DELIVERY.value, "Out for Delivery"),
    (OrderStatus.DELIVERED.value, "Delivered"),
    (OrderStatus.CANCELLED.value, "Order Cancelled"),
    (OrderStatus.RETURNED.value, "Returned"),
]

ORDER_STATUS_VALUES = {status for status, _ in ORDER_STATUS_CHOICES}
ORDER_STATUS_ALIASES = {
    "Pending": OrderStatus.PLACED.value,
    "Placed": OrderStatus.PLACED.value,
    "Accepted": OrderStatus.ACCEPTED.value,
    "Confirmed": OrderStatus.ACCEPTED.value,
    "Order Accepted": OrderStatus.ACCEPTED.value,
    "Order Dispatched": OrderStatus.DISPATCHED.value,
    "Dispatched": OrderStatus.DISPATCHED.value,
    "Intransit": OrderStatus.IN_TRANSIT.value,
    "In Transit": OrderStatus.IN_TRANSIT.value,
    "Out for delivery": OrderStatus.OUT_FOR_DELIVERY.value,
    "Out For Delivery": OrderStatus.OUT_FOR_DELIVERY.value,
    "Delivered": OrderStatus.DELIVERED.value,
    "Cancelled": OrderStatus.CANCELLED.value,
    "Order Rejected": OrderStatus.CANCELLED.value,
    "Rejected": OrderStatus.CANCELLED.value,
}
RESTOCK_ORDER_STATUSES = {
    OrderStatus.CANCELLED.value,
    OrderStatus.RETURNED.value,
}
PLACED_ORDER_STATUSES = (
    OrderStatus.PLACED.value,
    "Pending",
    "Placed",
)
BUYER_CANCELLABLE_STATUSES = {
    OrderStatus.PLACED.value,
    OrderStatus.ACCEPTED.value,
    OrderStatus.PAYMENT_RECEIVED.value,
    OrderStatus.PACKED.value,
}

class CommerceService:
    order_status_choices = ORDER_STATUS_CHOICES
    placed_status_values = PLACED_ORDER_STATUSES

    @staticmethod
    def normalize_order_status(status):
        if not status:
            return None
        status = str(status).strip()
        return ORDER_STATUS_ALIASES.get(status, status)

    @staticmethod
    def is_restock_status(status):
        return CommerceService.normalize_order_status(status) in RESTOCK_ORDER_STATUSES

    @staticmethod
    def can_buyer_cancel_order(order):
        return CommerceService.normalize_order_status(order.status) in BUYER_CANCELLABLE_STATUSES

    @staticmethod
    def restore_order_inventory(order):
        """
        Adds ordered quantities back to inventory.
        Seller-created orders restore SellerInventory; marketplace/admin orders
        restore Product.stock because that is where stock was deducted.
        """
        restored = []
        missing = []

        for item in order.items:
            restored_item = False

            if order.seller_id:
                inventory_item = db.session.query(SellerInventory)\
                    .join(Product, SellerInventory.product_id == Product.id)\
                    .filter(
                        SellerInventory.seller_id == order.seller_id,
                        Product.name == item.product_name
                    ).first()

                if inventory_item:
                    inventory_item.stock += item.quantity
                    restored.append(f"{item.product_name} x{item.quantity}")
                    restored_item = True

            if not restored_item:
                product_query = Product.query.filter_by(name=item.product_name)
                if order.seller_id:
                    seller_product = product_query.filter_by(seller_id=order.seller_id).first()
                    product = seller_product or Product.query.filter_by(name=item.product_name).first()
                else:
                    product = product_query.first()

                if product:
                    product.stock += item.quantity
                    restored.append(f"{item.product_name} x{item.quantity}")
                    restored_item = True

            if not restored_item:
                missing.append(item.product_name)

        return restored, missing

    @staticmethod
    def transition_order_status(order, new_status):
        normalized_status = CommerceService.normalize_order_status(new_status)
        if normalized_status not in ORDER_STATUS_VALUES:
            return False, f"Invalid order status: {new_status}", [], []

        current_status = CommerceService.normalize_order_status(order.status)
        if CommerceService.is_restock_status(current_status) and normalized_status not in RESTOCK_ORDER_STATUSES:
            return False, "Cancelled or returned orders cannot be reactivated.", [], []

        restored = []
        missing = []
        if normalized_status in RESTOCK_ORDER_STATUSES and current_status not in RESTOCK_ORDER_STATUSES:
            restored, missing = CommerceService.restore_order_inventory(order)

        order.status = normalized_status
        return True, f"Order updated to {normalized_status}.", restored, missing

    @staticmethod
    def get_cart_details(user_id):
        """
        Fetches cart items with product details in a SINGLE query (Optimized).
        Returns a tuple: (list_of_item_dicts, total_amount, cart_object)
        """
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
        
        if product.stock < 1:
            return False, "Product is out of stock."

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()

        item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if item:
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
        Atomic Checkout Process with Retry Logic (Robust).
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 1. Start Transaction
                user = User.query.get(user_id)
                if not user:
                    return None, "User not found."

                cart = Cart.query.options(
                    joinedload(Cart.items).joinedload(CartItem.product)
                ).filter_by(user_id=user_id).first()

                if not cart or not cart.items:
                    return None, "Your cart is empty."

                total_amount = 0
                order_items = []
                
                # 2. Process Items
                for item in cart.items:
                    product = item.product
                    
                    # Optimistic Locking with Atomic Update
                    stmt = (
                        update(Product)
                        .where(Product.id == product.id)
                        .where(Product.stock >= item.quantity)
                        .values(stock=Product.stock - item.quantity)
                        .execution_options(synchronize_session=False)
                    )
                    
                    result = db.session.execute(stmt)
                    
                    if result.rowcount == 0:
                        db.session.rollback()
                        # If we failed but there is stock (just contention), we retry.
                        # If stock is genuinely gone, we stop.
                        db.session.expire(product)
                        if product.stock < item.quantity:
                            return None, f"Insufficient stock for {product.name}. Transaction cancelled."
                        else:
                            raise StaleDataError("Contention detected, retrying...")

                    total_amount += product.price * item.quantity
                    
                    order_items.append(OrderItem(
                        product_name=product.name, 
                        quantity=item.quantity, 
                        price_at_purchase=product.price
                    ))

                # 3. Create Order
                order_number = f"ORD-{int(time.time())}-{user_id}"
                new_order = Order(
                    order_number=order_number, 
                    user_id=user_id, 
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    billing_address=billing_address, 
                    status=OrderStatus.PLACED.value
                )
                db.session.add(new_order)
                db.session.flush()

                for oi in order_items:
                    oi.order_id = new_order.id
                    db.session.add(oi)
                
                db.session.delete(cart)
                db.session.commit()

                # 4. Async Notification
                try:
                    send_email(
                        to=user.email,
                        subject=f"Order Confirmation: {new_order.order_number}",
                        template="mail/order_status_update.html",
                        buyer_name=user.username,
                        order_number=new_order.order_number,
                        status=OrderStatus.PLACED.value,
                        order_date=datetime.utcnow().strftime('%B %d, %Y'),
                        total_amount=new_order.total_amount,
                        shipping_address=shipping_address,
                        now=datetime.utcnow()
                    )
                except Exception as e:
                    print(f"Failed to send order email: {e}")
                    traceback.print_exc()

                return new_order, "Order placed successfully! Confirmation email sent."

            except StaleDataError:
                db.session.rollback()
                if attempt < max_retries - 1:
                    time.sleep(0.2) # Short backoff
                    continue
                return None, "High traffic detected. Please try again."
                
            except Exception as e:
                db.session.rollback()
                print(f"Checkout Error: {e}")
                traceback.print_exc()
                return None, "An error occurred during checkout. Please try again."
        
        return None, "Transaction failed after retries."
