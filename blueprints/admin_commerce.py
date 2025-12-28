from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.commerce import Product, ProductImage, Order, AffiliateAd, Invoice, InvoiceItem, SellerInventory, StockRequest
from utils import role_required, log_user_action, send_email
from invoice_service import InvoiceGenerator
from datetime import datetime
from werkzeug.utils import secure_filename
import csv
from io import TextIOWrapper
import openpyxl 

admin_commerce_bp = Blueprint('admin_commerce', __name__, url_prefix='/admin/commerce')

GST_RATES = {'Electronics': 18.0, 'Apparel': 12.0, 'Home & Office': 12.0, 'Books': 5.0, 'Accessories': 12.0, 'Other': 18.0}

@admin_commerce_bp.route('/dashboard')
@login_required
@role_required('admin')
def admin_commerce_dashboard():
    pending_orders_count = Order.query.filter_by(status='Order Placed').count()
    pending_requests_count = StockRequest.query.filter_by(status='Pending').count()
    low_stock_count = Product.query.filter(Product.stock < 10).count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    pending_requests = StockRequest.query.filter_by(status='Pending').order_by(StockRequest.request_date.desc()).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    pending_commerce_users = User.query.filter(User.is_approved == False, User.role.in_(['seller', 'buyer'])).all()
    sellers = User.query.filter_by(role='seller').limit(20).all()
    buyers = User.query.filter_by(role='buyer').limit(20).all()

    return render_template('admin_commerce_dashboard.html',
                           pending_orders_count=pending_orders_count,
                           pending_requests_count=pending_requests_count,
                           low_stock_count=low_stock_count,
                           recent_orders=recent_orders,
                           pending_requests=pending_requests,
                           recent_invoices=recent_invoices,
                           pending_commerce_users=pending_commerce_users,
                           sellers=sellers, buyers=buyers)

