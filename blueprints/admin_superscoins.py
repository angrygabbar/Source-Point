from datetime import datetime
from io import BytesIO

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from enums import UserRole, SupersCoinTransactionType, SupersCoinInvoiceStatus, CoinSpendingCategory
from invoice_service import SupersCoinInvoiceGenerator
from models.auth import User
from models.commerce import SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice
from services.superscoins_service import SupersCoinsService
from utils import role_required, send_email, log_user_action


admin_superscoins_bp = Blueprint(
    'admin_superscoins',
    __name__,
    url_prefix='/admin/superscoins'
)


def _parse_due_date(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()


def _coin_invoice_attachment(invoice):
    pdf_bytes = SupersCoinInvoiceGenerator(invoice).generate_pdf()
    return {
        'filename': f'{invoice.invoice_number}.pdf',
        'content_type': 'application/pdf',
        'data': pdf_bytes,
    }


def _notify_coin_activity(seller, wallet, transaction):
    send_email(
        to=seller.email,
        cc=current_user.email,
        subject=f"SupersCoins {transaction.transaction_type.title()} Update",
        template='mail/superscoins_activity_email.html',
        seller=seller,
        wallet=wallet,
        transaction=transaction,
        admin=current_user,
        now=datetime.utcnow(),
    )


def _notify_coin_invoice(invoice):
    attachment = _coin_invoice_attachment(invoice)
    send_email(
        to=invoice.seller.email,
        cc=current_user.email,
        subject=f"SupersCoins Invoice {invoice.invoice_number}",
        template='mail/superscoins_invoice_email.html',
        invoice=invoice,
        seller=invoice.seller,
        admin=current_user,
        now=datetime.utcnow(),
        attachments=[attachment],
    )


@admin_superscoins_bp.route('/')
@login_required
@role_required(UserRole.ADMIN.value)
def dashboard():
    selected_seller_id = request.args.get('seller_id', type=int)
    sellers = SupersCoinsService.seller_query().order_by(User.username.asc()).all()
    selected_seller = None
    selected_wallet = None
    setup_pending = not SupersCoinsService.tables_ready()

    if setup_pending:
        if selected_seller_id:
            selected_seller = SupersCoinsService.get_seller(selected_seller_id)
        flash("SupersCoins database tables are not installed yet. Please run the database migration.", "warning")
        return render_template(
            'admin_superscoins.html',
            sellers=sellers,
            wallet_map={},
            selected_seller=selected_seller,
            selected_wallet=None,
            transactions=[],
            invoices=[],
            total_balance=0,
            total_credited=0,
            total_debited=0,
            transaction_types=SupersCoinTransactionType,
            spending_categories=CoinSpendingCategory,
            setup_pending=True,
        )

    if selected_seller_id:
        selected_seller = SupersCoinsService.get_seller(selected_seller_id)
        if selected_seller:
            selected_wallet = SupersCoinWallet.query.filter_by(seller_id=selected_seller.id).first()

    wallet_map = {wallet.seller_id: wallet for wallet in SupersCoinWallet.query.all()}
    total_balance = db.session.query(func.coalesce(func.sum(SupersCoinWallet.balance), 0)).scalar() or 0
    total_credited = db.session.query(func.coalesce(func.sum(SupersCoinTransaction.amount), 0))\
        .filter(SupersCoinTransaction.transaction_type == SupersCoinTransactionType.CREDIT.value).scalar() or 0
    total_debited = db.session.query(func.coalesce(func.sum(SupersCoinTransaction.amount), 0))\
        .filter(SupersCoinTransaction.transaction_type == SupersCoinTransactionType.DEBIT.value).scalar() or 0

    transactions_query = SupersCoinTransaction.query.order_by(SupersCoinTransaction.created_at.desc())
    invoices_query = SupersCoinInvoice.query.order_by(SupersCoinInvoice.created_at.desc())
    if selected_seller:
        transactions_query = transactions_query.filter_by(seller_id=selected_seller.id)
        invoices_query = invoices_query.filter_by(seller_id=selected_seller.id)

    transactions = transactions_query.limit(80).all()
    invoices = invoices_query.limit(50).all()

    return render_template(
        'admin_superscoins.html',
        sellers=sellers,
        wallet_map=wallet_map,
        selected_seller=selected_seller,
        selected_wallet=selected_wallet,
        transactions=transactions,
        invoices=invoices,
        total_balance=total_balance,
        total_credited=total_credited,
        total_debited=total_debited,
        transaction_types=SupersCoinTransactionType,
        spending_categories=CoinSpendingCategory,
        setup_pending=False,
    )


@admin_superscoins_bp.route('/adjust', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def adjust_wallet():
    seller_id = request.form.get('seller_id', type=int)
    transaction_type = request.form.get('transaction_type')
    amount = request.form.get('amount')
    note = request.form.get('note', '').strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not SupersCoinsService.tables_ready():
        message = "SupersCoins database tables are not installed yet. Please run the database migration."
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 503
        flash(message, 'warning')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))

    success, message, wallet, transaction = SupersCoinsService.adjust_wallet(
        seller_id=seller_id,
        transaction_type=transaction_type,
        amount_value=amount,
        admin_id=current_user.id,
        note=note,
    )

    if not success:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))

    db.session.commit()

    try:
        _notify_coin_activity(wallet.seller, wallet, transaction)
    except Exception as e:
        print(f"SupersCoins activity email failed: {e}")

    log_user_action(
        "SupersCoins Wallet Update",
        f"{transaction.transaction_type.title()} {transaction.amount} SC for {wallet.seller.username}"
    )

    if is_ajax:
        return jsonify({
            'success': True,
            'message': message,
            'balance': f"{float(wallet.balance):,.2f}",
        })
    flash(message, 'success')
    return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))


