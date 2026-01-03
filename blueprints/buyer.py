from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models.commerce import Product, Cart, CartItem, Order 
from services.commerce_service import CommerceService      
from utils import role_required

buyer_bp = Blueprint('buyer', __name__)

@buyer_bp.route('/buyer')
@login_required
@role_required('buyer')
def buyer_dashboard():
    category_filter = request.args.get('category')
    # This query is already decent, but the index we added to models/commerce.py 
    # will make it much faster.
    query = Product.query.filter(Product.stock > 0)
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    products = query.all()
    
    # distinct() is expensive; in a real app, cache this list.
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
    # --- REFACTORED: Use Service for Performance ---
    cart_items, total, _ = CommerceService.get_cart_details(current_user.id)
    return render_template('cart.html', cart_items=cart_items, total=total)

@buyer_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def add_to_cart(product_id):
    success, msg = CommerceService.add_to_cart(current_user.id, product_id)
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
        
    return redirect(url_for('buyer.buyer_dashboard'))

@buyer_bp.route('/remove_from_cart/<int:item_id>')
@login_required
@role_required('buyer')
def remove_from_cart(item_id):
    # --- REFACTORED: Use Service ---
    success, msg = CommerceService.remove_item(current_user.id, item_id)
    if success:
        flash(msg, 'info')
    else:
        flash(msg, 'danger')
        
    return redirect(url_for('buyer.view_cart'))

@buyer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@role_required('buyer')
def checkout():
    # Quick check for empty cart before rendering page
    _, total, cart = CommerceService.get_cart_details(current_user.id)
    
    if not cart or not cart.items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.buyer_dashboard'))

    if request.method == 'POST':
        order, msg = CommerceService.process_checkout(
            user_id=current_user.id,
            shipping_address=request.form.get('shipping_address'),
            billing_address=request.form.get('billing_address')
        )
        
        if order:
            flash(msg, 'success')
            return redirect(url_for('buyer.my_orders'))
        else:
            flash(msg, 'danger')
            return redirect(url_for('buyer.view_cart'))

    return render_template('checkout.html', total=total)

@buyer_bp.route('/my_orders')
@login_required
@role_required('buyer')
def my_orders():
    # Added eager loading for items to speed up order history view
    from sqlalchemy.orm import joinedload
    orders = Order.query.options(joinedload(Order.items))\
                .filter_by(user_id=current_user.id)\
                .order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)