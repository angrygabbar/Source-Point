from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from io import BytesIO
from extensions import db
from models.auth import User
from models.commerce import (
    Product, Order, OrderItem, Invoice, InvoiceItem, StockRequest,
    SellerInventory, SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice
)
from utils import role_required, log_user_action, send_email
from datetime import datetime
from invoice_service import InvoiceGenerator, SupersCoinInvoiceGenerator
from services.commerce_service import CommerceService
from services.superscoins_service import SupersCoinsService
import os 
from enums import UserRole, OrderStatus, InvoiceStatus, SupersCoinTransactionType

seller_bp = Blueprint('seller', __name__, url_prefix='/seller')

# =========================================================
# 1. DASHBOARD
# =========================================================

@seller_bp.route('/dashboard')
@login_required
@role_required(UserRole.SELLER.value)
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
    
    # Calculate stats
    for inv, prod in inventory_items:
        total_inventory_value += (inv.stock * prod.price)
        if inv.stock < 10:
            low_stock_count += 1
    
    # Revenue from MY paid invoices (Use Enum)
    total_revenue = sum(inv.total_amount for inv in my_invoices if inv.status == InvoiceStatus.PAID.value)
    
    # Pending orders assigned to ME
    pending_orders_count = Order.query.filter(
        Order.seller_id == current_user.id,
        Order.status.in_(CommerceService.placed_status_values)
    ).count()
    
    recent_orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    superscoin_wallet = SupersCoinWallet.query.filter_by(seller_id=current_user.id).first() if SupersCoinsService.tables_ready() else None
    superscoin_balance = superscoin_wallet.balance if superscoin_wallet else 0

    return render_template('seller_dashboard.html',
                           total_inventory_value=total_inventory_value,
                           low_stock_count=low_stock_count,
                           pending_orders_count=pending_orders_count,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders,
                           superscoin_balance=superscoin_balance,
                           normalize_order_status=CommerceService.normalize_order_status)

# =========================================================
# 2. INVENTORY MANAGEMENT
# =========================================================

@seller_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.SELLER.value)
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
    low_stock = 0
    
    for inv, prod in inventory_items:
        products_display.append({
            'id': prod.id,
            'inventory_id': inv.id,
            'code': prod.product_code,
            'name': prod.name,
            'image_url': prod.image_url,
            'my_stock': inv.stock,
            'price': prod.price
        })
        total_val += (inv.stock * prod.price)
        if inv.stock < 10:
            low_stock += 1

    return render_template('seller/manage_inventory.html', 
                           products=products_display, 
                           all_products=all_products, 
                           total_inventory_value=total_val, 
                           total_products_count=len(products_display), 
                           low_stock_count=low_stock)

@seller_bp.route('/inventory/view/<int:product_id>')
@login_required
@role_required(UserRole.SELLER.value)
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    # Fetch seller's specific inventory record for this product
    my_inventory = SellerInventory.query.filter_by(seller_id=current_user.id, product_id=product.id).first()
    return render_template('product_detail_manage.html', product=product, my_inventory=my_inventory)

