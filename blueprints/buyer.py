from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Product, Cart, CartItem, Order, OrderItem, User
from utils import role_required
import time

buyer_bp = Blueprint('buyer', __name__)

@buyer_bp.route('/buyer')
@login_required
@role_required('buyer')
def buyer_dashboard():
    category_filter = request.args.get('category')
    query = Product.query.filter(Product.stock > 0)
    if category_filter:
        query = query.filter_by(category=category_filter)
    products = query.all()
    categories_query = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories_query if c[0]]
    return render_template('buyer_dashboard.html', products=products, categories=categories, current_category=category_filter)

@buyer_bp.route('/product/<int:product_id>')
@login_required
@role_required('buyer')
def product_detail_page(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail_buyer.html', product=product)

@buyer_bp.route('/cart')
@login_required
@role_required('buyer')
def view_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    cart_items = []
    total = 0
    if cart:
        for item in cart.items:
            product = Product.query.get(item.product_id)
            if product:
                subtotal = product.price * item.quantity
                total += subtotal
                cart_items.append({'id': item.id, 'product': product, 'quantity': item.quantity, 'subtotal': subtotal})
    return render_template('cart.html', cart_items=cart_items, total=total)

@buyer_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock < 1:
        flash('Product is out of stock.', 'danger')
        return redirect(url_for('buyer.buyer_dashboard'))

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item: cart_item.quantity += 1
    else: 
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('buyer.buyer_dashboard'))

@buyer_bp.route('/remove_from_cart/<int:item_id>')
@login_required
@role_required('buyer')
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id: abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('buyer.view_cart'))

@buyer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@role_required('buyer')
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.buyer_dashboard'))

    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address')
        billing_address = request.form.get('billing_address')
        total_amount = 0
        order_items = []
        
        for item in cart.items:
            product = Product.query.get(item.product_id)
            if product.stock < item.quantity:
                flash(f'Sorry, {product.name} only has {product.stock} left in stock.', 'danger')
                return redirect(url_for('buyer.view_cart'))
            total_amount += product.price * item.quantity
            product.stock -= item.quantity
            order_items.append(OrderItem(product_name=product.name, quantity=item.quantity, price_at_purchase=product.price))

        order_number = f"ORD-{int(time.time())}-{current_user.id}"
        new_order = Order(
            order_number=order_number, user_id=current_user.id, total_amount=total_amount,
            shipping_address=shipping_address, billing_address=billing_address, status='Order Placed'
        )
        db.session.add(new_order)
        db.session.commit()

        for oi in order_items:
            oi.order_id = new_order.id
            db.session.add(oi)
        
        db.session.delete(cart)
        db.session.commit()

        flash('Order placed successfully!', 'success')
        return redirect(url_for('buyer.my_orders'))

    return render_template('checkout.html')

@buyer_bp.route('/my_orders')
@login_required
@role_required('buyer')
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)