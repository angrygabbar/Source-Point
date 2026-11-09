# Source Point/blueprints/admin_giftcards.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.gift_card import GiftCard
from models.commerce import VoucherOrder
from enums import GiftCardStatus, GiftCardBrand, VoucherOrderStatus
from utils import role_required, send_email, log_user_action
from datetime import datetime
from sqlalchemy import or_
import re

admin_giftcards_bp = Blueprint('admin_giftcards', __name__)

_EMAIL_ADDRESS_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
GIFT_CARD_OCCASIONS = {
    'raksha_bandhan': {
        'label': 'Raksha Bandhan', 'greeting': 'Happy Raksha Bandhan!', 'motif': '🪢',
        'primary': '#be123c', 'secondary': '#f97316', 'accent': '#fbbf24', 'surface': '#3b1024',
    },
    'diwali': {
        'label': 'Diwali', 'greeting': 'Wishing you a bright Diwali!', 'motif': '🪔',
        'primary': '#7c3aed', 'secondary': '#f59e0b', 'accent': '#fde68a', 'surface': '#21113c',
    },
    'birthday': {
        'label': 'Birthday', 'greeting': 'Happy Birthday!', 'motif': '🎂',
        'primary': '#db2777', 'secondary': '#7c3aed', 'accent': '#fcd34d', 'surface': '#30123e',
    },
    'anniversary': {
        'label': 'Anniversary', 'greeting': 'Happy Anniversary!', 'motif': '💝',
        'primary': '#be123c', 'secondary': '#fb7185', 'accent': '#fda4af', 'surface': '#3a1020',
    },
    'congratulations': {
        'label': 'Congratulations', 'greeting': 'Congratulations!', 'motif': '🎉',
        'primary': '#2563eb', 'secondary': '#10b981', 'accent': '#93c5fd', 'surface': '#102a43',
    },
    'thank_you': {
        'label': 'Thank You', 'greeting': 'A little thank-you gift!', 'motif': '💐',
        'primary': '#0f766e', 'secondary': '#2dd4bf', 'accent': '#99f6e4', 'surface': '#0c2e2b',
    },
    'general': {
        'label': 'Just Because', 'greeting': 'A special gift for you!', 'motif': '🎁',
        'primary': '#ec4899', 'secondary': '#8b5cf6', 'accent': '#c4b5fd', 'surface': '#251343',
    },
}


def _get_gift_card_theme(occasion):
    return GIFT_CARD_OCCASIONS.get(occasion, GIFT_CARD_OCCASIONS['general'])


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
                           pending_count=pending_count,
                           gift_card_occasions=GIFT_CARD_OCCASIONS)


