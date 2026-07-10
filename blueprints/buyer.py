from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from extensions import db, cache
from models.commerce import Product, Cart, Order, VoucherOrder
from models.auth import User
from models.gift_card import GiftCard
from services.commerce_service import CommerceService      
from utils import role_required, send_email
from forms.commerce_forms import CheckoutForm
from sqlalchemy import or_
from enums import GiftCardStatus, VoucherOrderStatus, UserRole, OrderStatus
from datetime import datetime

buyer_bp = Blueprint('buyer', __name__)

def is_htmx():
    """Returns True if the request is an HTMX request."""
    return request.headers.get('HX-Request') is not None

@buyer_bp.route('/buyer')
@login_required
@role_required('buyer')
def buyer_dashboard():
    # 1. Filters & Search
    category_filter = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 24

    # 2. Build Query
    query = Product.query.filter(Product.stock > 0).order_by(Product.stock.desc(), Product.id.desc())

    if search_query:
        query = query.filter(or_(
            Product.name.ilike(f'%{search_query}%'),
            Product.description.ilike(f'%{search_query}%'),
            Product.category.ilike(f'%{search_query}%')
        ))

    if category_filter:
        query = query.filter_by(category=category_filter)

    # Paginate — only load 24 products at a time instead of ALL
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # 3. Optimized Categories (Redis with graceful fallback)
    categories = None
    try:
        categories = cache.get('all_product_categories')
    except Exception as e:
        print(f"[WARN] Cache GET failed (Redis unreachable?): {e}")

    if categories is None:
        categories_query = db.session.query(Product.category).distinct().all()
        categories = [c[0] for c in categories_query if c[0]]
        try:
            cache.set('all_product_categories', categories, timeout=3600)
        except Exception as e:
            print(f"[WARN] Cache SET failed (Redis unreachable?): {e}")

    # 4. Global Data
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    cart_count = len(cart.items) if cart else 0

    return render_template('buyer_dashboard.html',
                           products=products,
                           pagination=pagination,
                           categories=categories,
                           current_category=category_filter,

                           cart_count=cart_count,
                           search_query=search_query,
                           partial=is_htmx())

@buyer_bp.route('/product/<int:product_id>')
@login_required
@role_required('buyer')
def product_detail_page(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail_buyer.html', 
                           product=product, 
                           partial=is_htmx())

@buyer_bp.route('/cart')
@login_required
@role_required('buyer')
def view_cart():
    cart_items, total, _ = CommerceService.get_cart_details(current_user.id)
    return render_template('cart.html', 
                           cart_items=cart_items, 
                           total=total, 
                           partial=is_htmx())

@buyer_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
@role_required('buyer')
def add_to_cart(product_id):
    success, msg = CommerceService.add_to_cart(current_user.id, product_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('buyer.buyer_dashboard'))

@buyer_bp.route('/remove_from_cart/<int:item_id>')
@login_required
@role_required('buyer')
def remove_from_cart(item_id):
    success, msg = CommerceService.remove_item(current_user.id, item_id)
    flash(msg, 'info' if success else 'danger')
    return redirect(url_for('buyer.view_cart'))

@buyer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@role_required('buyer')
def checkout():
    _, total, cart = CommerceService.get_cart_details(current_user.id)
    if not cart or not cart.items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.buyer_dashboard'))

    form = CheckoutForm()
    if form.validate_on_submit():
        order, msg = CommerceService.process_checkout(
            user_id=current_user.id,
            shipping_address=form.shipping_address.data,
            billing_address=form.billing_address.data
        )
        if order:
            flash(msg, 'success')
            return redirect(url_for('buyer.my_orders'))
        
        flash(msg, 'danger')
        return redirect(url_for('buyer.view_cart'))
    
    return render_template('checkout.html', total=total, form=form, partial=is_htmx())

@buyer_bp.route('/my_orders')
@login_required
@role_required('buyer')
def my_orders():
    from sqlalchemy.orm import joinedload
    orders = Order.query.options(joinedload(Order.items))\
                .filter_by(user_id=current_user.id)\
                .order_by(Order.created_at.desc()).all()
    return render_template(
        'my_orders.html',
        orders=orders,
        partial=is_htmx(),
        can_cancel_order=CommerceService.can_buyer_cancel_order,
        normalize_order_status=CommerceService.normalize_order_status,
    )

