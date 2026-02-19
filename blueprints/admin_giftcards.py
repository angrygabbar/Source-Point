# Source Point/blueprints/admin_giftcards.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.gift_card import GiftCard
from models.commerce import VoucherOrder
from enums import GiftCardStatus, GiftCardBrand, VoucherOrderStatus
from utils import role_required, send_email, log_user_action
from datetime import datetime

admin_giftcards_bp = Blueprint('admin_giftcards', __name__)


@admin_giftcards_bp.route('/admin/gift-cards')
@login_required
@role_required('admin')
def gift_cards_dashboard():
    """Admin Gift Cards Dashboard — list all gift cards with filters."""
    status_filter = request.args.get('status', 'all')
    brand_filter = request.args.get('brand', 'all')
    
    query = GiftCard.query
    
    if status_filter != 'all':
        query = query.filter(GiftCard.status == status_filter)
    if brand_filter != 'all':
        query = query.filter(GiftCard.brand == brand_filter)
    
    gift_cards = query.order_by(GiftCard.created_at.desc()).all()
    
    # Stats
    total = GiftCard.query.count()
    available = GiftCard.query.filter_by(status=GiftCardStatus.AVAILABLE.value).count()
    sent = GiftCard.query.filter_by(status=GiftCardStatus.SENT.value).count()
    expired = GiftCard.query.filter_by(status=GiftCardStatus.EXPIRED.value).count()
    
    stats = {
        'total': total,
        'available': available,
        'sent': sent,
        'expired': expired
    }
    
    brands = [b.value for b in GiftCardBrand]
    statuses = [s.value for s in GiftCardStatus]
    
    # Pending voucher orders
    from sqlalchemy.orm import joinedload
    voucher_orders = VoucherOrder.query.options(
        joinedload(VoucherOrder.user),
        joinedload(VoucherOrder.gift_card)
    ).order_by(
        db.case(
            (VoucherOrder.status == VoucherOrderStatus.PENDING.value, 0),
        else_=1
        ),
        VoucherOrder.created_at.desc()
    ).all()
    
    pending_count = sum(1 for vo in voucher_orders if vo.status == VoucherOrderStatus.PENDING.value)

    return render_template('admin_gift_cards.html',
                           gift_cards=gift_cards,
                           stats=stats,
                           brands=brands,
                           statuses=statuses,
                           current_status=status_filter,
                           current_brand=brand_filter,
                           voucher_orders=voucher_orders,
                           pending_count=pending_count)


@admin_giftcards_bp.route('/admin/gift-cards/add', methods=['POST'])
@login_required
@role_required('admin')
def add_gift_card():
    """Add a new gift card."""
    brand = request.form.get('brand', '').strip()
    custom_brand = request.form.get('custom_brand', '').strip()
    card_number = request.form.get('card_number', '').strip()
    pin = request.form.get('pin', '').strip()
    denomination = request.form.get('denomination', '0')
    expiry_date_str = request.form.get('expiry_date', '')
    notes = request.form.get('notes', '').strip()
    
    if not card_number or not pin:
        flash('Card number and PIN are required.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    # Use custom brand if "Other" is selected
    if brand == 'Other' and custom_brand:
        brand = custom_brand
    
    # Parse expiry date
    expiry_date = None
    if expiry_date_str:
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid expiry date format.', 'danger')
            return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    try:
        card = GiftCard(
            brand=brand,
            denomination=float(denomination),
            expiry_date=expiry_date,
            notes=notes,
            created_by_id=current_user.id
        )
        card.set_card_number(card_number)
        card.set_pin(pin)
        
        db.session.add(card)
        db.session.commit()
        
        log_user_action('Gift Card Added', f'Brand: {brand}, Denomination: ₹{denomination}')
        flash(f'Gift card ({brand}) added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding gift card: {str(e)}', 'danger')
    
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))


@admin_giftcards_bp.route('/admin/gift-cards/<int:card_id>/edit', methods=['POST'])
@login_required
@role_required('admin')
def edit_gift_card(card_id):
    """Edit an existing gift card."""
    card = GiftCard.query.get_or_404(card_id)
    
    # Don't allow editing sent cards
    if card.status == GiftCardStatus.SENT.value:
        flash('Cannot edit a gift card that has already been sent.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    brand = request.form.get('brand', '').strip()
    custom_brand = request.form.get('custom_brand', '').strip()
    card_number = request.form.get('card_number', '').strip()
    pin = request.form.get('pin', '').strip()
    denomination = request.form.get('denomination', '0')
    expiry_date_str = request.form.get('expiry_date', '')
    notes = request.form.get('notes', '').strip()
    
    if brand == 'Other' and custom_brand:
        brand = custom_brand
    
    try:
        card.brand = brand
        card.denomination = float(denomination)
        card.notes = notes
        
        if card_number:
            card.set_card_number(card_number)
        if pin:
            card.set_pin(pin)
        
        if expiry_date_str:
            card.expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        
        db.session.commit()
        log_user_action('Gift Card Edited', f'ID: {card_id}, Brand: {brand}')
        flash('Gift card updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating gift card: {str(e)}', 'danger')
    
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))