@admin_giftcards_bp.route('/admin/gift-cards/send', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def direct_send_dashboard():
    """Dedicated admin workspace for sending an available gift card."""
    if request.method == 'POST':
        card_id = request.form.get('gift_card_id', type=int)
        sender_name = ' '.join(request.form.get('sender_name', '').split())
        sender_relationship = ' '.join(request.form.get('sender_relationship', '').split())
        recipient_name = ' '.join(request.form.get('recipient_name', '').split())
        recipient_email = request.form.get('recipient_email', '').strip()
        custom_message = request.form.get('custom_message', '').strip()
        occasion = request.form.get('occasion', 'general').strip()

        if not card_id:
            flash('Select a gift card from available stock.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if not sender_name or not recipient_name or not recipient_email:
            flash('Sender name, recipient name, and recipient email are required.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if not custom_message:
            flash('Enter a personal gift message for the recipient.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if not _EMAIL_ADDRESS_RE.fullmatch(recipient_email):
            flash('Enter a valid recipient email address.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if len(sender_name) > 150 or len(recipient_name) > 150 or len(recipient_email) > 150:
            flash('Sender name, recipient name, and recipient email must be 150 characters or fewer.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if len(sender_relationship) > 80:
            flash('Sender relationship must be 80 characters or fewer.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if len(custom_message) > 1500:
            flash('The personal message must be 1,500 characters or fewer.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))
        if occasion not in GIFT_CARD_OCCASIONS:
            flash('Choose a valid gift card occasion.', 'danger')
            return redirect(url_for('admin_giftcards.direct_send_dashboard'))

        try:
            card = GiftCard.query.filter_by(id=card_id).with_for_update().first()
            if not card:
                db.session.rollback()
                flash('That gift card could not be found.', 'danger')
                return redirect(url_for('admin_giftcards.direct_send_dashboard'))
            if card.status != GiftCardStatus.AVAILABLE.value:
                db.session.rollback()
                flash('That gift card is no longer available in stock.', 'warning')
                return redirect(url_for('admin_giftcards.direct_send_dashboard'))
            if VoucherOrder.query.filter_by(
                gift_card_id=card.id,
                status=VoucherOrderStatus.PENDING.value,
            ).first():
                db.session.rollback()
                flash('This gift card has a buyer request awaiting approval and cannot be sent directly.', 'warning')
                return redirect(url_for('admin_giftcards.direct_send_dashboard'))
            if card.is_expired:
                db.session.rollback()
                flash('Expired gift cards cannot be sent.', 'warning')
                return redirect(url_for('admin_giftcards.direct_send_dashboard'))

            _send_gift_card_to_recipient(
                card, recipient_name, recipient_email, custom_message,
                sender_name=sender_name, sender_relationship=sender_relationship, occasion=occasion,
            )
            flash(f'Gift card sent to {recipient_name} on behalf of {sender_name}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error sending gift card: {str(e)}', 'danger')
        return redirect(url_for('admin_giftcards.direct_send_dashboard'))

    today = datetime.utcnow().date()
    available_cards = GiftCard.query.filter(
        GiftCard.status == GiftCardStatus.AVAILABLE.value,
        or_(GiftCard.expiry_date.is_(None), GiftCard.expiry_date >= today),
        ~GiftCard.voucher_orders.any(
            VoucherOrder.status == VoucherOrderStatus.PENDING.value
        )
    ).order_by(GiftCard.brand.asc(), GiftCard.denomination.asc(), GiftCard.id.asc()).all()
    return render_template(
        'admin_gift_card_send.html',
        available_cards=available_cards,
        available_count=len(available_cards),
        gift_card_occasions=GIFT_CARD_OCCASIONS,
    )


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


@admin_giftcards_bp.route('/admin/gift-cards/bulk-add', methods=['POST'])
@login_required
@role_required('admin')
def bulk_add_gift_cards():
    """Add multiple gift cards at once for the same brand."""
    brand = request.form.get('brand', '').strip()
    custom_brand = request.form.get('custom_brand', '').strip()
    denomination = request.form.get('denomination', '0')
    expiry_date_str = request.form.get('expiry_date', '')
    notes = request.form.get('notes', '').strip()
    card_numbers_raw = request.form.get('card_numbers', '').strip()
    pins_raw = request.form.get('pins', '').strip()

    if not card_numbers_raw or not pins_raw:
        flash('Card numbers and PINs are required.', 'danger')
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

    # Parse card numbers and PINs (one per line)
    card_numbers = [cn.strip() for cn in card_numbers_raw.replace(',', '\n').split('\n') if cn.strip()]
    pins = [p.strip() for p in pins_raw.replace(',', '\n').split('\n') if p.strip()]

    if len(card_numbers) != len(pins):
        flash(f'Mismatch: {len(card_numbers)} card number(s) but {len(pins)} PIN(s). They must be equal.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))

    if len(card_numbers) == 0:
        flash('No valid card numbers found.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))

    try:
        count = 0
        for card_number, pin in zip(card_numbers, pins):
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
            count += 1

        db.session.commit()
        log_user_action('Bulk Gift Cards Added', f'Brand: {brand}, Count: {count}, Denomination: ₹{denomination}')
        flash(f'🎉 Successfully added {count} {brand} gift card(s)!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error during bulk add: {str(e)}', 'danger')

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


def _send_gift_card_to_recipient(card, recipient_name, recipient_email, custom_message='',
                                 sender_name='', sender_relationship='', occasion='general'):
    """Email one available card and record its recipient after queueing delivery."""
    gift_theme = _get_gift_card_theme(occasion)
    send_email(
        to=recipient_email,
        subject=f"🎁 Your {card.brand} {gift_theme['label']} gift from {sender_name or 'Source Point'}",
        template="mail/gift_card_email.html",
        recipient_name=recipient_name,
        brand=card.brand,
        card_number=card.get_card_number(),
        pin=card.get_pin(),
        denomination=card.denomination,
        expiry_date=card.expiry_date,
        custom_message=custom_message,
        sender_name=sender_name,
        sender_relationship=sender_relationship,
        gift_theme=gift_theme,
        include_default_cc=False,
    )

    card.status = GiftCardStatus.SENT.value
    card.recipient_name = recipient_name
    card.recipient_email = recipient_email
    card.sent_at = datetime.utcnow()
    card.sent_by_id = current_user.id
    db.session.commit()
    sender_details = sender_name or 'Source Point'
    if sender_relationship:
        sender_details += f' ({sender_relationship})'
    log_user_action('Gift Card Sent', f'Brand: {card.brand}, From: {sender_details}, To: {recipient_email}')


@admin_giftcards_bp.route('/admin/gift-cards/<int:card_id>/send', methods=['POST'])
@login_required
@role_required('admin')
def send_gift_card(card_id):
    """Send a gift card to a recipient via email."""
    card = GiftCard.query.filter_by(id=card_id).with_for_update().first_or_404()
    
    if card.status != GiftCardStatus.AVAILABLE.value:
        flash('This gift card is not available for sending.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if VoucherOrder.query.filter_by(
        gift_card_id=card.id,
        status=VoucherOrderStatus.PENDING.value,
    ).first():
        flash('This gift card has a buyer request awaiting approval.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    recipient_name = ' '.join(request.form.get('recipient_name', '').split())
    sender_name = ' '.join(request.form.get('sender_name', '').split())
    sender_relationship = ' '.join(request.form.get('sender_relationship', '').split())
    recipient_email = request.form.get('recipient_email', '').strip()
    custom_message = request.form.get('custom_message', '').strip()
    occasion = request.form.get('occasion', 'general').strip()
    
    if not sender_name or not recipient_name or not recipient_email:
        flash('Sender name, recipient name, and recipient email are required.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if not custom_message:
        flash('Enter a personal gift message for the recipient.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if not _EMAIL_ADDRESS_RE.fullmatch(recipient_email):
        flash('Enter a valid recipient email address.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if card.is_expired:
        flash('Expired gift cards cannot be sent.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if len(sender_name) > 150 or len(recipient_name) > 150 or len(recipient_email) > 150 or len(custom_message) > 1500:
        flash('Sender, recipient, or message exceeds the allowed length.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if len(sender_relationship) > 80:
        flash('Sender relationship must be 80 characters or fewer.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    if occasion not in GIFT_CARD_OCCASIONS:
        flash('Choose a valid gift card occasion.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    try:
        _send_gift_card_to_recipient(
            card, recipient_name, recipient_email, custom_message,
            sender_name=sender_name, sender_relationship=sender_relationship, occasion=occasion,
        )
        flash(f'Gift card sent to {recipient_name} on behalf of {sender_name} successfully! 🎉', 'success')
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
    vo = VoucherOrder.query.filter_by(id=order_id).with_for_update().first_or_404()
    
    if vo.status != VoucherOrderStatus.PENDING.value:
        flash('This order has already been processed.', 'warning')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    card = GiftCard.query.filter_by(id=vo.gift_card_id).with_for_update().first()
    user = vo.user

    if not card:
        flash('The gift card for this order could not be found.', 'danger')
        return redirect(url_for('admin_giftcards.gift_cards_dashboard'))
    
    if card.status != GiftCardStatus.AVAILABLE.value or card.is_expired:
        flash('This gift card is no longer available.', 'warning')
        vo.status = VoucherOrderStatus.REJECTED.value
        vo.rejection_reason = 'Gift card no longer available or expired'
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
            expiry_date=card.expiry_date,
            custom_message='',
            include_default_cc=False,
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