# --- ADS ---
@admin_commerce_bp.route('/ads/manage', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_ads():
    if request.method == 'POST':
        ad_name = request.form.get('ad_name')
        affiliate_link = request.form.get('affiliate_link')
        existing_ad = AffiliateAd.query.filter_by(ad_name=ad_name).first()
        if existing_ad:
            existing_ad.affiliate_link = affiliate_link
            flash(f'Ad "{ad_name}" updated.', 'success')
        else:
            new_ad = AffiliateAd(ad_name=ad_name, affiliate_link=affiliate_link)
            db.session.add(new_ad)
            flash(f'New ad "{ad_name}" added.', 'success')
        db.session.commit()
        return redirect(url_for('admin_commerce.manage_ads'))
    ads = AffiliateAd.query.all()
    return render_template('manage_ads.html', ads=ads)

@admin_commerce_bp.route('/ads/delete/<int:ad_id>')
@login_required
@role_required('admin')
def delete_ad(ad_id):
    ad = AffiliateAd.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Ad deleted.', 'remove_row_id': f'ad-{ad_id}'})
    return redirect(url_for('admin_commerce.manage_ads'))

# --- INVENTORY ---
@admin_commerce_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_inventory():
    if request.method == 'POST':
        product_code = request.form.get('product_code')
        name = request.form.get('name')
        stock = request.form.get('stock')
        price = request.form.get('price')
        
        if Product.query.filter_by(product_code=product_code).first():
            flash(f'Product ID {product_code} already exists.', 'danger')
        else:
            new_product = Product(product_code=product_code, name=name, stock=int(stock), price=float(price), seller_id=None)
            db.session.add(new_product)
            db.session.commit()
            flash(f'Product "{name}" added to Master Inventory.', 'success')
        return redirect(url_for('admin_commerce.manage_inventory'))
    
    products = Product.query.order_by(Product.name).all()
    sellers = User.query.filter_by(role='seller').all()
    total_inventory_value = sum(int(p.stock) * float(p.price) for p in products)
    low_stock_count = sum(1 for p in products if int(p.stock) < 10)

    return render_template('manage_inventory.html', products=products, sellers=sellers, 
                           total_inventory_value=total_inventory_value, total_products_count=len(products), low_stock_count=low_stock_count)

@admin_commerce_bp.route('/inventory/import', methods=['POST'])
@login_required
@role_required('admin')
def import_inventory():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin_commerce.manage_inventory'))

    try:
        filename = secure_filename(file.filename)
        products_added = 0
        
        if filename.endswith('.csv'):
            file_content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(file_content.splitlines())
            for row in csv_reader:
                if Product.query.filter_by(product_code=row.get('product_code')).first():
                    continue
                new_product = Product(
                    product_code=row.get('product_code'),
                    name=row.get('name'),
                    stock=int(row.get('stock', 0)),
                    price=float(row.get('price', 0)),
                    category=row.get('category', 'General')
                )
                db.session.add(new_product)
                products_added += 1

        elif filename.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            # Assuming row 1 is headers
            for row in sheet.iter_rows(min_row=2, values_only=True):
                # Format: code, name, stock, price, category
                if not row[0]: continue
                if Product.query.filter_by(product_code=str(row[0])).first():
                    continue
                new_product = Product(
                    product_code=str(row[0]),
                    name=row[1],
                    stock=int(row[2]) if row[2] else 0,
                    price=float(row[3]) if row[3] else 0.0,
                    category=row[4] if len(row)>4 else 'General'
                )
                db.session.add(new_product)
                products_added += 1

        db.session.commit()
        flash(f'Successfully imported {products_added} products.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Import failed: {str(e)}', 'danger')

    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required('admin')
def update_product():
    product_id = request.form.get('product_id')
    product = Product.query.get_or_404(product_id)
    
    product.name = request.form.get('name')
    product.stock = int(request.form.get('stock'))
    product.price = float(request.form.get('price'))
    
    db.session.commit()
    flash(f'Product "{product.name}" updated.', 'success')
    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required('admin')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Product deleted.', 'remove_row_id': f'prod-{product_id}'})
    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/assign', methods=['POST'])
@login_required
@role_required('admin')
def assign_inventory():
    product_id = request.form.get('product_id')
    seller_id = request.form.get('seller_id')
    quantity = int(request.form.get('quantity'))

    product = Product.query.get_or_404(product_id)
    if product.stock < quantity:
        flash(f"Insufficient stock (Available: {product.stock}).", "danger")
        return redirect(url_for('admin_commerce.manage_inventory'))

    product.stock -= quantity
    seller_inv = SellerInventory.query.filter_by(seller_id=seller_id, product_id=product.id).first()
    
    if seller_inv: seller_inv.stock += quantity
    else: db.session.add(SellerInventory(seller_id=seller_id, product_id=product.id, stock=quantity))

    db.session.commit()
    flash(f"Assigned {quantity} units to seller.", "success")
    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/requests')
@login_required
@role_required('admin')
def manage_stock_requests():
    requests = StockRequest.query.filter_by(status='Pending').order_by(StockRequest.request_date.desc()).all()
    history = StockRequest.query.filter(StockRequest.status != 'Pending').order_by(StockRequest.response_date.desc()).limit(20).all()
    return render_template('manage_stock_requests.html', requests=requests, history=history)

@admin_commerce_bp.route('/inventory/requests/approve/<int:req_id>', methods=['POST'])
@login_required
@role_required('admin')
def approve_stock_request(req_id):
    req = StockRequest.query.get_or_404(req_id)
    if req.product.stock < req.quantity:
        flash(f'Insufficient Master Stock (Available: {req.product.stock}).', 'danger')
        return redirect(url_for('admin_commerce.manage_stock_requests'))

    req.product.stock -= req.quantity
    seller_inv = SellerInventory.query.filter_by(seller_id=req.seller_id, product_id=req.product_id).first()
    if seller_inv: seller_inv.stock += req.quantity
    else: db.session.add(SellerInventory(seller_id=req.seller_id, product_id=req.product_id, stock=req.quantity))

    req.status = 'Approved'
    req.response_date = datetime.utcnow()
    db.session.commit()
    
    try:
        send_email(to=req.seller.email, subject=f"Stock Request Approved: {req.product.name}", template="mail/request_status_update.html", request=req, product=req.product, status="Approved")
    except Exception: pass
    
    flash('Request approved.', 'success')
    return redirect(url_for('admin_commerce.manage_stock_requests'))

@admin_commerce_bp.route('/inventory/requests/reject/<int:req_id>', methods=['POST'])
@login_required
@role_required('admin')
def reject_stock_request(req_id):
    req = StockRequest.query.get_or_404(req_id)
    req.status = 'Rejected'
    req.response_date = datetime.utcnow()
    db.session.commit()
    
    try:
        send_email(to=req.seller.email, subject=f"Stock Request Rejected: {req.product.name}", template="mail/request_status_update.html", request=req, product=req.product, status="Rejected")
    except Exception: pass
    
    flash('Request rejected.', 'warning')
    return redirect(url_for('admin_commerce.manage_stock_requests'))

# --- ORDERS ---
@admin_commerce_bp.route('/orders')
@login_required
@role_required('admin')
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('manage_orders.html', orders=orders)

@admin_commerce_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order.status = new_status
    db.session.commit()
    
    try:
        send_email(to=order.buyer.email, subject=f'Order Update: {new_status}', template='mail/order_status_update.html', buyer_name=order.buyer.username, order_number=order.order_number, status=new_status, order_date=order.created_at.strftime('%Y-%m-%d'), total_amount=order.total_amount)
    except Exception: pass
    
    flash(f'Order {order.order_number} status updated to {new_status}.', 'success')
    return redirect(url_for('admin_commerce.manage_orders'))

# --- INVOICES ---
@admin_commerce_bp.route('/invoices')
@login_required
@role_required('admin')
def manage_invoices():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('manage_invoices.html', invoices=invoices)

@admin_commerce_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_invoice():
    if request.method == 'POST':
        flash('Invoice created (Feature available in full version).', 'info')
        return redirect(url_for('admin_commerce.manage_invoices'))
    
    products = Product.query.filter(Product.stock > 0).all()
    products_js = [{'id': p.id, 'name': p.name, 'price': p.price} for p in products]
    return render_template('create_invoice.html', products=products_js)