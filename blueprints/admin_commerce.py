from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
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
import traceback 
from enums import UserRole, OrderStatus, InvoiceStatus

admin_commerce_bp = Blueprint('admin_commerce', __name__, url_prefix='/admin/commerce')

GST_RATES = {'Electronics': 18.0, 'Apparel': 12.0, 'Home & Office': 12.0, 'Books': 5.0, 'Accessories': 12.0, 'Other': 18.0}

@admin_commerce_bp.route('/dashboard')
@login_required
@role_required(UserRole.ADMIN.value)
def admin_commerce_dashboard():
    pending_orders_count = Order.query.filter_by(status=OrderStatus.PLACED.value).count()
    pending_requests_count = StockRequest.query.filter_by(status='Pending').count()
    low_stock_count = Product.query.filter(Product.stock < 10).count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    pending_requests = StockRequest.query.filter_by(status='Pending').order_by(StockRequest.request_date.desc()).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    pending_commerce_users = User.query.filter(
        User.is_approved == False, 
        User.role.in_([UserRole.SELLER.value, UserRole.BUYER.value])
    ).all()
    
    sellers = User.query.filter_by(role=UserRole.SELLER.value).limit(20).all()
    buyers = User.query.filter_by(role=UserRole.BUYER.value).limit(20).all()

    return render_template('admin_commerce_dashboard.html',
                           pending_orders_count=pending_orders_count,
                           pending_requests_count=pending_requests_count,
                           low_stock_count=low_stock_count,
                           recent_orders=recent_orders,
                           pending_requests=pending_requests,
                           recent_invoices=recent_invoices,
                           pending_commerce_users=pending_commerce_users,
                           sellers=sellers, buyers=buyers)

