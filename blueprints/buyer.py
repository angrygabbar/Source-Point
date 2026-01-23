from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db, cache
from models.commerce import Product, Cart, CartItem, Order 
from services.commerce_service import CommerceService      
from utils import role_required
from forms.commerce_forms import CheckoutForm  # Import the new form

buyer_bp = Blueprint('buyer', __name__)

@buyer_bp.route('/buyer')
@login_required
@role_required('buyer')
def buyer_dashboard():
    category_filter = request.args.get('category')
    
    # 1. Fetch Products
    query = Product.query.filter(Product.stock > 0)
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    products = query.all()
    
    # 2. Fetch Categories (OPTIMIZED WITH REDIS)
    categories = cache.get('all_product_categories')
    
    if categories is None:
        categories_query = db.session.query(Product.category).distinct().all()
        categories = [c[0] for c in categories_query if c[0]]
        cache.set('all_product_categories', categories, timeout=3600)
    
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
    # 1. Get Cart Totals
    _, total, cart = CommerceService.get_cart_details(current_user.id)
    
    if not cart or not cart.items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.buyer_dashboard'))

    # 2. Initialize Form
    form = CheckoutForm()

    # 3. Handle Form Submission (POST)
    if form.validate_on_submit():
        order, msg = CommerceService.process_checkout(
            user_id=current_user.id,
            shipping_address=form.shipping_address.data,
            billing_address=form.billing_address.data
        )
        
        if order:
            flash(msg, 'success')
            return redirect(url_for('buyer.my_orders'))
        else:
            flash(msg, 'danger')
            return redirect(url_for('buyer.view_cart'))
    
    # 4. Handle Validation Errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return render_template('checkout.html', total=total, form=form)

@buyer_bp.route('/my_orders')
@login_required
@role_required('buyer')
def my_orders():
    from sqlalchemy.orm import joinedload
    orders = Order.query.options(joinedload(Order.items))\
                .filter_by(user_id=current_user.id)\
                .order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)