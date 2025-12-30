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
import traceback 

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
            for row in sheet.iter_rows(min_row=2, values_only=True):
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

# --- SELLER INVENTORY MANAGEMENT (NEW MISSING ROUTES) ---
@admin_commerce_bp.route('/inventory/seller', defaults={'seller_id': None})
@admin_commerce_bp.route('/inventory/seller/<int:seller_id>')
@login_required
@role_required('admin')
def manage_seller_inventory(seller_id):
    sellers = User.query.filter_by(role='seller').all()
    selected_seller = None
    allocations = []
    if seller_id:
        selected_seller = User.query.get_or_404(seller_id)
        allocations = SellerInventory.query.filter_by(seller_id=seller_id).all()
    return render_template('manage_seller_inventory.html', sellers=sellers, selected_seller=selected_seller, allocations=allocations)

@admin_commerce_bp.route('/inventory/seller/update', methods=['POST'])
@login_required
@role_required('admin')
def update_seller_stock():
    allocation_id = request.form.get('allocation_id')
    try:
        new_stock = int(request.form.get('stock'))
        allocation = SellerInventory.query.get_or_404(allocation_id)
        allocation.stock = new_stock
        db.session.commit()
        flash(f"Stock updated for {allocation.product.name}.", "success")
        return redirect(url_for('admin_commerce.manage_seller_inventory', seller_id=allocation.seller_id))
    except ValueError:
        flash("Invalid stock value.", "danger")
        return redirect(url_for('admin_commerce.manage_seller_inventory'))

@admin_commerce_bp.route('/inventory/seller/delete/<int:allocation_id>')
@login_required
@role_required('admin')
def delete_seller_allocation(allocation_id):
    allocation = SellerInventory.query.get_or_404(allocation_id)
    seller_id = allocation.seller_id
    db.session.delete(allocation)
    db.session.commit()
    flash("Allocation removed.", "info")
    return redirect(url_for('admin_commerce.manage_seller_inventory', seller_id=seller_id))

# --- STOCK REQUESTS ---
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
    except Exception as e:
        print(f"Error sending stock approval email: {e}")
        traceback.print_exc()
    
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
    except Exception as e:
        print(f"Error sending stock rejection email: {e}")
        traceback.print_exc()
    
    flash('Request rejected.', 'warning')
    return redirect(url_for('admin_commerce.manage_stock_requests'))

# --- ORDERS ---
@admin_commerce_bp.route('/orders')
@login_required
@role_required('admin')
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    
    total_revenue = sum(order.total_amount for order in orders)
    pending_count = sum(1 for order in orders if order.status == 'Order Placed')
    completed_count = sum(1 for order in orders if order.status in ['Order Delivered', 'Order Dispatched'])

    return render_template('manage_orders.html', 
                           orders=orders,
                           total_revenue=total_revenue,
                           pending_count=pending_count,
                           completed_count=completed_count)

@admin_commerce_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order.status = new_status
    db.session.commit()
    
    # --- AUTOMATIC INVOICE GENERATION LOGIC ---
    attachments = None
    if new_status == 'Order Accepted':
        try:
            invoice = Invoice.query.filter_by(order_id=order.order_number).first()
            if not invoice:
                invoice = Invoice(
                    invoice_number=f"INV-{order.order_number}",
                    recipient_name=order.buyer.username,
                    recipient_email=order.buyer.email,
                    bill_to_address=order.billing_address,
                    ship_to_address=order.shipping_address, 
                    order_id=order.order_number,
                    subtotal=order.total_amount, 
                    tax=0.00,
                    total_amount=order.total_amount,
                    status='Unpaid',
                    admin_id=current_user.id,
                    created_at=datetime.utcnow(),
                    due_date=datetime.utcnow()
                )
                db.session.add(invoice)
                db.session.flush() 
                
                for order_item in order.items:
                    inv_item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=order_item.product_name,
                        quantity=order_item.quantity,
                        price=order_item.price_at_purchase
                    )
                    db.session.add(inv_item)
                db.session.commit()
            
            generator = InvoiceGenerator(invoice)
            pdf_bytes = generator.generate_pdf()
            
            attachments = [{
                'filename': f'Invoice_{invoice.invoice_number}.pdf',
                'data': pdf_bytes
            }]
            print(f"Invoice generated and attached for Order {order.order_number}")
            
        except Exception as e:
            print(f"Error generating invoice for Order {order.order_number}: {e}")
            traceback.print_exc()

    # --- EMAIL NOTIFICATION ---
    print(f"Attempting to send email to: {order.buyer.email}")
    try:
        send_email(
            to=order.buyer.email, 
            subject=f'Order Update: {new_status}', 
            template='mail/order_status_update.html', 
            buyer_name=order.buyer.username, 
            order_number=order.order_number, 
            status=new_status, 
            order_date=order.created_at.strftime('%Y-%m-%d'), 
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            now=datetime.utcnow(),
            attachments=attachments  
        )
        print("Email sent successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed to send order status email. Error: {e}")
        traceback.print_exc() 
    
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

@admin_commerce_bp.route('/invoices/mark_paid/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin')
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'Paid'
    
    if invoice.order_id:
        order = Order.query.filter_by(order_number=invoice.order_id).first()
        if order and order.status != 'Order Delivered':
             order.status = 'Payment Received'
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Invoice marked as Paid.'})
    
    flash('Invoice marked as Paid.', 'success')
    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/delete/<int:invoice_id>')
@login_required
@role_required('admin')
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
         return jsonify({'success': True, 'message': 'Invoice deleted.', 'remove_row_id': f'inv-{invoice_id}'})
    
    flash('Invoice deleted.', 'info')
    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/resend', methods=['POST'])
@login_required
@role_required('admin')
def resend_invoice():
    # Determine ID from form
    invoice_id = request.form.get('invoice_id')
    recipients = request.form.get('recipient_emails')
    
    if not invoice_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invoice ID missing.'})
        return redirect(url_for('admin_commerce.manage_invoices'))

    invoice = Invoice.query.get(invoice_id)
    
    try:
        generator = InvoiceGenerator(invoice)
        pdf_bytes = generator.generate_pdf()
        
        attachments = [{
            'filename': f'Invoice_{invoice.invoice_number}.pdf',
            'data': pdf_bytes
        }]
        
        recipient_list = [r.strip() for r in recipients.split(',')]
        
        for email_to in recipient_list:
             send_email(
                to=email_to,
                subject=f"Invoice #{invoice.invoice_number} from Source Point",
                template="mail/invoice_email.html",
                invoice=invoice,
                attachments=attachments
             )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Invoice resent successfully.'})
        flash("Invoice resent successfully.", "success")
        
    except Exception as e:
        print(f"Error resending invoice: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f"Error: {e}", "danger")

    return redirect(url_for('admin_commerce.manage_invoices'))

@admin_commerce_bp.route('/invoices/remind/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin')
def send_invoice_reminder(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    try:
        send_email(
            to=invoice.recipient_email,
            subject=f"Payment Reminder: Invoice #{invoice.invoice_number}",
            template="mail/reminder_invoice_email.html",
            invoice=invoice
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Reminder sent.'})
        flash("Reminder sent.", "success")
    except Exception as e:
         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
         flash(f"Error: {e}", "danger")
         
    return redirect(url_for('admin_commerce.manage_invoices'))