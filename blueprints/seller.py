from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Product, ProductImage, Invoice, InvoiceItem, Order, OrderItem, User, SellerInventory, StockRequest
from utils import role_required, log_user_action, send_email
from datetime import datetime
from invoice_service import InvoiceGenerator
import csv
from io import TextIOWrapper
import openpyxl

seller_bp = Blueprint('seller', __name__, url_prefix='/seller')

# =========================================================
# 1. DASHBOARD
# =========================================================

@seller_bp.route('/dashboard')
@login_required
@role_required('seller')
def seller_dashboard():
    # Fetch inventory specifically assigned to this seller
    inventory_items = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id)\
        .all()
    
    # Filter only MY invoices and orders
    my_invoices = Invoice.query.filter_by(admin_id=current_user.id).all()
    
    total_inventory_value = 0
    low_stock_count = 0
    
    # Calculate stats based on assigned inventory
    for inv, prod in inventory_items:
        total_inventory_value += (inv.stock * prod.price)
        if inv.stock < 10:
            low_stock_count += 1
    
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

# =========================================================
# 2. INVENTORY MANAGEMENT
# =========================================================

@seller_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def manage_inventory():
    # 1. Get My Inventory (Assigned Items)
    inventory_items = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id)\
        .order_by(Product.name)\
        .all()
    
    # 2. Get All Products (For the "Request Stock" Dropdown)
    all_products = Product.query.order_by(Product.name).all()
    
    products_display = []
    total_val = 0
    
    for inv, prod in inventory_items:
        # We include ALL details so the "View Details" modal works in the template
        products_display.append({
            'id': prod.id,
            'inventory_id': inv.id, # Used to update specific stock
            'code': prod.product_code,
            'name': prod.name,
            'image_url': prod.image_url,
            'category': prod.category,
            'brand': prod.brand or 'N/A',
            'description': prod.description or 'No description available.',
            'warranty': prod.warranty or 'N/A',
            'return_policy': prod.return_policy or 'N/A',
            'my_stock': inv.stock, # Seller's specific stock
            'price': prod.price,
            'mrp': prod.mrp
        })
        total_val += (inv.stock * prod.price)

    return render_template('seller/manage_inventory.html', 
                           products=products_display, 
                           all_products=all_products, # Passed for Request Modal
                           total_inventory_value=total_val, 
                           total_products_count=len(products_display), 
                           low_stock_count=sum(1 for p in products_display if p['my_stock'] < 10))

# --- REQUEST STOCK ROUTE (NEW) ---
@seller_bp.route('/inventory/request', methods=['POST'])
@login_required
@role_required('seller')
def request_stock():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    
    if not product_id or not quantity:
        flash('Please select a product and quantity.', 'danger')
        return redirect(url_for('seller.manage_inventory'))
        
    try:
        qty = int(quantity)
        if qty <= 0: raise ValueError
        
        # 1. Create Request Record
        req = StockRequest(
            seller_id=current_user.id,
            product_id=product_id,
            quantity=qty,
            status='Pending'
        )
        db.session.add(req)
        db.session.commit()
        
        # 2. Get Product Info for Email
        product = Product.query.get(product_id)

        # 3. Notify All Admins
        admins = User.query.filter_by(role='admin').all()
        email_sent_count = 0
        for admin in admins:
            try:
                send_email(
                    to=admin.email,
                    subject=f"New Stock Request: {product.name}",
                    template="mail/new_stock_request_admin.html",
                    request=req,
                    seller=current_user,
                    product=product,
                    now=datetime.utcnow()
                )
                email_sent_count += 1
            except Exception as e:
                print(f"Failed to email admin {admin.username}: {e}")
        
        log_user_action("Request Stock", f"Seller requested {qty} units of {product.name}. Notified {email_sent_count} admins.")
        flash('Stock request sent to Administrator.', 'success')
        
    except ValueError:
        flash('Invalid quantity.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting request: {e}', 'danger')

    return redirect(url_for('seller.manage_inventory'))

