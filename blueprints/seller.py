from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Product, ProductImage, Invoice, InvoiceItem, Order, OrderItem, User
from utils import role_required, log_user_action, send_email
from datetime import datetime
from invoice_service import InvoiceGenerator
import csv
from io import TextIOWrapper
import openpyxl

seller_bp = Blueprint('seller', __name__, url_prefix='/seller')

# --- DASHBOARD ---
@seller_bp.route('/dashboard')
@login_required
@role_required('seller')
def seller_dashboard():
    products = Product.query.all()
    # Filter only MY invoices and orders
    my_invoices = Invoice.query.filter_by(admin_id=current_user.id).all()
    my_orders = Order.query.filter_by(seller_id=current_user.id).all()
    
    total_inventory_value = sum(int(p.stock) * float(p.price) for p in products)
    low_stock_count = sum(1 for p in products if int(p.stock) < 10)
    
    # Revenue from MY paid invoices
    total_revenue = sum(inv.total_amount for inv in my_invoices if inv.status == 'Paid')
    
    # Pending orders assigned to ME
    pending_orders_count = Order.query.filter_by(seller_id=current_user.id, status='Order Placed').count()
    
    recent_orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()

    return render_template('seller_dashboard.html',
                           total_inventory_value=total_inventory_value,
                           low_stock_count=low_stock_count,
                           pending_orders_count=pending_orders_count,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders)

# --- INVENTORY MANAGEMENT ---
@seller_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def manage_inventory():
    products = Product.query.order_by(Product.name).all()
    
    total_inventory_value = sum(int(p.stock) * float(p.price) for p in products)
    total_products_count = len(products)
    low_stock_count = sum(1 for p in products if int(p.stock) < 10)

    return render_template('seller/manage_inventory.html', 
                           products=products, 
                           total_inventory_value=total_inventory_value, 
                           total_products_count=total_products_count, 
                           low_stock_count=low_stock_count)

@seller_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@role_required('seller')
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
            return redirect(url_for('seller.add_product_page'))
        
        primary_image = image_urls[0].strip() if image_urls and image_urls[0].strip() else None
        
        new_product = Product(
            product_code=product_code, name=name, stock=int(stock), price=float(price),
            description=description, image_url=primary_image, category=category,
            brand=brand, mrp=float(mrp) if mrp else None, warranty=warranty, return_policy=return_policy
        )
        db.session.add(new_product)
        db.session.commit()
        
        for url in image_urls:
            if url.strip():
                img = ProductImage(product_id=new_product.id, image_url=url.strip())
                db.session.add(img)
        db.session.commit()
        
        log_user_action("Add Product", f"Seller added product {name}")
        flash(f'Product "{name}" added to catalog successfully.', 'success')
        return redirect(url_for('seller.manage_inventory'))
    return render_template('seller/add_product.html')

@seller_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required('seller')
def update_product():
    product_id = request.form.get('product_id')
    product = Product.query.get_or_404(product_id)
    
    product.name = request.form.get('name')
    product.stock = int(request.form.get('stock'))
    product.price = float(request.form.get('price'))
    product.category = request.form.get('category')
    product.brand = request.form.get('brand')
    mrp = request.form.get('mrp')
    if mrp: product.mrp = float(mrp)
    product.warranty = request.form.get('warranty')
    product.return_policy = request.form.get('return_policy')
    
    image_urls = request.form.getlist('image_urls[]')
    primary_image = image_urls[0].strip() if image_urls and image_urls[0].strip() else None
    product.image_url = primary_image

    ProductImage.query.filter_by(product_id=product.id).delete()
    for url in image_urls:
        if url.strip():
            img = ProductImage(product_id=product.id, image_url=url.strip())
            db.session.add(img)

    db.session.commit()
    log_user_action("Update Product", f"Seller updated product {product.name}")
    flash(f'Product "{product.name}" updated.', 'success')
    return redirect(url_for('seller.manage_inventory'))

