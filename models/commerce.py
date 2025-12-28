# Source Point/models/commerce.py
from extensions import db
from datetime import datetime
from sqlalchemy import Numeric

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    # Enhancement: Use Numeric for money
    price = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    brand = db.Column(db.String(100), nullable=True)
    # Enhancement: Use Numeric for money
    mrp = db.Column(Numeric(10, 2), nullable=True) 
    warranty = db.Column(db.String(200), nullable=True)
    return_policy = db.Column(db.String(200), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Enhancement: Use Numeric for money
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='Order Placed') 
    
    # Enhancement: Structured Address Data
    shipping_street = db.Column(db.String(200), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=True)
    shipping_state = db.Column(db.String(100), nullable=True)
    shipping_zip = db.Column(db.String(20), nullable=True)
    shipping_country = db.Column(db.String(100), nullable=True)
    
    # Billing Address (Simplified for now, but could follow same pattern)
    billing_address = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    @property
    def shipping_address(self):
        """Returns the full address as a string for backward compatibility."""
        parts = [self.shipping_street, self.shipping_city, self.shipping_state, self.shipping_zip, self.shipping_country]
        return ", ".join(filter(None, parts))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    # Enhancement: Use Numeric for money
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

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    bill_to_address = db.Column(db.Text, nullable=True)
    ship_to_address = db.Column(db.Text, nullable=True)
    order_id = db.Column(db.String(50), nullable=True)
    
    # Enhancement: Use Numeric for money
    subtotal = db.Column(Numeric(10, 2), nullable=False)
    tax = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    
    status = db.Column(db.String(20), default='Unpaid', nullable=False) 
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
    # Enhancement: Use Numeric for money
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