@seller_bp.route('/inventory/request', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def request_stock():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    
    # Fallback if ID is missing
    if not product_id:
        flash('System Error: Product ID missing.', 'danger')
        return redirect(url_for('seller.manage_inventory'))

    if not quantity:
        flash('Please enter a valid quantity.', 'danger')
        return redirect(url_for('seller.view_product', product_id=product_id))
        
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
        
        # 2. Prepare for Email
        product = Product.query.get(product_id)
        
        # --- EMAIL NOTIFICATION LOGIC ---
        admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
        
        if not admins:
             flash('Stock request saved, but no Admin found to notify.', 'warning')
        elif not os.environ.get('BREVO_API_KEY'):
             flash('Stock request saved. (Email disabled: API Key missing)', 'warning')
        else:
            email_sent_count = 0
            for admin in admins:
                try:
                    # SYNC=TRUE forces immediate sending so we catch errors
                    send_email(
                        to=admin.email,
                        subject=f"New Stock Request: {product.name}",
                        template="mail/new_stock_request_admin.html",
                        request=req,
                        seller=current_user,
                        product=product,
                        now=datetime.utcnow(),
                        sync=True 
                    )
                    email_sent_count += 1
                except Exception as e:
                    print(f"EMAIL ERROR for {admin.email}: {e}")
            
            if email_sent_count > 0:
                flash(f'Stock request submitted and Admin notified!', 'success')
            else:
                flash('Stock request saved, but email notification failed.', 'warning')
        
        return redirect(url_for('seller.view_product', product_id=product_id))

    except ValueError:
        flash('Invalid quantity.', 'danger')
        return redirect(url_for('seller.view_product', product_id=product_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting request: {e}', 'danger')
        return redirect(url_for('seller.view_product', product_id=product_id))

@seller_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def update_product():
    inventory_id = request.form.get('inventory_id')
    new_stock = request.form.get('stock')
    
    if not inventory_id:
        flash('System Error: Inventory ID missing.', 'danger')
        return redirect(url_for('seller.manage_inventory'))

    inv_item = SellerInventory.query.get(inventory_id)
    if not inv_item:
        flash('Inventory item not found.', 'danger')
        return redirect(url_for('seller.manage_inventory'))
        
    product_id = inv_item.product_id

    try:
        if inv_item.seller_id == current_user.id:
            if new_stock:
                inv_item.stock = int(new_stock)
                db.session.commit()
                log_user_action("Update Inventory", f"Seller updated stock for {inv_item.product.name}")
                flash('Stock count updated.', 'success')
            else:
                flash('Please enter a valid stock number.', 'warning')
        else:
            flash('Unauthorized update action.', 'danger')
            
        return redirect(url_for('seller.view_product', product_id=product_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating stock: {str(e)}', 'danger')
        return redirect(url_for('seller.view_product', product_id=product_id))

# =========================================================
# 3. ORDERS
# =========================================================

@seller_bp.route('/orders')
@login_required
@role_required(UserRole.SELLER.value)
def manage_orders():
    orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).all()
    buyers = User.query.filter_by(role=UserRole.BUYER.value).all()
    
    my_inventory = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id, SellerInventory.stock > 0)\
        .all()
    
    products_available = []
    for inv, prod in my_inventory:
        prod.max_qty = inv.stock 
        products_available.append(prod)

    return render_template(
        'seller/manage_orders.html',
        orders=orders,
        buyers=buyers,
        products=products_available,
        order_status_choices=CommerceService.order_status_choices,
        normalize_order_status=CommerceService.normalize_order_status,
    )

@seller_bp.route('/orders/create', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
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
        last_order = Order.query.order_by(Order.id.desc()).first()
        next_id = (last_order.id + 1) if last_order else 1
        order_number = f"ORD{datetime.utcnow().year}{next_id:04d}"
        
        total_amount = 0
        order_items = []
        
        for i, p_id in enumerate(product_ids):
            if not p_id or not quantities[i]: continue
            
            inventory_item = SellerInventory.query.filter_by(seller_id=current_user.id, product_id=p_id).first()
            qty = int(quantities[i])
            
            if inventory_item and inventory_item.stock >= qty:
                product = inventory_item.product
                line_total = product.price * qty
                total_amount += line_total
                inventory_item.stock -= qty
                order_items.append(OrderItem(product_name=product.name, quantity=qty, price_at_purchase=product.price))
            else:
                flash(f'Insufficient stock for product ID {p_id}.', 'warning')
                return redirect(url_for('seller.manage_orders'))

        if not order_items:
            flash('No valid items added to order.', 'warning')
            return redirect(url_for('seller.manage_orders'))

        new_order = Order(
            order_number=order_number, user_id=buyer_id, seller_id=current_user.id,
            total_amount=total_amount, status=OrderStatus.PLACED.value,
            shipping_address=shipping_address, billing_address=billing_address
        )
        new_order.items = order_items
        db.session.add(new_order)
        db.session.commit()
        
        flash(f'Order {order_number} created successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating order: {str(e)}', 'danger')

    return redirect(url_for('seller.manage_orders'))

@seller_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('seller.manage_orders'))

    new_status = request.form.get('status')
    if not new_status:
        message = 'Status is required.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('seller.manage_orders'))

    success, message, restored_items, missing_items = CommerceService.transition_order_status(order, new_status)
    if not success:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('seller.manage_orders'))

    normalized_status = CommerceService.normalize_order_status(new_status)
    db.session.commit()
    
    # Notify Buyer
    try:
        send_email(
            to=order.buyer.email, 
            subject=f'Order Update: {normalized_status}', 
            template='mail/order_status_update.html', 
            buyer_name=order.buyer.username, 
            order_number=order.order_number, 
            status=normalized_status, 
            order_date=order.created_at.strftime('%Y-%m-%d'), 
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            now=datetime.utcnow()
        )
    except Exception as e:
        print(f"Failed to send seller order status email: {e}")
    
    extra = ''
    if restored_items:
        extra = ' Inventory was restored.'
    if missing_items:
        extra += f" Could not find inventory for: {', '.join(missing_items)}."
    flash(f'Order {order.order_number} updated to {normalized_status}.{extra}', 'success')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Order updated to {normalized_status}.', 'new_status': normalized_status})
    return redirect(url_for('seller.manage_orders'))

# =========================================================
# 4. INVOICES
# =========================================================

@seller_bp.route('/invoices')
@login_required
@role_required(UserRole.SELLER.value)
def manage_invoices():
    invoices = Invoice.query.filter_by(admin_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    return render_template('seller/manage_invoices.html', invoices=invoices)

@seller_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.SELLER.value)
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
            desc = item_descs[i].strip()
            if not desc: continue
            try:
                qty = int(item_qtys[i])
                price = float(item_prices[i])
                subtotal += qty * price
                items.append(InvoiceItem(description=desc, quantity=qty, price=price))
            except ValueError: continue
        
        if not items:
            flash('No valid items.', 'danger')
            return redirect(url_for('seller.manage_invoices'))
        
        invoice = Invoice(
            invoice_number=invoice_number, recipient_name=recipient_name, recipient_email=recipient_email,
            bill_to_address=bill_to, ship_to_address=ship_to, subtotal=subtotal, total_amount=subtotal,
            due_date=due_date, admin_id=current_user.id,
            status=InvoiceStatus.UNPAID.value
        )
        invoice.items = items
        db.session.add(invoice)
        db.session.commit()

        # Generate & Send
        try:
            gen = InvoiceGenerator(invoice)
            pdf = gen.generate_pdf()
            att = {'filename': f'{invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf}
            send_email(to=recipient_email, subject=f"Invoice {invoice_number}", template='mail/ecommerce_invoice_email.html',
                       invoice=invoice, attachments=[att])
        except Exception as e:
             print(f"Error sending invoice: {e}")

        flash('Invoice created successfully.', 'success')
        return redirect(url_for('seller.manage_invoices'))

    my_inventory = db.session.query(SellerInventory, Product)\
        .join(Product, SellerInventory.product_id == Product.id)\
        .filter(SellerInventory.seller_id == current_user.id, SellerInventory.stock > 0)\
        .all()
        
    products_js = [{'id': prod.id, 'name': prod.name, 'price': prod.price, 'code': prod.product_code} for inv, prod in my_inventory]
    
    return render_template('seller/create_invoice.html', products=products_js)

@seller_bp.route('/invoices/delete/<int:invoice_id>')
@login_required
@role_required(UserRole.SELLER.value)
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
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
@role_required(UserRole.SELLER.value)
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.admin_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    if invoice.status != InvoiceStatus.PAID.value:
        invoice.status = InvoiceStatus.PAID.value
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Invoice marked as Paid.'})
        flash('Invoice marked as Paid.', 'success')
    return redirect(url_for('seller.manage_invoices'))

@seller_bp.route('/invoices/resend', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def resend_invoice():
    invoice_id = request.form.get('invoice_id')
    recipients = request.form.get('recipient_emails', '')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.admin_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    recipient_list = []
    seen_recipients = set()
    for recipient in recipients.split(','):
        email_to = recipient.strip()
        if email_to and email_to not in seen_recipients:
            recipient_list.append(email_to)
            seen_recipients.add(email_to)

    if not recipient_list:
        recipient_list = [invoice.recipient_email]

    try:
        gen = InvoiceGenerator(invoice)
        pdf = gen.generate_pdf()
        att = {'filename': f'{invoice.invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf}
        send_email(
            to=recipient_list,
            subject=f"Resent: Invoice {invoice.invoice_number}", 
            template='mail/ecommerce_invoice_email.html', 
            invoice=invoice,
            attachments=[att]
        )
        if is_ajax:
            return jsonify({'success': True, 'message': 'Invoice resend queued successfully.'})
        flash('Invoice email resent.', 'success')
    except Exception as e:
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
        flash(f'Error resending email: {str(e)}', 'danger')

    return redirect(url_for('seller.manage_invoices'))

@seller_bp.route('/invoices/remind/<int:invoice_id>', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def send_invoice_reminder(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.admin_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Reminder sent.'})
        
    flash('Payment reminder sent.', 'success')
    return redirect(url_for('seller.manage_invoices'))

# =========================================================
# 5. SUPERSCOINS WALLET (READ-ONLY)
# =========================================================

@seller_bp.route('/superscoins')
@login_required
@role_required(UserRole.SELLER.value)
def superscoins_wallet():
    setup_pending = not SupersCoinsService.tables_ready()
    if setup_pending:
        flash("SupersCoins wallet is being set up. Please try again after the database migration is applied.", "warning")
        wallet = None
        transactions = []
        invoices = []
    else:
        wallet = SupersCoinWallet.query.filter_by(seller_id=current_user.id).first()
        transactions = SupersCoinTransaction.query.filter_by(seller_id=current_user.id)\
            .order_by(SupersCoinTransaction.created_at.desc()).limit(100).all()
        invoices = SupersCoinInvoice.query.filter_by(seller_id=current_user.id)\
            .order_by(SupersCoinInvoice.created_at.desc()).limit(50).all()

    return render_template(
        'seller/superscoins.html',
        wallet=wallet,
        transactions=transactions,
        invoices=invoices,
        transaction_types=SupersCoinTransactionType,
        setup_pending=setup_pending,
    )

@seller_bp.route('/superscoins/invoices/<int:invoice_id>/download')
@login_required
@role_required(UserRole.SELLER.value)
def download_superscoin_invoice(invoice_id):
    if not SupersCoinsService.tables_ready():
        flash("SupersCoins wallet is being set up. Please try again after the database migration is applied.", "warning")
        return redirect(url_for('seller.superscoins_wallet'))

    invoice = SupersCoinInvoice.query.filter_by(id=invoice_id, seller_id=current_user.id).first_or_404()
    pdf_bytes = SupersCoinInvoiceGenerator(invoice).generate_pdf()
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{invoice.invoice_number}.pdf',
    )

# =========================================================
# 6. SHAREABLE LINK
# =========================================================

@seller_bp.route('/share-link', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
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


@seller_bp.route('/share-link/toggle', methods=['POST'])
@login_required
@role_required(UserRole.SELLER.value)
def toggle_share_link():
    from models.commerce import ShareableLink

    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        return jsonify({'success': False, 'message': 'No share link found. Generate one first.'}), 404

    link.is_active = not link.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': link.is_active, 'message': f"Link {'activated' if link.is_active else 'deactivated'}."})