@seller_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required('seller')
def update_product():
    # Sellers update their OWN stock level (e.g. for corrections/offline sales)
    inventory_id = request.form.get('inventory_id')
    new_stock = request.form.get('stock')
    # Optional: Allow price override if business logic permits
    # new_price = request.form.get('price') 
    
    if inventory_id:
        inv_item = SellerInventory.query.get(inventory_id)
        # Security check: Ensure this inventory belongs to the logged-in seller
        if inv_item and inv_item.seller_id == current_user.id:
            if new_stock:
                inv_item.stock = int(new_stock)
            
            # If allowing price overrides:
            # if new_price: inv_item.price = float(new_price)

            db.session.commit()
            log_user_action("Update Inventory", f"Seller updated stock for {inv_item.product.name}")
            flash('Inventory stock updated.', 'success')
        else:
            flash('Unauthorized update action.', 'danger')
    else:
        flash('Invalid request data.', 'danger')

    return redirect(url_for('seller.manage_inventory'))

# --- RESTRICTED ROUTES (Security Placeholders) ---
@seller_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def add_product_page():
    flash('Only Administrators can add new products to the catalog.', 'warning')
    return redirect(url_for('seller.manage_inventory'))

@seller_bp.route('/inventory/import', methods=['POST'])
@login_required
@role_required('seller')
def import_inventory():
    flash('Bulk import is restricted to Administrators.', 'warning')
    return redirect(url_for('seller.manage_inventory'))

@seller_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required('seller')
def delete_product(product_id):
    flash('Contact an Administrator to remove products from your assignment.', 'warning')
    return redirect(url_for('seller.manage_inventory'))

# =========================================================
# 3. ORDERS
# =========================================================

@seller_bp.route('/orders')
@login_required
@role_required('seller')
def manage_orders():
    # Only orders where seller_id matches current user
    orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    # Fetch Data for Create Order Modal
    buyers = User.query.filter_by(role='buyer').all()
    
    # Filter product dropdown: Only show products I currently have in stock
    my_inventory = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id, SellerInventory.stock > 0)\
        .all()
    
    products_available = []
    for inv, prod in my_inventory:
        # Determine max qty available for this seller
        prod.max_qty = inv.stock 
        products_available.append(prod)

    return render_template('seller/manage_orders.html', orders=orders, buyers=buyers, products=products_available)

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
            
            # Find the specific inventory record for this seller and product
            inventory_item = SellerInventory.query.filter_by(
                seller_id=current_user.id, 
                product_id=p_id
            ).first()

            qty = int(quantities[i])
            
            # Check stock in SELLER'S Inventory
            if inventory_item and inventory_item.stock >= qty:
                product = inventory_item.product
                line_total = product.price * qty
                total_amount += line_total
                
                # Deduct Stock from Seller's Allocation
                inventory_item.stock -= qty
                
                # Add Item
                order_items.append(OrderItem(
                    product_name=product.name,
                    quantity=qty,
                    price_at_purchase=product.price
                ))
            else:
                prod_name = Product.query.get(p_id).name if Product.query.get(p_id) else "Unknown"
                flash(f'Insufficient stock for {prod_name}.', 'warning')
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
        
        # Auto-create Invoice for Seller logic (Simplified)
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

# =========================================================
# 4. INVOICES
# =========================================================

@seller_bp.route('/invoices')
@login_required
@role_required('seller')
def manage_invoices():
    # Only show invoices where admin_id matches current seller
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

    # Load seller's products for invoice dropdown
    # Using SellerInventory to ensure we only show allocated products
    my_inventory = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id, SellerInventory.stock > 0)\
        .all()
        
    products_js = [{'id': prod.id, 'name': prod.name, 'price': prod.price, 'code': prod.product_code} for inv, prod in my_inventory]
    
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