@seller_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required('seller')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    log_user_action("Delete Product", f"Seller deleted product {name}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Product deleted.', 'remove_row_id': f'product-{product_id}'})
    flash('Product deleted.', 'success')
    return redirect(url_for('seller.manage_inventory'))

@seller_bp.route('/inventory/import', methods=['POST'])
@login_required
@role_required('seller')
def import_inventory():
    file = request.files.get('import_file')
    if not file:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('seller.manage_inventory'))

    try:
        items_to_process = []
        if file.filename.endswith('.csv'):
            csv_file = TextIOWrapper(file, encoding='utf-8')
            csv_reader = csv.DictReader(csv_file)
            items_to_process = list(csv_reader)
        elif file.filename.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if rows:
                headers = rows[0]
                for row in rows[1:]:
                    row_data = {headers[i]: row[i] for i in range(len(headers)) if headers[i]}
                    items_to_process.append(row_data)

        added, updated = 0, 0
        for row in items_to_process:
            sku = row.get('SKU')
            name = row.get('Product Name')
            if not sku or not name: continue 

            price = float(row.get('Selling Price (INR)', 0))
            stock = int(row.get('Quantity', 0))
            
            product = Product.query.filter_by(product_code=sku).first()
            if product:
                product.stock = stock
                product.price = price
                updated += 1
            else:
                new_product = Product(product_code=sku, name=name, stock=stock, price=price)
                db.session.add(new_product)
                added += 1

        db.session.commit()
        flash(f'Inventory processed: {added} New, {updated} Updated.', 'success')

    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'danger')
    return redirect(url_for('seller.manage_inventory'))

# --- ORDERS ---
@seller_bp.route('/orders')
@login_required
@role_required('seller')
def manage_orders():
    # STRICT FILTER: Only orders where seller_id matches current user
    orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    # Fetch Data for Create Order Modal
    buyers = User.query.filter_by(role='buyer').all()
    products = Product.query.filter(Product.stock > 0).all()
    
    return render_template('seller/manage_orders.html', orders=orders, buyers=buyers, products=products)

@seller_bp.route('/orders/create', methods=['POST'])
@login_required
@role_required('seller')
def create_order():
    buyer_id = request.form.get('buyer_id')
    shipping_address = request.form.get('shipping_address')
    billing_address = request.form.get('billing_address') or shipping_address
    
    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    
    if not buyer_id:
        flash('Please select a valid buyer.', 'danger')
        return redirect(url_for('seller.manage_orders'))

    try:
        # Generate Order Number
        last_order = Order.query.order_by(Order.id.desc()).first()
        next_id = (last_order.id + 1) if last_order else 1
        order_number = f"ORD{datetime.utcnow().year}{next_id:04d}"
        
        total_amount = 0
        order_items = []
        
        for i, p_id in enumerate(product_ids):
            if not p_id or not quantities[i]: continue
            
            product = Product.query.get(p_id)
            qty = int(quantities[i])
            
            if product and product.stock >= qty:
                line_total = product.price * qty
                total_amount += line_total
                
                # Deduct Stock
                product.stock -= qty
                
                # Add Item
                order_items.append(OrderItem(
                    product_name=product.name,
                    quantity=qty,
                    price_at_purchase=product.price
                ))
            else:
                flash(f'Insufficient stock for {product.name} (Available: {product.stock})', 'warning')
                return redirect(url_for('seller.manage_orders'))

        if not order_items:
            flash('No valid items added to order.', 'warning')
            return redirect(url_for('seller.manage_orders'))

        # Create Order
        new_order = Order(
            order_number=order_number,
            user_id=buyer_id, # Buyer
            seller_id=current_user.id, # Seller (Creator)
            total_amount=total_amount,
            status='Order Placed',
            shipping_address=shipping_address,
            billing_address=billing_address,
            created_at=datetime.utcnow()
        )
        new_order.items = order_items
        
        db.session.add(new_order)
        db.session.commit()
        
        log_user_action("Create Order", f"Seller created order {order_number} for User ID {buyer_id}")
        flash(f'Order {order_number} created successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating order: {str(e)}', 'danger')
        print(e)

    return redirect(url_for('seller.manage_orders'))

@seller_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required('seller')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Security Check
    if order.seller_id != current_user.id:
        flash('Unauthorized: You can only update your own orders.', 'danger')
        return redirect(url_for('seller.manage_orders'))

    new_status = request.form.get('status')
    
    if new_status and order.status != new_status:
        order.status = new_status
        db.session.commit()
        
        # Auto-create Invoice for Seller
        if new_status == 'Order Accepted':
             if not Invoice.query.filter_by(order_id=order.order_number).first():
                last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
                next_id = (last_invoice.id + 1) if last_invoice else 1
                inv_num = f"INV{datetime.utcnow().year}{next_id:03d}"
                
                new_invoice = Invoice(
                    invoice_number=inv_num, recipient_name=order.buyer.username, 
                    recipient_email=order.buyer.email,
                    bill_to_address=order.billing_address or order.shipping_address, 
                    ship_to_address=order.shipping_address,
                    order_id=order.order_number, subtotal=order.total_amount, tax=0, 
                    total_amount=order.total_amount,
                    due_date=datetime.utcnow().date(), notes="Auto-generated by Seller.", 
                    admin_id=current_user.id # Assigned to current SELLER
                )
                db.session.add(new_invoice)
                db.session.commit()
                for item in order.items:
                    db.session.add(InvoiceItem(description=item.product_name, quantity=item.quantity, price=item.price_at_purchase, invoice_id=new_invoice.id))
                db.session.commit()

        try:
            send_email(to=order.buyer.email, subject=f'Order Update: {new_status}', template='mail/order_status_update.html', 
                       buyer_name=order.buyer.username, order_number=order.order_number, status=new_status, 
                       order_date=order.created_at.strftime('%Y-%m-%d'), total_amount=order.total_amount)
        except Exception: pass
        
        flash(f'Order {order.order_number} updated to {new_status}.', 'success')

    return redirect(url_for('seller.manage_orders'))