@buyer_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@role_required('buyer')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if order.user_id != current_user.id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
        abort(403)

    if not CommerceService.can_buyer_cancel_order(order):
        message = 'This order can no longer be cancelled from your account.'
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'warning')
        return redirect(url_for('buyer.my_orders'))

    success, message, restored_items, missing_items = CommerceService.transition_order_status(
        order,
        OrderStatus.CANCELLED.value
    )
    if not success:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('buyer.my_orders'))

    db.session.commit()

    try:
        send_email(
            to=current_user.email,
            subject=f"Order Cancelled: {order.order_number}",
            template="mail/order_status_update.html",
            buyer_name=current_user.username,
            order_number=order.order_number,
            status=OrderStatus.CANCELLED.value,
            order_date=order.created_at.strftime('%B %d, %Y'),
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            message="Your order has been cancelled. Reserved inventory has been released.",
            now=datetime.utcnow()
        )
    except Exception as e:
        print(f"Failed to send cancellation email: {e}")

    notice = 'Order cancelled successfully.'
    if missing_items:
        notice += f" Inventory could not be restored for: {', '.join(missing_items)}."

    if is_ajax:
        return jsonify({'success': True, 'message': notice, 'new_status': OrderStatus.CANCELLED.value})

    flash(notice, 'success')
    return redirect(url_for('buyer.my_orders'))


# ─── Voucher Routes ───────────────────────────────────────────────

@buyer_bp.route('/vouchers')
@login_required
@role_required('buyer')
def browse_vouchers():
    """Browse available gift vouchers."""
    vouchers = GiftCard.query.filter_by(
        status=GiftCardStatus.AVAILABLE.value
    ).order_by(GiftCard.denomination.asc()).all()

    # Get this buyer's existing voucher orders
    my_voucher_orders = VoucherOrder.query.filter_by(user_id=current_user.id)\
        .order_by(VoucherOrder.created_at.desc()).all()

    # Build set of gift card IDs the buyer already has a pending request for
    pending_card_ids = {vo.gift_card_id for vo in my_voucher_orders 
                        if vo.status == VoucherOrderStatus.PENDING.value}

    return render_template('voucher_browse.html',
                           vouchers=vouchers,
                           my_orders=my_voucher_orders,
                           pending_card_ids=pending_card_ids,
                           partial=is_htmx())


@buyer_bp.route('/vouchers/<int:card_id>/request', methods=['POST'])
@login_required
@role_required('buyer')
def request_voucher(card_id):
    """Place a voucher request — pending admin approval."""
    card = GiftCard.query.get_or_404(card_id)

    if card.status != GiftCardStatus.AVAILABLE.value:
        flash('This voucher is no longer available.', 'warning')
        return redirect(url_for('buyer.browse_vouchers'))

    # Check if buyer already has a pending request for this card
    existing = VoucherOrder.query.filter_by(
        user_id=current_user.id,
        gift_card_id=card_id,
        status=VoucherOrderStatus.PENDING.value
    ).first()

    if existing:
        flash('You already have a pending request for this voucher.', 'info')
        return redirect(url_for('buyer.browse_vouchers'))

    order = VoucherOrder(
        user_id=current_user.id,
        gift_card_id=card_id,
        status=VoucherOrderStatus.PENDING.value
    )
    db.session.add(order)
    db.session.commit()

    # ── Notify all admins via email ──
    try:
        admin_users = User.query.filter_by(role=UserRole.ADMIN.value).all()
        dashboard_url = url_for('admin_giftcards.gift_cards_dashboard', _external=True)
        now = datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')

        for admin in admin_users:
            send_email(
                to=admin.email,
                subject=f"🎫 New Voucher Request — {card.brand} ₹{card.denomination} by {current_user.username}",
                template="mail/voucher_request_admin_email.html",
                buyer_name=current_user.username,
                buyer_email=current_user.email,
                brand=card.brand,
                denomination=f"{card.denomination:.0f}",
                requested_at=now,
                dashboard_url=dashboard_url
            )
    except Exception as e:
        # Don't block the user flow if email fails
        print(f"[WARN] Admin notification email failed: {e}")

    flash(f'Voucher request placed! Admin will review your request for {card.brand} ₹{card.denomination}.', 'success')
    return redirect(url_for('buyer.browse_vouchers'))
