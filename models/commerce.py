# Source Point/models/commerce.py
from extensions import db
from datetime import datetime
from sqlalchemy import Numeric
from enums import OrderStatus, InvoiceStatus, VoucherOrderStatus

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False, index=True)
    price = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    brand = db.Column(db.String(100), nullable=True)
    mrp = db.Column(Numeric(10, 2), nullable=True) 
    warranty = db.Column(db.String(200), nullable=True)
    return_policy = db.Column(db.String(200), nullable=True)
    
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")

    # --- OPTIMIZATION: Composite Index for Filters ---
    __table_args__ = (
        db.Index('idx_product_category_price', 'category', 'price'),
    )

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False)

class Order(db.Model):
    # This must match your PostgreSQL "order" table exactly
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    
    # Use Enum value
    status = db.Column(db.String(20), default=OrderStatus.PLACED.value, index=True) 
    
    shipping_address = db.Column(db.Text, nullable=False)
    
    # We keep these as nullable=True so they don't cause errors if they exist in DB
    shipping_street = db.Column(db.String(200), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=True)
    shipping_state = db.Column(db.String(100), nullable=True)
    shipping_zip = db.Column(db.String(20), nullable=True)
    shipping_country = db.Column(db.String(100), nullable=True)
    
    billing_address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(Numeric(10, 2), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    product = db.relationship('Product')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    bill_to_address = db.Column(db.Text, nullable=True)
    ship_to_address = db.Column(db.Text, nullable=True)
    order_id = db.Column(db.String(50), nullable=True)
    subtotal = db.Column(Numeric(10, 2), nullable=False)
    tax = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    
    status = db.Column(db.String(20), default=InvoiceStatus.UNPAID.value, nullable=False) 
    
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    payment_details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(Numeric(10, 2), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)

class StockRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    response_date = db.Column(db.DateTime, nullable=True)
    admin_note = db.Column(db.String(255), nullable=True)
    seller = db.relationship('User', backref='stock_requests')
    product = db.relationship('Product', backref='stock_requests')

class SellerInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    stock = db.Column(db.Integer, default=0)
    seller = db.relationship('User', backref='inventory_items')
    product = db.relationship('Product', backref='seller_allocations')

class AffiliateAd(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_name = db.Column(db.String(100), nullable=False, unique=True)
    affiliate_link = db.Column(db.Text, nullable=False)

class ShareableLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller = db.relationship('User', backref='shareable_links')


class VoucherOrder(db.Model):
    __tablename__ = 'voucher_order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gift_card_id = db.Column(db.Integer, db.ForeignKey('gift_card.id'), nullable=False)
    status = db.Column(db.String(20), default=VoucherOrderStatus.PENDING.value, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='voucher_orders')
    gift_card = db.relationship('GiftCard', backref='voucher_orders')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])