@admin_giftcards_bp.route('/admin/gift-cards/<int:card_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_gift_card(card_id):
    """Delete a gift card."""
    card = GiftCard.query.get_or_404(card_id)
    
    try:
        brand = card.brand
        db.session.delete(card)
        db.session.commit()
        log_user_action('Gift Card Deleted', f'ID: {card_id}, Brand: {brand}')
        flash('Gift card deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting gift card: {str(e)}', 'danger')
    
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))


@admin_giftcards_bp.route('/admin/gift-cards/<int:card_id>/send', methods=['POST'])
@login_required
@role_required('admin')
def send_gift_card(card_id):
    """Send a gift card to a recipient via email."""
    card = GiftCard.query.get_or_404(card_id)
    
    if card.status != GiftCardStatus.AVAILABLE.value:
        flash('This gift card is not available for sending.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    recipient_name = request.form.get('recipient_name', '').strip()
    recipient_email = request.form.get('recipient_email', '').strip()
    
    if not recipient_name or not recipient_email:
        flash('Recipient name and email are required.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    try:
        # Decrypt card details for the email
        full_card_number = card.get_card_number()
        full_pin = card.get_pin()
        
        # Send the email
        send_email(
            to=recipient_email,
            subject=f"🎁 Your {card.brand} Gift Card from Source Point",
            template="mail/gift_card_email.html",
            recipient_name=recipient_name,
            brand=card.brand,
            card_number=full_card_number,
            pin=full_pin,
            denomination=card.denomination,
            expiry_date=card.expiry_date
        )
        
        # Update card status
        card.status = GiftCardStatus.SENT.value
        card.recipient_name = recipient_name
        card.recipient_email = recipient_email
        card.sent_at = datetime.utcnow()
        card.sent_by_id = current_user.id
        
        db.session.commit()
        
        log_user_action('Gift Card Sent', f'Brand: {card.brand}, To: {recipient_email}')
        flash(f'Gift card sent to {recipient_name} ({recipient_email}) successfully! 🎉', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending gift card: {str(e)}', 'danger')
    
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))


# ─── Voucher Order Management ─────────────────────────────────────

@admin_giftcards_bp.route('/admin/voucher-orders/<int:order_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_voucher_order(order_id):
    """Approve a voucher order — decrypt and email PIN/code to buyer."""
    vo = VoucherOrder.query.get_or_404(order_id)
    
    if vo.status != VoucherOrderStatus.PENDING.value:
        flash('This order has already been processed.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    card = vo.gift_card
    user = vo.user
    
    if card.status != GiftCardStatus.AVAILABLE.value:
        flash('This gift card is no longer available.', 'warning')
        vo.status = VoucherOrderStatus.REJECTED.value
        vo.rejection_reason = 'Gift card no longer available'
        vo.reviewed_at = datetime.utcnow()
        vo.reviewed_by_id = current_user.id
        db.session.commit()
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    try:
        # Decrypt card details for the email
        full_card_number = card.get_card_number()
        full_pin = card.get_pin()
        
        # Send the email to the buyer
        send_email(
            to=user.email,
            subject=f"🎁 Your {card.brand} Gift Card from SourcePoint",
            template="mail/gift_card_email.html",
            recipient_name=user.username,
            brand=card.brand,
            card_number=full_card_number,
            pin=full_pin,
            denomination=card.denomination,
            expiry_date=card.expiry_date
        )
        
        # Update card status
        card.status = GiftCardStatus.SENT.value
        card.recipient_name = user.username
        card.recipient_email = user.email
        card.sent_at = datetime.utcnow()
        card.sent_by_id = current_user.id
        
        # Update voucher order
        vo.status = VoucherOrderStatus.APPROVED.value
        vo.reviewed_at = datetime.utcnow()
        vo.reviewed_by_id = current_user.id
        
        db.session.commit()
        
        log_user_action('Voucher Order Approved', f'Order #{vo.id}, {card.brand} → {user.email}')
        flash(f'Voucher approved! {card.brand} card details sent to {user.username} ({user.email}). 🎉', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving voucher order: {str(e)}', 'danger')
    
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))


@admin_giftcards_bp.route('/admin/voucher-orders/<int:order_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_voucher_order(order_id):
    """Reject a voucher order with an optional reason."""
    vo = VoucherOrder.query.get_or_404(order_id)
    
    if vo.status != VoucherOrderStatus.PENDING.value:
        flash('This order has already been processed.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    rejection_reason = request.form.get('rejection_reason', '').strip()
    
    vo.status = VoucherOrderStatus.REJECTED.value
    vo.rejection_reason = rejection_reason or None
    vo.reviewed_at = datetime.utcnow()
    vo.reviewed_by_id = current_user.id
    
    db.session.commit()
    
    log_user_action('Voucher Order Rejected', f'Order #{vo.id}, Reason: {rejection_reason or "No reason"}')
    flash(f'Voucher order #{vo.id} rejected.', 'info')
    return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