# --- ADS MANAGEMENT ---
@admin_commerce_bp.route('/ads/manage', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def manage_ads():
    if request.method == 'POST':
        ad_name = request.form.get('ad_name')
        affiliate_link = request.form.get('affiliate_link')
        existing_ad = AffiliateAd.query.filter_by(ad_name=ad_name).first()
        if existing_ad:
            existing_ad.affiliate_link = affiliate_link
            log_user_action("Update Ad", f"Updated ad {ad_name}")
            flash(f'Ad "{ad_name}" updated.', 'success')
        else:
            new_ad = AffiliateAd(ad_name=ad_name, affiliate_link=affiliate_link)
            db.session.add(new_ad)
            log_user_action("Create Ad", f"Created ad {ad_name}")
            flash(f'New ad "{ad_name}" added.', 'success')
        db.session.commit()
        return redirect(url_for('admin_commerce.manage_ads'))
    ads = AffiliateAd.query.all()
    return render_template('manage_ads.html', ads=ads)

@admin_commerce_bp.route('/ads/delete/<int:ad_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_ad(ad_id):
    ad = AffiliateAd.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    log_user_action("Delete Ad", f"Deleted ad {ad.ad_name}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Ad deleted.', 'remove_row_id': f'ad-{ad_id}'})
    return redirect(url_for('admin_commerce.manage_ads'))

# --- INVENTORY MANAGEMENT ---
@admin_commerce_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
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
            log_user_action("Add Product", f"Added product {name}")
            flash(f'Product "{name}" added to Master Inventory.', 'success')
        return redirect(url_for('admin_commerce.manage_inventory'))
    
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # ── Stats via SQL (fast, no Python loops) ──────────────────────────────
    from sqlalchemy import func as sqlfunc
    total_products_count = Product.query.count()
    low_stock_count = Product.query.filter(Product.stock < 10).count()
    value_row = db.session.query(
        sqlfunc.coalesce(sqlfunc.sum(Product.stock * Product.price), 0)
    ).scalar()
    total_inventory_value = float(value_row or 0)

    # ── Paginated product list (with optional search) ───────────────────────
    base_query = Product.query
    if search_query:
        base_query = base_query.filter(
            db.or_(
                Product.name.ilike(f'%{search_query}%'),
                Product.product_code.ilike(f'%{search_query}%'),
                Product.category.ilike(f'%{search_query}%')
            )
        )
    pagination = base_query.order_by(Product.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    products = pagination.items

    sellers = User.query.filter_by(role=UserRole.SELLER.value).with_entities(
        User.id, User.username, User.email
    ).all()

    return render_template('manage_inventory.html',
                           products=products,
                           pagination=pagination,
                           sellers=sellers,
                           total_inventory_value=total_inventory_value,
                           total_products_count=total_products_count,
                           low_stock_count=low_stock_count,
                           search_query=search_query)

@admin_commerce_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def add_product_page():
    if request.method == 'POST':
        product_code = request.form.get('product_code')
        name = request.form.get('name')
        stock = request.form.get('stock')
        price = request.form.get('price')
        description = request.form.get('description')
        image_urls = request.form.getlist('image_urls[]')
        category = request.form.get('category')
        brand = request.form.get('brand')
        mrp = request.form.get('mrp')
        warranty = request.form.get('warranty')
        return_policy = request.form.get('return_policy')
        
        if Product.query.filter_by(product_code=product_code).first():
            flash(f'Product ID {product_code} already exists.', 'danger')
            return redirect(url_for('admin_commerce.add_product_page'))
        
        primary_image = image_urls[0].strip() if image_urls and image_urls[0].strip() else None
        
        new_product = Product(
            product_code=product_code, name=name, stock=int(stock), price=float(price),
            description=description, image_url=primary_image, category=category,
            brand=brand, mrp=float(mrp) if mrp else None, warranty=warranty, return_policy=return_policy,
            seller_id=None
        )
        db.session.add(new_product)
        db.session.commit()
        
        for url in image_urls:
            if url.strip():
                img = ProductImage(product_id=new_product.id, image_url=url.strip())
                db.session.add(img)
        db.session.commit()
        
        log_user_action("Add Product", f"Added product {name}")
        flash(f'Product "{name}" added to catalog successfully.', 'success')
        return redirect(url_for('admin_commerce.manage_inventory'))
    
    return render_template('add_product.html')

@admin_commerce_bp.route('/inventory/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_product_page(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.stock = int(request.form.get('stock'))
        product.price = float(request.form.get('price'))
        product.description = request.form.get('description')
        product.category = request.form.get('category')
        product.brand = request.form.get('brand')
        
        mrp = request.form.get('mrp')
        if mrp: product.mrp = float(mrp)
        else: product.mrp = None
        
        product.warranty = request.form.get('warranty')
        product.return_policy = request.form.get('return_policy')

        image_urls = request.form.getlist('image_urls[]')
        if image_urls and image_urls[0].strip():
            product.image_url = image_urls[0].strip()
        
        ProductImage.query.filter_by(product_id=product.id).delete()
        for url in image_urls:
            if url.strip():
                db.session.add(ProductImage(product_id=product.id, image_url=url.strip()))
        
        db.session.commit()
        log_user_action("Update Product", f"Updated product {product.name}")
        flash(f'Product "{product.name}" updated successfully.', 'success')
        # Redirect to the product detail view instead of the inventory list
        return redirect(url_for('admin_commerce.view_product', product_id=product.id))

    return render_template('edit_product.html', product=product)

@admin_commerce_bp.route('/inventory/import', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
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
                if Product.query.filter_by(product_code=row.get('product_code')).first(): continue
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
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not row[0]: continue
                if Product.query.filter_by(product_code=str(row[0])).first(): continue
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
        log_user_action("Import Inventory", f"Imported {products_added} products")
        flash(f'Successfully imported {products_added} products.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Import failed: {str(e)}', 'danger')

    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_product():
    product_id = request.form.get('product_id')
    product = Product.query.get_or_404(product_id)
    product.name = request.form.get('name')
    product.stock = int(request.form.get('stock'))
    product.price = float(request.form.get('price'))
    db.session.commit()
    log_user_action("Quick Update", f"Quick updated product {product.name}")
    flash(f'Product "{product.name}" updated.', 'success')
    
    # Redirect to the product detail view
    return redirect(url_for('admin_commerce.view_product', product_id=product.id))

@admin_commerce_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    log_user_action("Delete Product", f"Deleted product {product_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Product deleted.', 'remove_row_id': f'prod-{product_id}'})
    return redirect(url_for('admin_commerce.manage_inventory'))

@admin_commerce_bp.route('/inventory/assign', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def assign_inventory():
    product_id = request.form.get('product_id')
    seller_id = request.form.get('seller_id')
    quantity = int(request.form.get('quantity'))

    product = Product.query.get_or_404(product_id)
    
    # Redirect target
    redirect_target = redirect(url_for('admin_commerce.view_product', product_id=product.id))
    
    if product.stock < quantity:
        flash(f"Insufficient stock (Available: {product.stock}).", "danger")
        return redirect_target

    product.stock -= quantity
    seller_inv = SellerInventory.query.filter_by(seller_id=seller_id, product_id=product.id).first()
    
    if seller_inv: seller_inv.stock += quantity
    else: db.session.add(SellerInventory(seller_id=seller_id, product_id=product.id, stock=quantity))

    db.session.commit()
    log_user_action("Assign Inventory", f"Assigned {quantity} of {product.name} to seller {seller_id}")
    flash(f"Assigned {quantity} units to seller.", "success")
    return redirect_target

# --- SELLER INVENTORY ---
@admin_commerce_bp.route('/inventory/seller', defaults={'seller_id': None})
@admin_commerce_bp.route('/inventory/seller/<int:seller_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_seller_inventory(seller_id):
    sellers = User.query.filter_by(role=UserRole.SELLER.value).all()
    selected_seller = None
    allocations = []
    if seller_id:
        selected_seller = User.query.get_or_404(seller_id)
        allocations = SellerInventory.query.filter_by(seller_id=seller_id).all()
    return render_template('manage_seller_inventory.html', sellers=sellers, selected_seller=selected_seller, allocations=allocations)

@admin_commerce_bp.route('/inventory/seller/update', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_seller_stock():
    allocation_id = request.form.get('allocation_id')
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        new_stock = int(request.form.get('stock'))
        allocation = SellerInventory.query.get_or_404(allocation_id)
        allocation.stock = new_stock
        db.session.commit()
        log_user_action("Update Seller Stock", f"Updated stock for seller {allocation.seller.username}")
        if is_xhr:
            return jsonify({'success': True, 'message': f'Stock updated for {allocation.product.name}.', 'new_stock': new_stock})
        flash(f"Stock updated for {allocation.product.name}.", "success")
        return redirect(url_for('admin_commerce.manage_seller_inventory', seller_id=allocation.seller_id))
    except ValueError:
        if is_xhr:
            return jsonify({'success': False, 'message': 'Invalid stock value.'}), 400
        flash("Invalid stock value.", "danger")
        return redirect(url_for('admin_commerce.manage_seller_inventory'))

@admin_commerce_bp.route('/inventory/seller/delete/<int:allocation_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_seller_allocation(allocation_id):
    allocation = SellerInventory.query.get_or_404(allocation_id)
    seller_id = allocation.seller_id
    product_name = allocation.product.name
    db.session.delete(allocation)
    db.session.commit()
    log_user_action("Delete Seller Alloc", f"Removed allocation {allocation_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'{product_name} allocation removed.', 'remove_row_id': f'row-alloc-{allocation_id}'})
    flash("Allocation removed.", "info")
    return redirect(url_for('admin_commerce.manage_seller_inventory', seller_id=seller_id))

# --- STOCK REQUESTS ---
@admin_commerce_bp.route('/inventory/requests')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_stock_requests_page():
    requests = StockRequest.query.filter_by(status='Pending').order_by(StockRequest.request_date.desc()).all()
    history = StockRequest.query.filter(StockRequest.status != 'Pending').order_by(StockRequest.response_date.desc()).limit(20).all()
    return render_template('manage_stock_requests.html', requests=requests, history=history)

@admin_commerce_bp.route('/inventory/requests/approve/<int:req_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def approve_stock_request(req_id):
    req = StockRequest.query.get_or_404(req_id)
    if req.product.stock < req.quantity:
        flash(f'Insufficient Master Stock (Available: {req.product.stock}).', 'danger')
        return redirect(url_for('admin_commerce.manage_stock_requests_page'))

    req.product.stock -= req.quantity
    seller_inv = SellerInventory.query.filter_by(seller_id=req.seller_id, product_id=req.product_id).first()
    if seller_inv: seller_inv.stock += req.quantity
    else: db.session.add(SellerInventory(seller_id=req.seller_id, product_id=req.product_id, stock=req.quantity))

    req.status = 'Approved'
    req.response_date = datetime.utcnow()
    db.session.commit()
    
    try:
        send_email(to=req.seller.email, subject=f"Stock Request Approved: {req.product.name}", template="mail/request_status_update.html", request=req, product=req.product, status="Approved")
    except Exception as e:
        print(f"Error sending stock approval email: {e}")
    
    log_user_action("Approve Stock Request", f"Approved stock for {req.seller.username}")
    flash('Request approved.', 'success')
    return redirect(url_for('admin_commerce.manage_stock_requests_page'))

@admin_commerce_bp.route('/inventory/requests/reject/<int:req_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def reject_stock_request(req_id):
    req = StockRequest.query.get_or_404(req_id)
    req.status = 'Rejected'
    req.response_date = datetime.utcnow()
    db.session.commit()
    
    try:
        send_email(to=req.seller.email, subject=f"Stock Request Rejected: {req.product.name}", template="mail/request_status_update.html", request=req, product=req.product, status="Rejected")
    except Exception as e:
        print(f"Error sending stock rejection email: {e}")
    
    log_user_action("Reject Stock Request", f"Rejected stock for {req.seller.username}")
    flash('Request rejected.', 'warning')
    return redirect(url_for('admin_commerce.manage_stock_requests_page'))

# --- ORDERS ---
@admin_commerce_bp.route('/orders')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    total_revenue = sum(order.total_amount for order in orders)
    pending_count = sum(1 for order in orders if order.status == OrderStatus.PLACED.value)
    completed_count = sum(1 for order in orders if order.status in [OrderStatus.DELIVERED.value, OrderStatus.SHIPPED.value])

    return render_template('manage_orders.html', orders=orders, total_revenue=total_revenue, pending_count=pending_count, completed_count=completed_count)

@admin_commerce_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order.status = new_status
    db.session.commit()
    
    # Auto Invoice Generation when Accepted
    attachments = None
    if new_status == OrderStatus.CONFIRMED.value or new_status == 'Order Accepted':
        try:
            invoice = Invoice.query.filter_by(order_id=order.order_number).first()
            if not invoice:
                # --- NEW TAX CALCULATION LOGIC ---
                total_tax_amount = 0
                total_base_amount = 0
                
                # Iterate order items to determine category-based tax
                for item in order.items:
                    # Find Product to get category
                    product = Product.query.filter_by(name=item.product_name).first()
                    category = product.category if product else 'Other'
                    
                    # Get Tax Rate from Config
                    rate = GST_RATES.get(category, GST_RATES['Other'])
                    
                    # Back-calculate Tax from Inclusive Price
                    # Formula: Tax = (Price * Rate) / (100 + Rate)
                    item_total_inclusive = float(item.price_at_purchase) * item.quantity
                    tax_component = (item_total_inclusive * rate) / (100 + rate)
                    base_component = item_total_inclusive - tax_component
                    
                    total_tax_amount += tax_component
                    total_base_amount += base_component

                # Create Invoice with Segregated Tax
                invoice = Invoice(
                    invoice_number=f"INV-{order.order_number}",
                    recipient_name=order.buyer.username,
                    recipient_email=order.buyer.email,
                    bill_to_address=order.billing_address,
                    ship_to_address=order.shipping_address, 
                    order_id=order.order_number,
                    subtotal=total_base_amount, 
                    tax=total_tax_amount, # Stores the AMOUNT now
                    total_amount=order.total_amount,
                    status=InvoiceStatus.UNPAID.value,
                    admin_id=current_user.id,
                    created_at=datetime.utcnow(),
                    due_date=datetime.utcnow()
                )
                db.session.add(invoice)
                db.session.flush() 
                for order_item in order.items:
                    inv_item = InvoiceItem(invoice_id=invoice.id, description=order_item.product_name, quantity=order_item.quantity, price=order_item.price_at_purchase)
                    db.session.add(inv_item)
                db.session.commit()
            
            generator = InvoiceGenerator(invoice)
            pdf_bytes = generator.generate_pdf()
            attachments = [{'filename': f'Invoice_{invoice.invoice_number}.pdf', 'data': pdf_bytes}]
        except Exception as e:
            print(f"Error generating invoice: {e}")
            traceback.print_exc()

    try:
        send_email(
            to=order.buyer.email, subject=f'Order Update: {new_status}', 
            template='mail/order_status_update.html', buyer_name=order.buyer.username, 
            order_number=order.order_number, status=new_status, 
            total_amount=order.total_amount, shipping_address=order.shipping_address, now=datetime.utcnow(),
            attachments=attachments  
        )
    except Exception as e:
        print(f"Failed to send email: {e}")
    
    log_user_action("Update Order", f"Updated order {order.order_number} to {new_status}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Order {order.order_number} updated to {new_status}.', 'new_status': new_status})
    flash(f'Order {order.order_number} updated to {new_status}.', 'success')
    return redirect(url_for('admin_commerce.manage_orders'))

# --- CREATE ORDER (Admin) ---
@admin_commerce_bp.route('/orders/create', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def admin_create_order():
    if request.method == 'POST':
        try:
            buyer_type = request.form.get('buyer_type', 'existing')
            shipping_address = request.form.get('shipping_address', '').strip()
            billing_address = request.form.get('billing_address', '').strip() or shipping_address
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')

            if not shipping_address:
                flash('Shipping address is required.', 'danger')
                return redirect(url_for('admin_commerce.admin_create_order'))

            if not product_ids:
                flash('Please add at least one product to the order.', 'danger')
                return redirect(url_for('admin_commerce.admin_create_order'))

            # --- 1. Resolve Buyer ---
            buyer = None
            new_account_created = False

            if buyer_type == 'existing':
                user_id = request.form.get('buyer_user_id')
                if not user_id:
                    flash('Please select a buyer.', 'danger')
                    return redirect(url_for('admin_commerce.admin_create_order'))
                buyer = User.query.get(user_id)
                if not buyer:
                    flash('Selected buyer not found.', 'danger')
                    return redirect(url_for('admin_commerce.admin_create_order'))
            else:
                # Custom email flow
                custom_email = request.form.get('custom_email', '').strip().lower()
                if not custom_email:
                    flash('Please enter a buyer email address.', 'danger')
                    return redirect(url_for('admin_commerce.admin_create_order'))

                buyer = User.query.filter_by(email=custom_email).first()
                if not buyer:
                    # Auto-create buyer account
                    from extensions import bcrypt as _bcrypt
                    default_password = 'SourcePoint@123'

                    # Generate a unique username from email prefix
                    base_username = custom_email.split('@')[0].replace('.', '_').replace('+', '_')[:50]
                    username_candidate = base_username
                    counter = 1
                    while User.query.filter_by(username=username_candidate).first():
                        username_candidate = f"{base_username}{counter}"
                        counter += 1

                    hashed_pw = _bcrypt.generate_password_hash(default_password).decode('utf-8')
                    avatar_url = f'https://api.dicebear.com/8.x/initials/svg?seed={username_candidate}'

                    buyer = User(
                        username=username_candidate,
                        email=custom_email,
                        password_hash=hashed_pw,
                        role=UserRole.BUYER.value,
                        is_approved=True,
                        avatar_url=avatar_url,
                    )
                    db.session.add(buyer)
                    db.session.flush()  # get buyer.id before commit
                    new_account_created = True
                    log_user_action("Auto-Create Buyer", f"Created buyer account for {custom_email} via admin order")

            # --- 2. Process Products & Stock ---
            import time as _time
            total_amount = 0
            order_items_data = []

            for pid, qty_str in zip(product_ids, quantities):
                if not pid or not qty_str:
                    continue
                try:
                    qty = int(qty_str)
                    if qty < 1:
                        continue
                except ValueError:
                    continue

                product = Product.query.get(pid)
                if not product:
                    flash(f'Product ID {pid} not found.', 'danger')
                    db.session.rollback()
                    return redirect(url_for('admin_commerce.admin_create_order'))

                if product.stock < qty:
                    flash(f'Insufficient stock for "{product.name}" (Available: {product.stock}, Requested: {qty}).', 'danger')
                    db.session.rollback()
                    return redirect(url_for('admin_commerce.admin_create_order'))

                product.stock -= qty
                total_amount += float(product.price) * qty
                order_items_data.append({
                    'product_name': product.name,
                    'quantity': qty,
                    'price_at_purchase': product.price,
                })

            if not order_items_data:
                flash('No valid products were added to the order.', 'danger')
                db.session.rollback()
                return redirect(url_for('admin_commerce.admin_create_order'))

            # --- 3. Create Order ---
            from models.commerce import OrderItem as _OrderItem
            order_number = f"ORD-ADMIN-{int(_time.time())}-{buyer.id}"
            new_order = Order(
                order_number=order_number,
                user_id=buyer.id,
                total_amount=total_amount,
                shipping_address=shipping_address,
                billing_address=billing_address,
                status='Order Placed',
            )
            db.session.add(new_order)
            db.session.flush()

            for item_data in order_items_data:
                db.session.add(_OrderItem(
                    order_id=new_order.id,
                    product_name=item_data['product_name'],
                    quantity=item_data['quantity'],
                    price_at_purchase=item_data['price_at_purchase'],
                ))

            db.session.commit()

            # --- 4. Send Emails ---
            # Welcome email for newly created accounts
            if new_account_created:
                try:
                    send_email(
                        to=buyer.email,
                        subject="Welcome to SourcePoint — Your Account & Order Details",
                        template="mail/admin_created_order_welcome.html",
                        buyer=buyer,
                        order=new_order,
                        default_password='SourcePoint@123',
                        login_url=url_for('auth.login_register', _external=True),
                        now=datetime.utcnow(),
                    )
                except Exception as e:
                    print(f"[WARN] Welcome email failed for {buyer.email}: {e}")

            # Order confirmation email
            try:
                send_email(
                    to=buyer.email,
                    subject=f"Order Confirmation: {new_order.order_number}",
                    template="mail/order_status_update.html",
                    buyer_name=buyer.username,
                    order_number=new_order.order_number,
                    status="Order Placed",
                    order_date=datetime.utcnow().strftime('%B %d, %Y'),
                    total_amount=new_order.total_amount,
                    shipping_address=shipping_address,
                    now=datetime.utcnow(),
                )
            except Exception as e:
                print(f"[WARN] Order confirmation email failed: {e}")

            log_user_action("Admin Create Order", f"Created order {order_number} for buyer {buyer.email}")
            flash(f'Order {order_number} created successfully for {buyer.email}!', 'success')
            if new_account_created:
                flash(f'A new buyer account was created for {buyer.email} with the default password.', 'info')
            return redirect(url_for('admin_commerce.manage_orders'))

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Admin create order failed: {e}")
            traceback.print_exc()
            flash(f'Error creating order: {str(e)}', 'danger')
            return redirect(url_for('admin_commerce.admin_create_order'))

    # GET: Render form
    buyers = User.query.filter_by(role=UserRole.BUYER.value, is_approved=True).order_by(User.username).all()
    products = Product.query.filter(Product.stock > 0).order_by(Product.name).all()
    products_js = [
        {'id': p.id, 'name': p.name, 'price': float(p.price), 'stock': p.stock, 'code': p.product_code}
        for p in products
    ]
    return render_template('admin_create_order.html', buyers=buyers, products=products, products_js=products_js)


# --- INVOICES ---
@admin_commerce_bp.route('/invoices')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_invoices():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('manage_invoices.html', invoices=invoices)

@admin_commerce_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_invoice():
    if request.method == 'POST':
        try:
            recipient_name = request.form.get('recipient_name')
            recipient_email = request.form.get('recipient_email')
            due_date_str = request.form.get('due_date')
            order_id = request.form.get('order_id')
            bill_to = request.form.get('bill_to_address')
            ship_to = request.form.get('ship_to_address')
            notes = request.form.get('notes')
            payment_details = request.form.get('payment_details')
            tax_rate = float(request.form.get('tax', 0))

            descriptions = request.form.getlist('item_description[]')
            quantities = request.form.getlist('item_quantity[]')
            prices = request.form.getlist('item_price[]')

            subtotal = 0
            invoice_items_data = []

            for d, q, p in zip(descriptions, quantities, prices):
                if d and q and p:
                    qty = int(q)
                    price = float(p)
                    subtotal += qty * price
                    invoice_items_data.append({'description': d, 'quantity': qty, 'price': price})
            
            tax_amount = subtotal * (tax_rate / 100)
            total_amount = subtotal + tax_amount

            import uuid
            invoice_num = f"INV-{uuid.uuid4().hex[:6].upper()}"
            
            new_invoice = Invoice(
                invoice_number=invoice_num, recipient_name=recipient_name, recipient_email=recipient_email,
                bill_to_address=bill_to, ship_to_address=ship_to, order_id=order_id,
                subtotal=subtotal, tax=tax_amount, total_amount=total_amount,
                status=InvoiceStatus.UNPAID.value,
                due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None,
                notes=notes, payment_details=payment_details, admin_id=current_user.id
            )
            db.session.add(new_invoice)
            db.session.flush()

            for item in invoice_items_data:
                db.session.add(InvoiceItem(invoice_id=new_invoice.id, description=item['description'], quantity=item['quantity'], price=item['price']))

            db.session.commit()

            generator = InvoiceGenerator(new_invoice)
            pdf_bytes = generator.generate_pdf()
            attachments = [{'filename': f'Invoice_{new_invoice.invoice_number}.pdf', 'data': pdf_bytes}]
            
            send_email(to=recipient_email, subject=f"New Invoice #{new_invoice.invoice_number}", template="mail/ecommerce_invoice_email.html", invoice=new_invoice, attachments=attachments)

            log_user_action("Create Invoice", f"Created invoice {invoice_num}")
            flash(f'Invoice {new_invoice.invoice_number} created and sent.', 'success')
            return redirect(url_for('admin_commerce.manage_invoices'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating invoice: {str(e)}", 'danger')
            return redirect(url_for('admin_commerce.create_invoice'))

    products = Product.query.filter(Product.stock > 0).all()
    products_js = [{'id': p.id, 'name': p.name, 'price': float(p.price), 'code': p.product_code} for p in products]
    return render_template('create_invoice.html', products=products_js)

@admin_commerce_bp.route('/invoices/mark_paid/<int:invoice_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = InvoiceStatus.PAID.value
    if invoice.order_id:
        order = Order.query.filter_by(order_number=invoice.order_id).first()
        if order and order.status != OrderStatus.DELIVERED.value: order.status = 'Payment Received'
    db.session.commit()
    
    try:
        send_email(to=invoice.recipient_email, subject=f"Payment Receipt: Invoice #{invoice.invoice_number}", template="mail/payment_received.html", recipient_name=invoice.recipient_name, invoice=invoice, total_amount=invoice.total_amount)
    except Exception as e: print(f"Email error: {e}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Invoice marked as Paid.'})
    flash('Invoice marked as Paid.', 'success')
    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/delete/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    log_user_action("Delete Invoice", f"Deleted invoice {invoice_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Invoice deleted.', 'remove_row_id': f'inv-{invoice_id}'})
    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/resend', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def resend_invoice():
    invoice_id = request.form.get('invoice_id')
    recipients = request.form.get('recipient_emails')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not invoice_id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Invoice ID is required.'})
        return redirect(url_for('admin_commerce.manage_invoices'))

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Invoice not found.'})
        flash("Invoice not found.", "danger")
        return redirect(url_for('admin_commerce.manage_invoices'))
    
    try:
        generator = InvoiceGenerator(invoice)
        pdf_bytes = generator.generate_pdf()
        attachments = [{'filename': f'Invoice_{invoice.invoice_number}.pdf', 'data': pdf_bytes}]
        recipient_list = [r.strip() for r in recipients.split(',')]
        for email_to in recipient_list:
             send_email(to=email_to, subject=f"Invoice #{invoice.invoice_number}", template="mail/ecommerce_invoice_email.html", invoice=invoice, attachments=attachments, sync=True)
        
        if is_ajax:
            return jsonify({'success': True, 'message': 'Invoice resent successfully.'})
        flash("Invoice resent.", "success")
    except Exception as e:
        if is_ajax:
            return jsonify({'success': False, 'message': str(e)})
        flash(f"Error: {e}", "danger")
    
    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/remind/<int:invoice_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def send_invoice_reminder(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    try:
        generator = InvoiceGenerator(invoice)
        pdf_bytes = generator.generate_pdf()
        attachments = [{'filename': f'Invoice_{invoice.invoice_number}.pdf', 'data': pdf_bytes}]
        send_email(to=invoice.recipient_email, subject=f"Payment Reminder: Invoice #{invoice.invoice_number}", template="mail/reminder_invoice_email.html", recipient_name=invoice.recipient_name, invoice_number=invoice.invoice_number, created_at=invoice.created_at.strftime('%d %b %Y'), total_amount=invoice.total_amount, due_date=invoice.due_date.strftime('%d %b %Y') if invoice.due_date else "Immediate", invoice=invoice, attachments=attachments)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Reminder sent.'})
        flash("Reminder sent.", "success")
    except Exception as e:
         if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': False, 'message': str(e)})
         flash(f"Error: {e}", "danger")
    return redirect(url_for('admin_commerce.manage_invoices'))

# --- VIEW PRODUCT DETAILS ROUTE ---
@admin_commerce_bp.route('/inventory/view/<int:product_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    # Admin wants to see who has this product
    allocations = SellerInventory.query.filter_by(product_id=product.id).all()
    return render_template('product_detail_manage.html', product=product, allocations=allocations)

# --- SHAREABLE LINK ---

@admin_commerce_bp.route('/share-link', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def generate_share_link():
    import uuid
    from models.commerce import ShareableLink

    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        link = ShareableLink(
            token=uuid.uuid4().hex,
            seller_id=current_user.id,
            is_active=True
        )
        db.session.add(link)
        db.session.commit()

    share_url = url_for('public.shared_catalog', token=link.token, _external=True)
    return jsonify({'success': True, 'url': share_url, 'is_active': link.is_active, 'token': link.token})


@admin_commerce_bp.route('/share-link/toggle', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def toggle_share_link():
    from models.commerce import ShareableLink

    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        return jsonify({'success': False, 'message': 'No share link found. Generate one first.'}), 404

    link.is_active = not link.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': link.is_active, 'message': f"Link {'activated' if link.is_active else 'deactivated'}."})