@admin_superscoins_bp.route('/invoices/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_invoice():
    seller_id = request.form.get('seller_id', type=int)
    amount = request.form.get('amount')
    description = request.form.get('description', '').strip()
    notes = request.form.get('notes', '').strip()
    due_date_value = request.form.get('due_date')
    spending_category = request.form.get('spending_category', '').strip()
    booking_details = request.form.get('booking_details', '').strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not SupersCoinsService.tables_ready():
        message = "SupersCoins database tables are not installed yet. Please run the database migration."
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 503
        flash(message, 'warning')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))

    try:
        due_date = _parse_due_date(due_date_value)
    except ValueError:
        message = "Invalid invoice due date."
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))

    success, message, invoice = SupersCoinsService.create_invoice(
        seller_id=seller_id,
        amount_value=amount,
        admin_id=current_user.id,
        description=description,
        notes=notes,
        due_date=due_date,
        spending_category=spending_category,
        booking_details=booking_details,
    )

    if not success:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))

    db.session.commit()

    try:
        _notify_coin_invoice(invoice)
    except Exception as e:
        print(f"SupersCoins invoice email failed: {e}")

    log_user_action(
        "Create SupersCoins Invoice",
        f"Created {invoice.invoice_number} for {invoice.seller.username}: {invoice.amount} SC"
    )

    if is_ajax:
        return jsonify({'success': True, 'message': message})
    flash(f"{message} Notification queued for seller and admin.", 'success')
    return redirect(url_for('admin_superscoins.dashboard', seller_id=seller_id))


@admin_superscoins_bp.route('/invoices/<int:invoice_id>/download')
@login_required
@role_required(UserRole.ADMIN.value)
def download_invoice(invoice_id):
    if not SupersCoinsService.tables_ready():
        flash("SupersCoins database tables are not installed yet. Please run the database migration.", "warning")
        return redirect(url_for('admin_superscoins.dashboard'))

    invoice = SupersCoinInvoice.query.get_or_404(invoice_id)
    pdf_bytes = SupersCoinInvoiceGenerator(invoice).generate_pdf()
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{invoice.invoice_number}.pdf',
    )


@admin_superscoins_bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def send_invoice(invoice_id):
    if not SupersCoinsService.tables_ready():
        message = "SupersCoins database tables are not installed yet. Please run the database migration."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message}), 503
        flash(message, 'warning')
        return redirect(url_for('admin_superscoins.dashboard'))

    invoice = SupersCoinInvoice.query.get_or_404(invoice_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        _notify_coin_invoice(invoice)
        message = f"SupersCoins invoice {invoice.invoice_number} notification queued."
        log_user_action("Send SupersCoins Invoice", message)
        if is_ajax:
            return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    except Exception as e:
        message = f"Unable to send SupersCoins invoice: {e}"
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 500
        flash(message, 'danger')

    return redirect(url_for('admin_superscoins.dashboard', seller_id=invoice.seller_id))


def _notify_coin_invoice_paid(invoice):
    attachment = _coin_invoice_attachment(invoice)
    send_email(
        to=invoice.seller.email,
        cc=current_user.email,
        subject=f"SupersCoins Invoice {invoice.invoice_number} — Payment Confirmed",
        template='mail/superscoins_invoice_paid_email.html',
        invoice=invoice,
        seller=invoice.seller,
        admin=current_user,
        now=datetime.utcnow(),
        attachments=[attachment],
    )


@admin_superscoins_bp.route('/invoices/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def mark_invoice_paid(invoice_id):
    if not SupersCoinsService.tables_ready():
        message = "SupersCoins database tables are not installed yet. Please run the database migration."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message}), 503
        flash(message, 'warning')
        return redirect(url_for('admin_superscoins.dashboard'))

    invoice = SupersCoinInvoice.query.get_or_404(invoice_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if invoice.status == SupersCoinInvoiceStatus.PAID.value:
        message = f"Invoice {invoice.invoice_number} is already marked as Paid."
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'info')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=invoice.seller_id))

    if invoice.status == SupersCoinInvoiceStatus.CANCELLED.value:
        message = f"Cannot mark a cancelled invoice as Paid."
        if is_ajax:
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'danger')
        return redirect(url_for('admin_superscoins.dashboard', seller_id=invoice.seller_id))

    invoice.status = SupersCoinInvoiceStatus.PAID.value
    invoice.paid_at = datetime.utcnow()
    db.session.commit()

    try:
        _notify_coin_invoice_paid(invoice)
    except Exception as e:
        print(f"SupersCoins invoice paid email failed: {e}")

    log_user_action(
        "Mark SupersCoins Invoice Paid",
        f"Marked {invoice.invoice_number} as Paid for {invoice.seller.username}: SC {invoice.amount}"
    )

    message = f"Invoice {invoice.invoice_number} marked as Paid. Seller has been notified."
    if is_ajax:
        return jsonify({'success': True, 'message': message})
    flash(message, 'success')
    return redirect(url_for('admin_superscoins.dashboard', seller_id=invoice.seller_id))