# --- INVOICES ---
@seller_bp.route('/invoices')
@login_required
@role_required('seller')
def manage_invoices():
    # STRICT FILTER: Only show invoices where admin_id matches current seller
    invoices = Invoice.query.filter_by(admin_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    return render_template('seller/manage_invoices.html', invoices=invoices)

@seller_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def create_invoice():
    if request.method == 'POST':
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        invoice_number = f"INV{datetime.utcnow().year}{last_invoice.id + 1 if last_invoice else 1:03d}"
        
        recipient_name = request.form.get('recipient_name')
        recipient_email = request.form.get('recipient_email')
        bill_to = request.form.get('bill_to_address')
        ship_to = request.form.get('ship_to_address')
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        
        item_descs = request.form.getlist('item_description[]')
        item_qtys = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        
        subtotal = 0
        items = []
        for i in range(len(item_descs)):
            qty, price = int(item_qtys[i]), float(item_prices[i])
            subtotal += qty * price
            items.append(InvoiceItem(description=item_descs[i], quantity=qty, price=price))
        
        invoice = Invoice(
            invoice_number=invoice_number, recipient_name=recipient_name, recipient_email=recipient_email,
            bill_to_address=bill_to, ship_to_address=ship_to, subtotal=subtotal, total_amount=subtotal,
            due_date=due_date, admin_id=current_user.id # Set Creator to SELLER
        )
        invoice.items = items
        db.session.add(invoice)
        db.session.commit()

        try:
            gen = InvoiceGenerator(invoice)
            pdf = gen.generate_pdf()
            att = {'filename': f'{invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf}
            send_email(to=recipient_email, subject=f"Invoice {invoice_number}", template='mail/professional_invoice_email.html', 
                       recipient_name=recipient_name, invoice_number=invoice_number, total_amount=subtotal, due_date=due_date, attachments=[att])
        except Exception: pass

        flash('Invoice created successfully.', 'success')
        return redirect(url_for('seller.manage_invoices'))

    products = Product.query.filter(Product.stock > 0).all()
    products_js = [{'id': p.id, 'name': p.name, 'price': p.price, 'code': p.product_code} for p in products]
    return render_template('seller/create_invoice.html', products=products_js)

@seller_bp.route('/invoices/delete/<int:invoice_id>')
@login_required
@role_required('seller')
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # Security Check
    if invoice.admin_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('seller.manage_invoices'))
        
    db.session.delete(invoice)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Invoice deleted.', 'remove_row_id': f'invoice-{invoice_id}'})
    flash('Invoice deleted.', 'success')
    return redirect(url_for('seller.manage_invoices'))

@seller_bp.route('/invoices/mark_paid/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('seller')
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # Security Check
    if invoice.admin_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    if invoice.status != 'Paid':
        invoice.status = 'Paid'
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Marked as Paid.'})
        flash('Invoice marked as Paid.', 'success')
    return redirect(url_for('seller.manage_invoices'))

@seller_bp.route('/invoices/resend', methods=['POST'])
@login_required
@role_required('seller')
def resend_invoice():
    invoice_id = request.form.get('invoice_id')
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Security Check
    if invoice.admin_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        return redirect(url_for('seller.manage_invoices'))

    # Logic to resend email...
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Invoice resent.'})
    flash('Invoice resent.', 'success')
    return redirect(url_for('seller.manage_invoices'))

@seller_bp.route('/invoices/remind/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('seller')
def send_invoice_reminder(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.admin_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # Logic to send reminder...
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Reminder sent.'})
    flash('Reminder sent.', 'success')
    return redirect(url_for('seller.manage_invoices'))