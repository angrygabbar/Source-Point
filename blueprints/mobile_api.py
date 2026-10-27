"""JSON API used by the native SourcePoint Android client.

The mobile client authenticates through Flask-Login and uses the same User
records and application database as the website. Responses intentionally expose
only fields needed by the signed-in user's own app session.
"""

from functools import wraps

from datetime import datetime, timedelta
import secrets
from datetime import timezone
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from io import BytesIO

from extensions import db, bcrypt
from enums import (
    OrderStatus, GiftCardStatus, VoucherOrderStatus, UserRole, ApplicationStatus,
    InvoiceStatus, RollbackRequestStatus, RollbackTermsDecision,
)
from models.commerce import (
    Cart, CartItem, Order, Product, SellerInventory, StockRequest, VoucherOrder,
    Invoice, InvoiceItem, ShareableLink, SupersCoinWallet, SupersCoinTransaction,
    SupersCoinInvoice, InventoryRollbackRequest, InventoryRollbackTerms,
)
from models.auth import User, ActivityUpdate, Message
from models.hiring import JobApplication, JobOpening, CodeSnippet, ModeratorAssignmentHistory
from models.learning import LearningContent
from models.gift_card import GiftCard
from models.mcq import TestAssignment, TestResult
from models.teaching import (
    TeachingAnnouncement, TeachingAssignment, TeachingClass, TeachingEnrollment,
    TeachingMaterial, TeachingSession, TeachingSubmission, TeachingTest,
    TeachingTestQuestion, TeachingTestAssignment, TeachingTestSubmission, TeachingTestAnswer,
    TeachingAttendance, TeachingSessionFeedback, TeachingEffortLog,
)
from models.interview import Interview, InterviewParticipant, InterviewFeedback
from services.auth_service import AuthService
from services.commerce_service import CommerceService
from services.hiring_service import HiringService
from services.rollback_terms_service import RollbackTermsService
from utils import log_user_action, send_email


mobile_api_bp = Blueprint("mobile_api", __name__, url_prefix="/api/v1")
LEARNING_ROLES = {"admin", "candidate", "developer", "recruiter", "moderator", "seller", "buyer"}
LEARNING_LANGUAGES = ("java", "cpp", "c", "sql", "dbms", "plsql", "mysql")


def _teaching_class_access(class_id):
    teaching_class = TeachingClass.query.filter_by(id=class_id).first()
    if not teaching_class:
        return None
    if current_user.role == UserRole.ADMIN.value:
        return teaching_class
    if current_user.role == UserRole.TEACHER.value and teaching_class.teacher_id == current_user.id:
        return teaching_class
    if current_user.role == UserRole.STUDENT.value and TeachingEnrollment.query.filter_by(
        class_id=class_id, student_id=current_user.id
    ).first():
        return teaching_class
    return None


def _teaching_class_payload(teaching_class, teacher_view):
    return {
        "id": teaching_class.id,
        "title": teaching_class.title,
        "subject": teaching_class.subject or "",
        "level": teaching_class.level or "",
        "description": teaching_class.description or "",
        "timezone_name": teaching_class.timezone_name,
        "invite_code": teaching_class.invite_code if teacher_view else None,
        "is_active": teaching_class.is_active,
        "teacher": teaching_class.teacher.username if teaching_class.teacher else "",
        "student_count": len(teaching_class.enrollments),
    }


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "mobile_number": user.mobile_number,
        "primary_skill": user.primary_skill,
        "primary_skill_experience": user.primary_skill_experience,
    }


def mobile_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"success": False, "message": "Sign in is required."}), 401
        return view(*args, **kwargs)

    return wrapped


def _require_role(role):
    if current_user.role != role:
        return jsonify({"success": False, "message": "This feature is not available for your account type."}), 403
    return None


def _product_payload(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description or "",
        "category": product.category or "",
        "brand": product.brand or "",
        "price": float(product.price or 0),
        "mrp": float(product.mrp) if product.mrp is not None else None,
        "stock": product.stock,
        "image_url": product.image_url or "",
        "images": [image.image_url for image in product.images],
    }


def _order_payload(order):
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": CommerceService.normalize_order_status(order.status),
        "total_amount": float(order.total_amount or 0),
        "shipping_address": order.shipping_address,
        "billing_address": order.billing_address or "",
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "buyer_name": order.buyer.username if order.buyer else "",
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": float(item.price_at_purchase or 0),
            }
            for item in order.items
        ],
    }


@mobile_api_bp.get("/health")
def health():
    """Check that the API process can reach the same database as the website."""
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native API database health check failed")
        return jsonify({"status": "error", "database": "unavailable"}), 503


@mobile_api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    user, message = AuthService.authenticate_user(email, password)
    if not user:
        return jsonify({"success": False, "message": message}), 401

    if not login_user(user, remember=False):
        return jsonify({"success": False, "message": "This account cannot sign in."}), 403

    # Match the website's configured session lifetime while ensuring a cookie
    # is returned to a native HTTP client that is not a browser session.
    session.permanent = True
    return jsonify({"success": True, "user": _user_payload(user)})


@mobile_api_bp.get("/auth/me")
@mobile_login_required
def me():
    return jsonify({"success": True, "user": _user_payload(current_user)})


@mobile_api_bp.post("/auth/logout")
@mobile_login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({"success": True})


@mobile_api_bp.get("/buyer/products")
@mobile_login_required
def buyer_products():
    denied = _require_role("buyer")
    if denied:
        return denied

    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    query = Product.query.filter(Product.stock > 0)
    if search:
        query = query.filter(or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
            Product.category.ilike(f"%{search}%"),
        ))
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(Product.stock.desc(), Product.id.desc()).paginate(
        page=page, per_page=24, error_out=False
    )
    categories = [
        value for (value,) in db.session.query(Product.category).distinct().all() if value
    ]
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    return jsonify({
        "success": True,
        "products": [_product_payload(product) for product in pagination.items],
        "categories": categories,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "cart_count": len(cart.items) if cart else 0,
    })


@mobile_api_bp.get("/buyer/products/<int:product_id>")
@mobile_login_required
def buyer_product_detail(product_id):
    denied = _require_role("buyer")
    if denied:
        return denied
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404
    return jsonify({"success": True, "product": _product_payload(product)})


@mobile_api_bp.get("/buyer/cart")
@mobile_login_required
def buyer_cart():
    denied = _require_role("buyer")
    if denied:
        return denied
    items, total, _ = CommerceService.get_cart_details(current_user.id)
    return jsonify({
        "success": True,
        "items": [
            {
                "id": item["id"],
                "quantity": item["quantity"],
                "subtotal": float(item["subtotal"]),
                "product": _product_payload(item["product"]),
            }
            for item in items
        ],
        "total": float(total),
    })


@mobile_api_bp.post("/buyer/cart/items/<int:product_id>")
@mobile_login_required
def buyer_add_to_cart(product_id):
    denied = _require_role("buyer")
    if denied:
        return denied
    success, message = CommerceService.add_to_cart(current_user.id, product_id)
    return jsonify({"success": success, "message": message}), (200 if success else 400)


@mobile_api_bp.delete("/buyer/cart/items/<int:item_id>")
@mobile_login_required
def buyer_remove_from_cart(item_id):
    denied = _require_role("buyer")
    if denied:
        return denied
    success, message = CommerceService.remove_item(current_user.id, item_id)
    return jsonify({"success": success, "message": message}), (200 if success else 400)


@mobile_api_bp.post("/buyer/checkout")
@mobile_login_required
def buyer_checkout():
    denied = _require_role("buyer")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    shipping = str(data.get("shipping_address", "")).strip()
    billing = str(data.get("billing_address", shipping)).strip()
    if not shipping:
        return jsonify({"success": False, "message": "Shipping address is required."}), 400

    order, message = CommerceService.process_checkout(current_user.id, shipping, billing)
    if not order:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "order": _order_payload(order)}), 201


@mobile_api_bp.get("/buyer/orders")
@mobile_login_required
def buyer_orders():
    denied = _require_role("buyer")
    if denied:
        return denied
    orders = Order.query.options(joinedload(Order.items)).filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.desc()).all()
    return jsonify({"success": True, "orders": [_order_payload(order) for order in orders]})


@mobile_api_bp.post("/buyer/orders/<int:order_id>/cancel")
@mobile_login_required
def buyer_cancel_order(order_id):
    denied = _require_role("buyer")
    if denied:
        return denied
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404
    if order.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized action."}), 403
    if not CommerceService.can_buyer_cancel_order(order):
        return jsonify({"success": False, "message": "This order can no longer be cancelled."}), 400

    success, message, _, missing_items = CommerceService.transition_order_status(
        order, OrderStatus.CANCELLED.value
    )
    if not success:
        db.session.rollback()
        return jsonify({"success": False, "message": message}), 400
    db.session.commit()
    try:
        send_email(
            to=current_user.email,
            subject=f"Order Cancelled: {order.order_number}",
            template="mail/order_status_update.html",
            buyer_name=current_user.username,
            order_number=order.order_number,
            status=OrderStatus.CANCELLED.value,
            order_date=order.created_at.strftime("%B %d, %Y"),
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            message="Your order has been cancelled. Reserved inventory has been released.",
            now=datetime.utcnow(),
        )
    except Exception:
        current_app.logger.exception("Native order cancellation notification failed")
    if missing_items:
        message += f" Inventory could not be restored for: {', '.join(missing_items)}."
    return jsonify({"success": True, "message": message, "order": _order_payload(order)})


@mobile_api_bp.get("/buyer/vouchers")
@mobile_login_required
def buyer_vouchers():
    denied = _require_role("buyer")
    if denied:
        return denied
    vouchers = GiftCard.query.filter_by(status=GiftCardStatus.AVAILABLE.value).order_by(
        GiftCard.denomination.asc()
    ).all()
    orders = VoucherOrder.query.filter_by(user_id=current_user.id).order_by(
        VoucherOrder.created_at.desc()
    ).all()
    pending_card_ids = {
        order.gift_card_id for order in orders
        if order.status == VoucherOrderStatus.PENDING.value
    }
    return jsonify({
        "success": True,
        "vouchers": [
            {
                "id": card.id,
                "brand": card.brand,
                "denomination": float(card.denomination or 0),
                "expiry_date": card.expiry_date.isoformat() if card.expiry_date else None,
                "request_pending": card.id in pending_card_ids,
            }
            for card in vouchers
        ],
        "orders": [
            {
                "id": order.id,
                "brand": order.gift_card.brand if order.gift_card else "",
                "denomination": float(order.gift_card.denomination or 0) if order.gift_card else 0,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "rejection_reason": order.rejection_reason or "",
            }
            for order in orders
        ],
    })


@mobile_api_bp.post("/buyer/vouchers/<int:card_id>/request")
@mobile_login_required
def buyer_request_voucher(card_id):
    denied = _require_role("buyer")
    if denied:
        return denied
    card = GiftCard.query.filter_by(id=card_id, status=GiftCardStatus.AVAILABLE.value).first()
    if not card:
        return jsonify({"success": False, "message": "This voucher is no longer available."}), 404
    existing = VoucherOrder.query.filter_by(
        user_id=current_user.id,
        gift_card_id=card.id,
        status=VoucherOrderStatus.PENDING.value,
    ).first()
    if existing:
        return jsonify({"success": False, "message": "You already have a pending request for this voucher."}), 409
    order = VoucherOrder(user_id=current_user.id, gift_card_id=card.id)
    db.session.add(order)
    db.session.commit()
    try:
        dashboard_url = url_for("admin_giftcards.gift_cards_dashboard", _external=True)
        requested_at = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")
        for admin in User.query.filter_by(role=UserRole.ADMIN.value).all():
            send_email(
                to=admin.email,
                subject=f"New voucher request — {card.brand} ₹{card.denomination} by {current_user.username}",
                template="mail/voucher_request_admin_email.html",
                buyer_name=current_user.username,
                buyer_email=current_user.email,
                brand=card.brand,
                denomination=f"{card.denomination:.0f}",
                requested_at=requested_at,
                dashboard_url=dashboard_url,
            )
    except Exception:
        current_app.logger.exception("Voucher request saved but admin notification failed")
    return jsonify({"success": True, "message": "Voucher request sent for review.", "order_id": order.id}), 201


@mobile_api_bp.get("/seller/inventory")
@mobile_login_required
def seller_inventory():
    denied = _require_role("seller")
    if denied:
        return denied
    rows = db.session.query(SellerInventory, Product).join(Product).filter(
        SellerInventory.seller_id == current_user.id
    ).order_by(Product.name).all()
    products = [{
        "inventory_id": inventory.id,
        "stock": inventory.stock,
        "product": _product_payload(product),
    } for inventory, product in rows]
    catalog = [_product_payload(product) for product in Product.query.order_by(Product.name).all()]
    return jsonify({"success": True, "products": products, "catalog": catalog})


@mobile_api_bp.patch("/seller/inventory/<int:inventory_id>")
@mobile_login_required
def seller_update_inventory(inventory_id):
    denied = _require_role("seller")
    if denied:
        return denied
    inventory = SellerInventory.query.get(inventory_id)
    if not inventory or inventory.seller_id != current_user.id:
        return jsonify({"success": False, "message": "Inventory item not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        new_stock = int(data.get("stock"))
        if new_stock < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Stock must be zero or greater."}), 400
    inventory.stock = new_stock
    db.session.commit()
    log_user_action("Update Inventory", f"Seller updated stock for {inventory.product.name}")
    return jsonify({"success": True, "message": "Stock count updated.", "stock": inventory.stock})


@mobile_api_bp.post("/seller/stock-requests")
@mobile_login_required
def seller_request_stock():
    denied = _require_role("seller")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity"))
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a product and enter a positive quantity."}), 400
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    stock_request = StockRequest(
        seller_id=current_user.id,
        product_id=product.id,
        quantity=quantity,
        status="Pending",
    )
    db.session.add(stock_request)
    db.session.commit()
    notified = False
    for admin in User.query.filter_by(role="admin").all():
        try:
            send_email(
                to=admin.email,
                subject=f"New Stock Request: {product.name}",
                template="mail/new_stock_request_admin.html",
                request=stock_request,
                seller=current_user,
                product=product,
                now=datetime.utcnow(),
                sync=True,
            )
            notified = True
        except Exception:
            current_app.logger.exception("Native stock request notification failed")
    return jsonify({
        "success": True,
        "message": "Stock request submitted." if notified else "Stock request saved for admin review.",
        "request_id": stock_request.id,
    }), 201


@mobile_api_bp.get("/seller/orders")
@mobile_login_required
def seller_orders():
    denied = _require_role("seller")
    if denied:
        return denied
    orders = Order.query.options(joinedload(Order.items)).filter_by(
        seller_id=current_user.id
    ).order_by(Order.created_at.desc()).all()
    return jsonify({"success": True, "orders": [_order_payload(order) for order in orders]})


@mobile_api_bp.patch("/seller/orders/<int:order_id>")
@mobile_login_required
def seller_update_order(order_id):
    denied = _require_role("seller")
    if denied:
        return denied
    order = Order.query.get(order_id)
    if not order or order.seller_id != current_user.id:
        return jsonify({"success": False, "message": "Order not found."}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not isinstance(new_status, str) or not new_status.strip():
        return jsonify({"success": False, "message": "Status is required."}), 400
    success, message, _, missing_items = CommerceService.transition_order_status(order, new_status)
    if not success:
        db.session.rollback()
        return jsonify({"success": False, "message": message}), 400
    db.session.commit()
    try:
        send_email(
            to=order.buyer.email,
            subject=f"Order Update: {order.status}",
            template="mail/order_status_update.html",
            buyer_name=order.buyer.username,
            order_number=order.order_number,
            status=order.status,
            order_date=order.created_at.strftime("%Y-%m-%d"),
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            now=datetime.utcnow(),
        )
    except Exception:
        current_app.logger.exception("Native seller order notification failed")
    if missing_items:
        message += f" Could not restore inventory for: {', '.join(missing_items)}."
    return jsonify({"success": True, "message": message, "order": _order_payload(order)})


@mobile_api_bp.get("/seller/invoices")
@mobile_login_required
def seller_invoices():
    denied = _require_role("seller")
    if denied:
        return denied
    invoices = Invoice.query.filter_by(admin_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    return jsonify({
        "success": True,
        "invoices": [
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "recipient_name": invoice.recipient_name,
                "recipient_email": invoice.recipient_email,
                "status": invoice.status,
                "total_amount": float(invoice.total_amount or 0),
                "amount_paid": float(invoice.amount_paid or 0),
                "pending_amount": invoice.pending_amount,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "items": [
                    {"description": item.description, "quantity": item.quantity, "price": float(item.price)}
                    for item in invoice.items
                ],
            }
            for invoice in invoices
        ],
    })


@mobile_api_bp.post("/seller/invoices")
@mobile_login_required
def seller_create_invoice():
    denied = _require_role("seller")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    recipient_name = data.get("recipient_name")
    recipient_email = data.get("recipient_email")
    if not isinstance(recipient_name, str) or not recipient_name.strip():
        return jsonify({"success": False, "message": "Recipient name is required."}), 400
    if not isinstance(recipient_email, str) or "@" not in recipient_email:
        return jsonify({"success": False, "message": "Enter a valid recipient email."}), 400
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({"success": False, "message": "Add at least one invoice item."}), 400
    invoice_items = []
    subtotal = 0.0
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        description = item.get("description")
        try:
            quantity = int(item.get("quantity"))
            price = float(item.get("price"))
        except (TypeError, ValueError):
            continue
        if not isinstance(description, str) or not description.strip() or quantity <= 0 or price < 0:
            continue
        invoice_items.append(InvoiceItem(description=description.strip()[:200], quantity=quantity, price=price))
        subtotal += quantity * price
    if not invoice_items:
        return jsonify({"success": False, "message": "Enter valid invoice item descriptions, quantities, and prices."}), 400
    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.strptime(str(data["due_date"]), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Due date must use YYYY-MM-DD."}), 400
    last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
    next_number = (last_invoice.id + 1) if last_invoice else 1
    invoice = Invoice(
        invoice_number=f"INV{datetime.utcnow().year}{next_number:03d}",
        recipient_name=recipient_name.strip(),
        recipient_email=recipient_email.strip(),
        bill_to_address=(data.get("bill_to_address") or "").strip() or None,
        ship_to_address=(data.get("ship_to_address") or "").strip() or None,
        subtotal=subtotal,
        total_amount=subtotal,
        due_date=due_date,
        admin_id=current_user.id,
        status=InvoiceStatus.UNPAID.value,
        items=invoice_items,
    )
    db.session.add(invoice)
    db.session.commit()
    try:
        from invoice_service import InvoiceGenerator
        pdf = InvoiceGenerator(invoice).generate_pdf()
        send_email(
            to=recipient_email.strip(),
            subject=f"Invoice {invoice.invoice_number}",
            template="mail/ecommerce_invoice_email.html",
            invoice=invoice,
            attachments=[{"filename": f"{invoice.invoice_number}.pdf", "content_type": "application/pdf", "data": pdf}],
        )
    except Exception:
        current_app.logger.exception("Invoice saved but PDF email delivery failed")
    log_user_action("Create Invoice", f"Created invoice {invoice.invoice_number} from native app")
    return jsonify({"success": True, "message": "Invoice created.", "invoice_id": invoice.id}), 201


@mobile_api_bp.post("/seller/invoices/<int:invoice_id>/mark-paid")
@mobile_login_required
def seller_mark_invoice_paid(invoice_id):
    denied = _require_role("seller")
    if denied:
        return denied
    invoice = Invoice.query.filter_by(id=invoice_id, admin_id=current_user.id).first()
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    if invoice.status != InvoiceStatus.PAID.value:
        invoice.status = InvoiceStatus.PAID.value
        invoice.amount_paid = invoice.total_amount
        db.session.commit()
    return jsonify({"success": True, "message": "Invoice marked paid."})


@mobile_api_bp.delete("/seller/invoices/<int:invoice_id>")
@mobile_login_required
def seller_delete_invoice(invoice_id):
    denied = _require_role("seller")
    if denied:
        return denied
    invoice = Invoice.query.filter_by(id=invoice_id, admin_id=current_user.id).first()
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    db.session.delete(invoice)
    db.session.commit()
    return jsonify({"success": True, "message": "Invoice deleted."})


@mobile_api_bp.get("/seller/superscoins")
@mobile_login_required
def seller_superscoins():
    denied = _require_role("seller")
    if denied:
        return denied
    try:
        from services.superscoins_service import SupersCoinsService
        if not SupersCoinsService.tables_ready():
            return jsonify({"success": True, "setup_pending": True, "message": "SupersCoins is being set up."})
        wallet = SupersCoinWallet.query.filter_by(seller_id=current_user.id).first()
        transactions = SupersCoinTransaction.query.filter_by(seller_id=current_user.id).order_by(
            SupersCoinTransaction.created_at.desc()
        ).limit(100).all()
        invoices = SupersCoinInvoice.query.filter_by(seller_id=current_user.id).order_by(
            SupersCoinInvoice.created_at.desc()
        ).limit(50).all()
        return jsonify({
            "success": True,
            "setup_pending": False,
            "balance": float(wallet.balance or 0) if wallet else 0,
            "transactions": [
                {"id": item.id, "type": item.transaction_type, "amount": float(item.amount or 0),
                 "balance_after": float(item.balance_after or 0), "note": item.note or "",
                 "created_at": item.created_at.isoformat() if item.created_at else None}
                for item in transactions
            ],
            "invoices": [
                {"id": item.id, "invoice_number": item.invoice_number,
                 "amount": float(item.amount or 0), "status": item.status,
                 "description": item.description, "due_date": item.due_date.isoformat() if item.due_date else None}
                for item in invoices
            ],
        })
    except Exception:
        current_app.logger.exception("Native SupersCoins wallet could not be loaded")
        return jsonify({"success": False, "message": "SupersCoins wallet is temporarily unavailable."}), 503


@mobile_api_bp.get("/seller/share-link")
@mobile_login_required
def seller_share_link():
    denied = _require_role("seller")
    if denied:
        return denied
    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    return jsonify({
        "success": True,
        "exists": bool(link),
        "url": url_for("public.shared_catalog", token=link.token, _external=True) if link else "",
        "is_active": bool(link and link.is_active),
    })


@mobile_api_bp.post("/seller/share-link")
@mobile_login_required
def seller_create_share_link():
    denied = _require_role("seller")
    if denied:
        return denied
    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        link = ShareableLink(token=secrets.token_hex(16), seller_id=current_user.id, is_active=True)
        db.session.add(link)
        db.session.commit()
    return jsonify({
        "success": True,
        "url": url_for("public.shared_catalog", token=link.token, _external=True),
        "is_active": link.is_active,
    }), 201


@mobile_api_bp.post("/seller/share-link/toggle")
@mobile_login_required
def seller_toggle_share_link():
    denied = _require_role("seller")
    if denied:
        return denied
    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        return jsonify({"success": False, "message": "Generate a share link first."}), 404
    link.is_active = not link.is_active
    db.session.commit()
    return jsonify({"success": True, "is_active": link.is_active, "message": f"Link {'activated' if link.is_active else 'deactivated'}."})


@mobile_api_bp.get("/seller/rollback")
@mobile_login_required
def seller_rollback_dashboard():
    denied = _require_role("seller")
    if denied:
        return denied
    terms = RollbackTermsService.ensure_active_terms()
    decision = RollbackTermsService.get_seller_decision(current_user.id, terms.id)
    inventory = db.session.query(SellerInventory, Product).join(
        Product, SellerInventory.product_id == Product.id
    ).filter(SellerInventory.seller_id == current_user.id, SellerInventory.stock > 0).order_by(Product.name).all()
    requests_for_seller = InventoryRollbackRequest.query.filter_by(
        seller_id=current_user.id
    ).order_by(InventoryRollbackRequest.request_date.desc()).limit(100).all()
    return jsonify({
        "success": True,
        "terms": {"id": terms.id, "version": terms.version, "title": terms.title, "content": terms.content},
        "decision": decision.decision if decision else None,
        "inventory": [
            {"id": row.id, "product_id": row.product_id, "name": product.name, "stock": row.stock}
            for row, product in inventory
        ],
        "requests": [
            {"id": row.id, "request_number": row.request_number, "product": row.product.name,
             "quantity": row.quantity, "reason": row.reason or "", "status": row.status,
             "admin_note": row.admin_note or "", "request_date": row.request_date.isoformat() if row.request_date else None}
            for row in requests_for_seller
        ],
    })


@mobile_api_bp.post("/seller/rollback/terms")
@mobile_login_required
def seller_rollback_terms_decision():
    denied = _require_role("seller")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    terms = RollbackTermsService.ensure_active_terms()
    try:
        terms_id = int(data.get("terms_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Review the current terms before responding."}), 400
    decision = data.get("decision")
    if terms_id != terms.id:
        return jsonify({"success": False, "message": "Terms changed. Reload and review the latest version."}), 409
    if decision not in {RollbackTermsDecision.ACCEPTED.value, RollbackTermsDecision.REJECTED.value}:
        return jsonify({"success": False, "message": "Choose Accept or Reject."}), 400
    RollbackTermsService.record_seller_decision(
        seller_id=current_user.id, terms_id=terms.id, decision=decision, request_obj=request
    )
    log_user_action("Accept Rollback Terms" if decision == RollbackTermsDecision.ACCEPTED.value else "Reject Rollback Terms",
                    f"Seller responded to rollback terms v{terms.version} in native app")
    return jsonify({"success": True, "message": "Terms response saved.", "decision": decision})


@mobile_api_bp.post("/seller/rollback/requests")
@mobile_login_required
def seller_submit_rollback():
    denied = _require_role("seller")
    if denied:
        return denied
    if not RollbackTermsService.seller_has_accepted_current_terms(current_user.id):
        return jsonify({"success": False, "message": "Accept the current rollback terms before requesting a return."}), 403
    data = request.get_json(silent=True) or {}
    try:
        inventory_id = int(data.get("inventory_id"))
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a product and enter a positive quantity."}), 400
    reason = data.get("reason", "")
    if not isinstance(reason, str) or len(reason.strip()) > 2000:
        return jsonify({"success": False, "message": "Reason must be 2,000 characters or fewer."}), 400
    inventory = SellerInventory.query.filter_by(id=inventory_id, seller_id=current_user.id).first()
    if not inventory:
        return jsonify({"success": False, "message": "Inventory item was not found."}), 404
    if quantity < 1 or quantity > inventory.stock:
        return jsonify({"success": False, "message": f"Quantity must be between 1 and {inventory.stock}."}), 400
    pending = InventoryRollbackRequest.query.filter_by(
        seller_id=current_user.id, seller_inventory_id=inventory.id,
        status=RollbackRequestStatus.PENDING.value,
    ).first()
    if pending:
        return jsonify({"success": False, "message": f"A request ({pending.request_number}) is already pending for this product."}), 409
    latest = InventoryRollbackRequest.query.order_by(InventoryRollbackRequest.id.desc()).first()
    request_number = f"RB-{(latest.id + 1) if latest else 1:04d}"
    rollback = InventoryRollbackRequest(
        request_number=request_number, seller_id=current_user.id, product_id=inventory.product_id,
        seller_inventory_id=inventory.id, quantity=quantity,
        reason=reason.strip() or None, status=RollbackRequestStatus.PENDING.value,
    )
    db.session.add(rollback)
    db.session.commit()
    log_user_action("Submit Rollback Request", f"Submitted {request_number} from native app")
    return jsonify({"success": True, "message": f"Rollback request {request_number} submitted."}), 201


@mobile_api_bp.get("/candidate/jobs")
@mobile_login_required
def candidate_jobs():
    denied = _require_role("candidate")
    if denied:
        return denied
    jobs = JobOpening.query.filter_by(is_open=True).order_by(JobOpening.created_at.desc()).all()
    applications = {
        application.job_id: application
        for application in JobApplication.query.filter_by(user_id=current_user.id).all()
    }
    return jsonify({
        "success": True,
        "resume_available": bool(current_user.resume_filename),
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "description": job.description,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "application_status": applications[job.id].status if job.id in applications else None,
            }
            for job in jobs
        ],
    })


@mobile_api_bp.post("/candidate/jobs/<int:job_id>/apply")
@mobile_login_required
def candidate_apply(job_id):
    denied = _require_role("candidate")
    if denied:
        return denied
    job = JobOpening.query.get(job_id)
    if not job or not job.is_open:
        return jsonify({"success": False, "message": "This job is no longer open."}), 404
    try:
        success, message = HiringService.apply_for_job(current_user, job_id, None)
        if success:
            log_user_action("Apply Job", f"Applied for job ID: {job_id} from native app")
        return jsonify({"success": success, "message": message}), (201 if success else 400)
    except Exception as error:
        if JobApplication.query.filter_by(user_id=current_user.id, job_id=job_id).first():
            current_app.logger.exception("Application saved but a follow-up action failed")
            return jsonify({"success": True, "message": "Application submitted. Notification delivery may be delayed."}), 201
        status = 404 if error.__class__.__name__ == "ResourceNotFoundError" else 400
        return jsonify({"success": False, "message": str(error)}), status


@mobile_api_bp.get("/candidate/assessments")
@mobile_login_required
def candidate_assessments():
    denied = _require_role("candidate")
    if denied:
        return denied
    assignments = TestAssignment.query.filter_by(candidate_id=current_user.id).order_by(
        TestAssignment.scheduled_start_time.desc()
    ).all()
    return jsonify({
        "success": True,
        "assessments": [
            {
                "id": assignment.id,
                "title": assignment.test.title,
                "description": assignment.test.description or "",
                "duration_minutes": assignment.test.duration_minutes,
                "question_count": len(assignment.test.questions),
                "scheduled_start_time": assignment.scheduled_start_time.isoformat() if assignment.scheduled_start_time else None,
                "status": assignment.status,
                "started_at": assignment.started_at.isoformat() if assignment.started_at else None,
                "score": assignment.result.score if assignment.result else None,
                "total_questions": assignment.result.total_questions if assignment.result else None,
                "percentage": assignment.result.percentage if assignment.result else None,
            }
            for assignment in assignments
        ],
    })


@mobile_api_bp.post("/candidate/assessments/<int:assignment_id>/start")
@mobile_login_required
def candidate_start_assessment(assignment_id):
    denied = _require_role("candidate")
    if denied:
        return denied
    assignment = TestAssignment.query.filter_by(
        id=assignment_id, candidate_id=current_user.id
    ).first()
    if not assignment:
        return jsonify({"success": False, "message": "Assessment not found."}), 404
    if assignment.status == "completed":
        return jsonify({"success": False, "message": "This assessment has already been completed."}), 409
    if assignment.status == "expired":
        return jsonify({"success": False, "message": "This assessment has expired."}), 410
    now = datetime.utcnow()
    if assignment.scheduled_start_time and now < assignment.scheduled_start_time:
        return jsonify({"success": False, "message": "This assessment is not available yet."}), 403
    if not assignment.started_at:
        assignment.started_at = now
        assignment.status = "in_progress"
        db.session.commit()
    elapsed = (now - assignment.started_at).total_seconds()
    total_seconds = max(0, assignment.test.duration_minutes * 60 - int(elapsed))
    if total_seconds <= 0:
        result = TestResult(
            assignment_id=assignment.id,
            score=0,
            total_questions=len(assignment.test.questions),
            time_taken_minutes=assignment.test.duration_minutes,
            answers_json="{}",
        )
        assignment.status = "completed"
        db.session.add(result)
        db.session.commit()
        return jsonify({"success": False, "message": "The assessment time has expired."}), 410
    return jsonify({
        "success": True,
        "assessment": {
            "id": assignment.id,
            "title": assignment.test.title,
            "description": assignment.test.description or "",
            "remaining_seconds": total_seconds,
            "questions": [
                {
                    "id": question.id,
                    "text": question.question_text,
                    "options": {
                        "A": question.option_a,
                        "B": question.option_b,
                        "C": question.option_c,
                        "D": question.option_d,
                    },
                }
                for question in assignment.test.questions
            ],
        },
    })


@mobile_api_bp.post("/candidate/assessments/<int:assignment_id>/submit")
@mobile_login_required
def candidate_submit_assessment(assignment_id):
    denied = _require_role("candidate")
    if denied:
        return denied
    assignment = TestAssignment.query.filter_by(
        id=assignment_id, candidate_id=current_user.id
    ).first()
    if not assignment:
        return jsonify({"success": False, "message": "Assessment not found."}), 404
    if assignment.status == "completed" or assignment.result:
        return jsonify({"success": False, "message": "This assessment has already been submitted."}), 409
    if not assignment.started_at:
        return jsonify({"success": False, "message": "Start the assessment before submitting answers."}), 400
    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if not isinstance(answers, dict):
        return jsonify({"success": False, "message": "Answers must be provided as an object."}), 400
    elapsed_seconds = (datetime.utcnow() - assignment.started_at).total_seconds()
    if elapsed_seconds > (assignment.test.duration_minutes * 60) + 60:
        result = TestResult(
            assignment_id=assignment.id,
            score=0,
            total_questions=len(assignment.test.questions),
            time_taken_minutes=assignment.test.duration_minutes,
            answers_json="{}",
        )
        assignment.status = "completed"
        db.session.add(result)
        db.session.commit()
        return jsonify({"success": False, "message": "The assessment time expired and it was submitted."}), 410
    questions = assignment.test.questions
    valid_ids = {str(question.id): question for question in questions}
    normalized = {}
    for question_id, option in answers.items():
        question = valid_ids.get(str(question_id))
        if question and isinstance(option, str) and option.upper() in {"A", "B", "C", "D"}:
            normalized[str(question.id)] = option.upper()
    score = sum(
        1 for question in questions
        if normalized.get(str(question.id)) == question.correct_option
    )
    elapsed_minutes = int((datetime.utcnow() - assignment.started_at).total_seconds() / 60)
    result = TestResult(
        assignment_id=assignment.id,
        score=score,
        total_questions=len(questions),
        time_taken_minutes=elapsed_minutes,
        answers_json=__import__("json").dumps(normalized),
    )
    assignment.status = "completed"
    db.session.add(result)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native candidate assessment submission failed")
        return jsonify({"success": False, "message": "Assessment could not be submitted."}), 500
    try:
        from blueprints.candidate_mcq import _send_test_completion_emails
        _send_test_completion_emails(assignment, result)
    except Exception:
        current_app.logger.exception("Assessment saved but completion notifications failed")
    log_user_action("Submit MCQ Test", f"Submitted test '{assignment.test.title}' from native app")
    return jsonify({
        "success": True,
        "message": "Assessment submitted.",
        "score": score,
        "total_questions": len(questions),
        "percentage": result.percentage,
    })


@mobile_api_bp.get("/candidate/code-test")
@mobile_login_required
def candidate_code_test():
    denied = _require_role("candidate")
    if denied:
        return denied
    problem = current_user.assigned_problem
    if not problem:
        return jsonify({"success": True, "assigned": False, "message": "No coding test has been assigned."})
    now = datetime.utcnow()
    if current_user.test_end_time and now > current_user.test_end_time and not current_user.test_completed:
        current_user.test_completed = True
        db.session.commit()
    available_at = current_user.test_start_time
    ended = bool(current_user.test_end_time and now > current_user.test_end_time)
    return jsonify({
        "success": True,
        "assigned": True,
        "available": not ended and (not available_at or now >= available_at) and not current_user.test_completed,
        "completed": bool(current_user.test_completed),
        "starts_at": available_at.isoformat() if available_at else None,
        "ends_at": current_user.test_end_time.isoformat() if current_user.test_end_time else None,
        "seconds_remaining": max(0, int((current_user.test_end_time - now).total_seconds())) if current_user.test_end_time and now < current_user.test_end_time else None,
        "problem": {"title": problem.title, "description": problem.description, "difficulty": problem.difficulty},
        "recipients": [
            {"id": user.id, "username": user.username}
            for user in User.query.filter(User.role.in_(["admin", "developer"])).order_by(User.username).all()
        ],
    })


@mobile_api_bp.post("/candidate/code-test/submit")
@mobile_login_required
def candidate_submit_code_test():
    denied = _require_role("candidate")
    if denied:
        return denied
    if not current_user.assigned_problem:
        return jsonify({"success": False, "message": "No coding test has been assigned."}), 404
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    output = data.get("output", "")
    recipient_id = data.get("recipient_id")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"success": False, "message": "Enter your code before submitting."}), 400
    now = datetime.utcnow()
    if current_user.test_start_time and now < current_user.test_start_time:
        return jsonify({"success": False, "message": "The coding test is not available yet."}), 403
    if current_user.test_end_time and now > current_user.test_end_time:
        current_user.test_completed = True
        db.session.commit()
        return jsonify({"success": False, "message": "The coding test deadline has passed."}), 410
    if not isinstance(recipient_id, (str, int)) or not str(recipient_id).isdigit():
        return jsonify({"success": False, "message": "Choose a reviewer for your submission."}), 400
    try:
        success, message = HiringService.submit_code_test(
            candidate=current_user,
            recipient_id=str(recipient_id),
            code=code,
            output=output if isinstance(output, str) else "",
        )
        if success:
            current_user.test_completed = True
            db.session.commit()
            log_user_action("Submit Code Test", "Submitted code test from native app")
        return jsonify({"success": success, "message": message}), (201 if success else 400)
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Native coding test submission failed")
        return jsonify({"success": False, "message": str(error)}), 400


@mobile_api_bp.get("/profile")
@mobile_login_required
def profile():
    user = _user_payload(current_user)
    user.update({
        "secondary_skill": current_user.secondary_skill,
        "secondary_skill_experience": current_user.secondary_skill_experience,
        "resume_url": current_user.resume_filename,
        "secret_question": current_user.secret_question,
    })
    return jsonify({"success": True, "profile": user})


@mobile_api_bp.patch("/profile")
@mobile_login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    editable_fields = (
        "mobile_number",
        "primary_skill",
        "primary_skill_experience",
        "secondary_skill",
        "secondary_skill_experience",
    )
    for field in editable_fields:
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, str):
                return jsonify({"success": False, "message": f"Invalid value for {field}."}), 400
            setattr(current_user, field, value.strip() or None if isinstance(value, str) else value)
    try:
        db.session.commit()
        log_user_action("Update Profile", "User updated their profile details from the native app")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native profile update failed")
        return jsonify({"success": False, "message": "Profile could not be saved."}), 500
    return jsonify({"success": True, "message": "Profile updated."})


@mobile_api_bp.post("/profile/resume")
@mobile_login_required
def upload_resume():
    resume = request.files.get("resume")
    if not resume or not resume.filename:
        return jsonify({"success": False, "message": "Choose a PDF resume to upload."}), 400
    filename = secure_filename(resume.filename)
    if not filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "message": "Only PDF resumes are accepted."}), 400
    content = resume.read()
    if len(content) > 10 * 1024 * 1024:
        return jsonify({"success": False, "message": "Resume must be 10 MB or smaller."}), 413
    if not content.startswith(b"%PDF-"):
        return jsonify({"success": False, "message": "The selected file is not a valid PDF."}), 400
    try:
        import cloudinary.uploader
        upload_result = cloudinary.uploader.upload(
            BytesIO(content),
            resource_type="raw",
            folder="resumes",
            public_id=f"resume_{current_user.id}",
        )
        current_user.resume_filename = upload_result["secure_url"]
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native resume upload failed")
        return jsonify({"success": False, "message": "Resume upload failed. Try again."}), 502
    log_user_action("Update Resume", "Uploaded resume from native app")
    return jsonify({"success": True, "message": "Resume uploaded.", "resume_url": current_user.resume_filename})


@mobile_api_bp.post("/profile/security-question")
@mobile_login_required
def update_security_question():
    data = request.get_json(silent=True) or {}
    question = str(data.get("secret_question", "")).strip()
    answer = data.get("secret_answer")
    if not question or not isinstance(answer, str) or not answer.strip():
        return jsonify({"success": False, "message": "Question and answer are required."}), 400
    current_user.secret_question = question
    current_user.secret_answer_hash = bcrypt.generate_password_hash(answer.strip()).decode("utf-8")
    db.session.commit()
    log_user_action("Update Security Question", "Updated security question from the native app")
    return jsonify({"success": True, "message": "Recovery question updated."})


@mobile_api_bp.post("/profile/password")
@mobile_login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    if not all(isinstance(value, str) and value for value in (old_password, new_password, confirm_password)):
        return jsonify({"success": False, "message": "Complete all password fields."}), 400
    if not bcrypt.check_password_hash(current_user.password_hash, old_password):
        return jsonify({"success": False, "message": "Current password is not correct."}), 400
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match."}), 400
    current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    log_user_action("Change Password", "User changed their password from the native app")
    return jsonify({"success": True, "message": "Password updated."})


def _mobile_messageable_users():
    now = datetime.utcnow()
    role = current_user.role
    users = {}
    if role in {UserRole.CANDIDATE.value, UserRole.MODERATOR.value,
                UserRole.BUYER.value, UserRole.SELLER.value, UserRole.RECRUITER.value}:
        for user in User.query.filter_by(role=UserRole.ADMIN.value, is_active=True).all():
            users[user.id] = user
    if role == UserRole.CANDIDATE.value:
        if (current_user.test_start_time and current_user.test_end_time
                and current_user.test_start_time <= now <= current_user.test_end_time
                and current_user.moderator_id):
            moderator = User.query.filter_by(id=current_user.moderator_id, is_active=True).first()
            if moderator:
                users[moderator.id] = moderator
    elif role == UserRole.MODERATOR.value:
        candidates = User.query.filter(
            User.moderator_id == current_user.id,
            User.test_start_time <= now,
            User.test_end_time >= now,
            User.is_active.is_(True),
        ).all()
        users.update({user.id: user for user in candidates})
    elif role in {UserRole.ADMIN.value, UserRole.DEVELOPER.value}:
        others = User.query.filter(User.id != current_user.id, User.is_active.is_(True)).all()
        users.update({user.id: user for user in others})
    return users


@mobile_api_bp.get("/messages")
@mobile_login_required
def mobile_messages():
    users = _mobile_messageable_users()
    ids = list(users)
    latest = {}
    if ids:
        messages = Message.query.filter(
            or_(
                (Message.sender_id == current_user.id) & Message.recipient_id.in_(ids),
                (Message.recipient_id == current_user.id) & Message.sender_id.in_(ids),
            )
        ).order_by(Message.timestamp.desc()).all()
        for message in messages:
            other_id = message.recipient_id if message.sender_id == current_user.id else message.sender_id
            latest.setdefault(other_id, message)
    return jsonify({
        "success": True,
        "users": [
            {"id": user.id, "username": user.username, "role": user.role,
             "last_message": latest[user.id].body if user.id in latest else "",
             "last_message_at": latest[user.id].timestamp.isoformat() if user.id in latest and latest[user.id].timestamp else None}
            for user in sorted(users.values(), key=lambda item: item.username.lower())
        ],
    })


@mobile_api_bp.get("/messages/<int:other_user_id>")
@mobile_login_required
def mobile_message_conversation(other_user_id):
    users = _mobile_messageable_users()
    if other_user_id not in users:
        return jsonify({"success": False, "message": "This conversation is not available to your account."}), 403
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == other_user_id),
            (Message.sender_id == other_user_id) & (Message.recipient_id == current_user.id),
        )
    ).order_by(Message.timestamp.asc()).limit(500).all()
    return jsonify({
        "success": True,
        "recipient": {"id": users[other_user_id].id, "username": users[other_user_id].username},
        "messages": [
            {"id": message.id, "sender_id": message.sender_id, "body": message.body,
             "timestamp": message.timestamp.isoformat() if message.timestamp else None}
            for message in messages
        ],
    })


@mobile_api_bp.post("/messages/<int:other_user_id>")
@mobile_login_required
def mobile_send_message(other_user_id):
    users = _mobile_messageable_users()
    if other_user_id not in users:
        return jsonify({"success": False, "message": "This conversation is not available to your account."}), 403
    data = request.get_json(silent=True) or {}
    body = data.get("body")
    if not isinstance(body, str) or not body.strip() or len(body.strip()) > 10000:
        return jsonify({"success": False, "message": "Enter a message of up to 10,000 characters."}), 400
    message = Message(sender_id=current_user.id, recipient_id=other_user_id, body=body.strip())
    db.session.add(message)
    db.session.commit()
    return jsonify({"success": True, "message": "Message sent."}), 201


@mobile_api_bp.get("/learning")
@mobile_login_required
def learning_library():
    if current_user.role not in LEARNING_ROLES:
        return jsonify({"success": False, "message": "Learning content is not available for this account type."}), 403
    return jsonify({"success": True, "languages": list(LEARNING_LANGUAGES)})


@mobile_api_bp.get("/learning/<language>")
@mobile_login_required
def learning_content(language):
    if current_user.role not in LEARNING_ROLES:
        return jsonify({"success": False, "message": "Learning content is not available for this account type."}), 403
    if language not in LEARNING_LANGUAGES:
        return jsonify({"success": False, "message": "Learning topic not found."}), 404
    content = LearningContent.query.get(language)
    if not content:
        content = LearningContent(id=language, content=f"<h1>{language.upper()} Tutorial</h1><p>Content coming soon...</p>")
        db.session.add(content)
        db.session.commit()
    log_user_action("View Learning Content", f"Viewed {language} tutorial from native app")
    return jsonify({"success": True, "language": language, "content": content.content})


@mobile_api_bp.get("/teaching/classes")
@mobile_login_required
def teaching_classes():
    role = current_user.role
    if role == UserRole.ADMIN.value:
        classes = TeachingClass.query.order_by(TeachingClass.created_at.desc()).all()
    elif role == UserRole.TEACHER.value:
        classes = TeachingClass.query.filter_by(teacher_id=current_user.id).order_by(TeachingClass.created_at.desc()).all()
    elif role == UserRole.STUDENT.value:
        classes = TeachingClass.query.join(TeachingEnrollment).filter(
            TeachingEnrollment.student_id == current_user.id
        ).order_by(TeachingClass.created_at.desc()).all()
    else:
        return jsonify({"success": False, "message": "Classes are not available for this account type."}), 403
    teacher_view = role in {UserRole.TEACHER.value, UserRole.ADMIN.value}
    return jsonify({
        "success": True,
        "teacher_view": teacher_view,
        "classes": [_teaching_class_payload(item, teacher_view) for item in classes],
    })


@mobile_api_bp.post("/teaching/classes")
@mobile_login_required
def teaching_create_class():
    if current_user.role != UserRole.TEACHER.value:
        return jsonify({"success": False, "message": "Only teachers can create classes from this screen."}), 403
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
        return jsonify({"success": False, "message": "Enter a class title of 1 to 140 characters."}), 400
    teaching_class = TeachingClass(
        teacher_id=current_user.id,
        title=title.strip(),
        subject=(data.get("subject") or "").strip()[:100] or None,
        level=(data.get("level") or "").strip()[:80] or None,
        description=(data.get("description") or "").strip()[:4000] or None,
        timezone_name="Asia/Kolkata",
        invite_code=secrets.token_hex(5).upper(),
    )
    db.session.add(teaching_class)
    db.session.commit()
    return jsonify({"success": True, "message": "Class created.", "class": _teaching_class_payload(teaching_class, True)}), 201


@mobile_api_bp.post("/teaching/join")
@mobile_login_required
def teaching_join_class():
    if current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Only student accounts can join classes."}), 403
    data = request.get_json(silent=True) or {}
    code = data.get("invite_code")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"success": False, "message": "Enter the class invite code."}), 400
    teaching_class = TeachingClass.query.filter_by(invite_code=code.strip().upper(), is_active=True).first()
    if not teaching_class:
        return jsonify({"success": False, "message": "That class code was not found or the class is archived."}), 404
    enrollment = TeachingEnrollment.query.filter_by(class_id=teaching_class.id, student_id=current_user.id).first()
    if not enrollment:
        db.session.add(TeachingEnrollment(class_id=teaching_class.id, student_id=current_user.id))
        db.session.commit()
    return jsonify({"success": True, "message": f"You joined {teaching_class.title}.", "class_id": teaching_class.id}), 201


@mobile_api_bp.get("/teaching/classes/<int:class_id>")
@mobile_login_required
def teaching_class_detail(class_id):
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    teacher_view = current_user.role in {UserRole.TEACHER.value, UserRole.ADMIN.value}
    assignments = []
    for assignment in teaching_class.assignments:
        if teacher_view:
            submissions = [
                {"id": submission.id, "student": submission.student.username if submission.student else "",
                 "response": submission.response, "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                 "grade": submission.grade, "feedback": submission.feedback or ""}
                for submission in assignment.submissions
            ]
        else:
            submission = TeachingSubmission.query.filter_by(
                assignment_id=assignment.id, student_id=current_user.id
            ).first()
            submissions = ([{
                "id": submission.id, "student": current_user.username,
                "response": submission.response,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "grade": submission.grade, "feedback": submission.feedback or "",
            }] if submission else [])
        assignments.append({
            "id": assignment.id, "title": assignment.title,
            "instructions": assignment.instructions,
            "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
            "points": assignment.points,
            "submissions": submissions,
        })
    tests = []
    if teacher_view:
        for test in teaching_class.tests:
            tests.append({
                "id": test.id, "title": test.title, "instructions": test.instructions or "",
                "question_type": test.question_type, "question_count": len(test.questions),
                "opens_at": test.opens_at.isoformat() if test.opens_at else None,
                "due_at": test.due_at.isoformat() if test.due_at else None,
                "assignments": [
                    {"assignment_id": item.id, "student_id": item.student_id,
                     "student": item.student.username if item.student else "",
                     "submitted": bool(item.submission),
                     "score": float(item.submission.score) if item.submission and item.submission.score is not None else None,
                     "feedback": item.submission.feedback or "" if item.submission else "",
                     "submission_id": item.submission.id if item.submission else None,
                     "graded": bool(item.submission and item.submission.graded_at),
                     "answers": ([
                         {"prompt": answer.question.prompt, "response": answer.response,
                          "points": answer.question.points}
                         for answer in item.submission.answers
                     ] if item.submission else [])}
                    for item in test.assignments
                ],
            })
    else:
        student_test_assignments = TeachingTestAssignment.query.join(TeachingTest).filter(
            TeachingTest.class_id == teaching_class.id,
            TeachingTestAssignment.student_id == current_user.id,
        ).order_by(TeachingTest.created_at.desc()).all()
        now = datetime.utcnow()
        for item in student_test_assignments:
            test = item.test
            submission = item.submission
            tests.append({
                "id": test.id, "assignment_id": item.id,
                "title": test.title, "instructions": test.instructions or "",
                "question_type": test.question_type, "question_count": len(test.questions),
                "opens_at": test.opens_at.isoformat() if test.opens_at else None,
                "due_at": test.due_at.isoformat() if test.due_at else None,
                "submitted": bool(submission),
                "score": float(submission.score) if submission and submission.score is not None else None,
                "feedback": submission.feedback or "" if submission else "",
                "available": bool(teaching_class.is_active)
                    and (not test.opens_at or now >= test.opens_at)
                    and (not test.due_at or now <= test.due_at)
                    and not submission,
            })
    return jsonify({
        "success": True,
        "teacher_view": teacher_view,
        "class": _teaching_class_payload(teaching_class, teacher_view),
        "students": ([
            {"id": student.id, "username": student.username}
            for student in User.query.join(TeachingEnrollment, TeachingEnrollment.student_id == User.id)
            .filter(TeachingEnrollment.class_id == teaching_class.id, User.role == UserRole.STUDENT.value)
            .order_by(User.username).all()
        ] if teacher_view else []),
        "announcements": [
            {"id": item.id, "title": item.title, "body": item.body,
             "author": item.author.username if item.author else "",
             "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in teaching_class.announcements
        ],
        "materials": [
            {"id": item.id, "title": item.title, "description": item.description or "", "url": item.resource_url}
            for item in teaching_class.materials
        ],
        "sessions": [
            {
                "id": item.id, "class_id": item.class_id, "title": item.title,
                "starts_at": item.starts_at.isoformat() if item.starts_at else None,
                "duration_minutes": item.duration_minutes,
                "meeting_url": item.meeting_url or "", "notes": item.notes or "",
                "attendance": ([
                    {"student_id": entry.student_id,
                     "student": entry.student.username if entry.student else "",
                     "status": entry.status}
                    for entry in item.attendance_records
                ] if teacher_view else next((entry.status for entry in item.attendance_records
                    if entry.student_id == current_user.id), None)),
                "feedback": ([
                    {"student": entry.student.username if entry.student else "",
                     "rating": entry.rating, "comments": entry.comments or ""}
                    for entry in item.feedback_entries
                ] if teacher_view else next((
                    {"rating": entry.rating, "comments": entry.comments or ""}
                    for entry in item.feedback_entries if entry.student_id == current_user.id
                ), None)),
                "feedback_available": bool(item.starts_at and
                    item.starts_at + timedelta(minutes=item.duration_minutes) <= datetime.utcnow()),
            }
            for item in teaching_class.sessions
        ],
        "assignments": assignments,
        "tests": tests,
    })


@mobile_api_bp.post("/teaching/classes/<int:class_id>/materials")
@mobile_login_required
def teaching_add_material(class_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can add class materials."}), 403
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if not teaching_class.is_active:
        return jsonify({"success": False, "message": "Archived classes cannot be changed."}), 409
    data = request.get_json(silent=True) or {}
    title, raw_url = data.get("title"), data.get("resource_url")
    description = data.get("description", "")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
        return jsonify({"success": False, "message": "Enter a material title of up to 160 characters."}), 400
    if not isinstance(description, str) or len(description) > 2000:
        return jsonify({"success": False, "message": "Description must be 2,000 characters or fewer."}), 400
    parsed = urlparse(raw_url.strip()) if isinstance(raw_url, str) else None
    if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return jsonify({"success": False, "message": "Enter a valid HTTP or HTTPS resource link."}), 400
    db.session.add(TeachingMaterial(
        class_id=teaching_class.id, title=title.strip(), description=description.strip() or None,
        resource_url=raw_url.strip(),
    ))
    db.session.commit()
    return jsonify({"success": True, "message": "Learning material added."}), 201


@mobile_api_bp.post("/teaching/classes/<int:class_id>/sessions")
@mobile_login_required
def teaching_add_session(class_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can schedule class sessions."}), 403
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if not teaching_class.is_active:
        return jsonify({"success": False, "message": "Archived classes cannot be changed."}), 409
    data = request.get_json(silent=True) or {}
    title, starts_raw = data.get("title"), data.get("starts_at")
    try:
        starts_at = datetime.fromisoformat(str(starts_raw).replace("Z", "+00:00"))
        if starts_at.tzinfo:
            starts_at = starts_at.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        starts_at = None
    try:
        duration = int(data.get("duration_minutes", 60))
    except (TypeError, ValueError):
        duration = 0
    meeting_url = data.get("meeting_url", "")
    notes = data.get("notes", "")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160 or starts_at is None:
        return jsonify({"success": False, "message": "Enter a title and valid ISO start date/time."}), 400
    if not 1 <= duration <= 480:
        return jsonify({"success": False, "message": "Session duration must be between 1 and 480 minutes."}), 400
    if not isinstance(meeting_url, str) or len(meeting_url) > 500 or not isinstance(notes, str) or len(notes) > 4000:
        return jsonify({"success": False, "message": "Meeting link or notes are too long."}), 400
    if meeting_url.strip():
        parsed = urlparse(meeting_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return jsonify({"success": False, "message": "Meeting links must use HTTP or HTTPS."}), 400
    session_item = TeachingSession(
        class_id=teaching_class.id, title=title.strip(), starts_at=starts_at,
        duration_minutes=duration, meeting_url=meeting_url.strip() or None,
        notes=notes.strip() or None,
    )
    db.session.add(session_item)
    db.session.commit()
    return jsonify({"success": True, "message": "Online class session scheduled."}), 201


@mobile_api_bp.patch("/teaching/sessions/<int:session_id>/attendance")
@mobile_login_required
def teaching_update_attendance(session_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can record attendance."}), 403
    session_item = TeachingSession.query.get(session_id)
    if not session_item or not _teaching_class_access(session_item.class_id):
        return jsonify({"success": False, "message": "Session not found or you do not have access."}), 404
    data = request.get_json(silent=True) or {}
    statuses = data.get("attendance")
    allowed = {"present", "absent", "late", "excused"}
    if not isinstance(statuses, list) or not statuses:
        return jsonify({"success": False, "message": "Choose attendance for at least one enrolled student."}), 400
    valid_ids = {row.student_id for row in TeachingEnrollment.query.filter_by(class_id=session_item.class_id).all()}
    staged = []
    for entry in statuses:
        if not isinstance(entry, dict):
            return jsonify({"success": False, "message": "Attendance data is invalid."}), 400
        try:
            student_id = int(entry.get("student_id"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Student selection is invalid."}), 400
        status = entry.get("status")
        if student_id not in valid_ids or status not in allowed:
            return jsonify({"success": False, "message": "Use a valid enrolled student and attendance status."}), 400
        staged.append((student_id, status))
    for student_id, status in staged:
        record = TeachingAttendance.query.filter_by(session_id=session_item.id, student_id=student_id).first()
        if record is None:
            record = TeachingAttendance(session_id=session_item.id, student_id=student_id,
                                        status=status, marked_by_id=current_user.id)
            db.session.add(record)
        else:
            record.status = status
            record.marked_by_id = current_user.id
            record.marked_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Attendance saved."})


@mobile_api_bp.post("/teaching/sessions/<int:session_id>/feedback")
@mobile_login_required
def teaching_submit_session_feedback(session_id):
    if current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Only students can submit session feedback."}), 403
    session_item = TeachingSession.query.get(session_id)
    if not session_item or not TeachingEnrollment.query.filter_by(
        class_id=session_item.class_id, student_id=current_user.id
    ).first():
        return jsonify({"success": False, "message": "Session not found or you are not enrolled."}), 404
    if session_item.starts_at + timedelta(minutes=session_item.duration_minutes) > datetime.utcnow():
        return jsonify({"success": False, "message": "Feedback is available after the session ends."}), 409
    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        rating = 0
    comments = data.get("comments", "")
    if rating not in range(1, 6) or not isinstance(comments, str) or len(comments) > 3000:
        return jsonify({"success": False, "message": "Choose a 1 to 5 rating and keep feedback under 3,000 characters."}), 400
    feedback = TeachingSessionFeedback.query.filter_by(session_id=session_item.id, student_id=current_user.id).first()
    if feedback is None:
        feedback = TeachingSessionFeedback(session_id=session_item.id, student_id=current_user.id, rating=rating)
        db.session.add(feedback)
    feedback.rating = rating
    feedback.comments = comments.strip() or None
    feedback.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Session feedback saved."})


TEACHER_EFFORT_CATEGORIES = {"preparation", "live teaching", "grading", "mentoring", "admin"}
STUDENT_EFFORT_CATEGORIES = {"class study", "assignment", "revision", "practice"}


@mobile_api_bp.get("/teaching/effort")
@mobile_login_required
def teaching_effort_logs():
    if current_user.role not in {UserRole.TEACHER.value, UserRole.STUDENT.value}:
        return jsonify({"success": False, "message": "Effort logs are available to teachers and students."}), 403
    logs = TeachingEffortLog.query.filter_by(user_id=current_user.id).order_by(
        TeachingEffortLog.logged_at.desc()
    ).limit(100).all()
    return jsonify({"success": True, "logs": [
        {"id": item.id, "category": item.category, "minutes": item.minutes,
         "note": item.note or "", "class_id": item.class_id,
         "class_title": item.teaching_class.title if item.teaching_class else "General",
         "visible_to_teacher": item.visible_to_teacher,
         "logged_at": item.logged_at.isoformat() if item.logged_at else None}
        for item in logs
    ]})


@mobile_api_bp.post("/teaching/effort")
@mobile_login_required
def teaching_log_effort():
    is_teacher = current_user.role == UserRole.TEACHER.value
    if not is_teacher and current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Effort logs are available to teachers and students."}), 403
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    note = data.get("note", "")
    try:
        minutes = int(data.get("minutes"))
    except (TypeError, ValueError):
        minutes = 0
    allowed = TEACHER_EFFORT_CATEGORIES if is_teacher else STUDENT_EFFORT_CATEGORIES
    class_id = data.get("class_id")
    teaching_class = None
    if class_id not in (None, ""):
        try:
            teaching_class = _teaching_class_access(int(class_id))
        except (TypeError, ValueError):
            teaching_class = None
        if not teaching_class:
            return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if category not in allowed or not 1 <= minutes <= 1440 or not isinstance(note, str) or len(note) > 500:
        return jsonify({"success": False, "message": "Choose a valid activity and enter 1 to 1,440 minutes."}), 400
    visible = (not is_teacher and teaching_class is not None and data.get("visible_to_teacher") is True)
    db.session.add(TeachingEffortLog(
        user_id=current_user.id, class_id=teaching_class.id if teaching_class else None,
        category=category, minutes=minutes, note=note.strip() or None,
        visible_to_teacher=visible,
    ))
    db.session.commit()
    return jsonify({"success": True, "message": "Effort log saved."}), 201


@mobile_api_bp.post("/teaching/classes/<int:class_id>/tests")
@mobile_login_required
def teaching_create_test(class_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can create class tests."}), 403
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if not teaching_class.is_active:
        return jsonify({"success": False, "message": "Archived classes cannot be changed."}), 409
    data = request.get_json(silent=True) or {}
    title, question_type = data.get("title"), data.get("question_type")
    instructions = data.get("instructions", "")
    raw_questions, raw_students = data.get("questions"), data.get("student_ids")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
        return jsonify({"success": False, "message": "Enter a test title of 1 to 160 characters."}), 400
    if not isinstance(instructions, str) or len(instructions) > 4000:
        return jsonify({"success": False, "message": "Test instructions must be 4,000 characters or fewer."}), 400
    if question_type not in {"mcq", "short_answer"}:
        return jsonify({"success": False, "message": "Choose a multiple-choice or short-answer test."}), 400
    if not isinstance(raw_questions, list) or not 1 <= len(raw_questions) <= 20:
        return jsonify({"success": False, "message": "Add 1 to 20 test questions."}), 400
    if not isinstance(raw_students, list) or not raw_students:
        return jsonify({"success": False, "message": "Select at least one enrolled student."}), 400
    try:
        student_ids = {int(value) for value in raw_students}
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Student selection is invalid."}), 400
    valid_student_ids = {
        row[0] for row in db.session.query(User.id).join(TeachingEnrollment, TeachingEnrollment.student_id == User.id)
        .filter(TeachingEnrollment.class_id == teaching_class.id, User.id.in_(student_ids),
                User.role == UserRole.STUDENT.value, User.is_active.is_(True), User.is_approved.is_(True)).all()
    }
    if valid_student_ids != student_ids:
        return jsonify({"success": False, "message": "Choose only active students enrolled in this class."}), 400
    questions = []
    total_points = 0
    for index, question in enumerate(raw_questions):
        if not isinstance(question, dict):
            return jsonify({"success": False, "message": "Each test question must be an object."}), 400
        prompt, points_raw = question.get("prompt"), question.get("points", 1)
        try:
            points = int(points_raw)
        except (TypeError, ValueError):
            points = 0
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt.strip()) > 1000 or not 1 <= points <= 1000:
            return jsonify({"success": False, "message": "Questions need text and 1 to 1,000 points."}), 400
        item = {"prompt": prompt.strip(), "points": points, "position": index}
        if question_type == "mcq":
            choices = question.get("choices")
            correct = str(question.get("correct_option", "")).upper()
            if not isinstance(choices, list) or len(choices) != 4 or any(
                not isinstance(choice, str) or not choice.strip() or len(choice.strip()) > 250 for choice in choices
            ) or correct not in {"A", "B", "C", "D"}:
                return jsonify({"success": False, "message": "Each multiple-choice question needs four options and a correct option."}), 400
            item.update(choices=[choice.strip() for choice in choices], correct_option=correct)
        questions.append(item)
        total_points += points
    if total_points > 10000:
        return jsonify({"success": False, "message": "A test can have up to 10,000 total points."}), 400
    def parse_test_time(value):
        if not value:
            return None
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    try:
        opens_at = parse_test_time(data.get("opens_at"))
        due_at = parse_test_time(data.get("due_at"))
    except ValueError:
        return jsonify({"success": False, "message": "Enter valid opening and due dates."}), 400
    effective_open = opens_at or datetime.utcnow()
    if due_at and due_at <= effective_open:
        return jsonify({"success": False, "message": "The deadline must be after the opening time."}), 400
    test = TeachingTest(
        class_id=teaching_class.id, created_by_id=current_user.id,
        title=title.strip(), instructions=instructions.strip() or None,
        question_type=question_type, opens_at=opens_at, due_at=due_at,
    )
    db.session.add(test)
    db.session.flush()
    for question in questions:
        db.session.add(TeachingTestQuestion(test_id=test.id, **question))
    test_assignments = [TeachingTestAssignment(test_id=test.id, student_id=student_id) for student_id in student_ids]
    db.session.add_all(test_assignments)
    db.session.commit()
    return jsonify({"success": True, "message": "Test created and assigned.", "test_id": test.id}), 201


@mobile_api_bp.get("/teaching/test-assignments/<int:assignment_id>/take")
@mobile_login_required
def teaching_take_test(assignment_id):
    if current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Only students can take class tests."}), 403
    assignment = TeachingTestAssignment.query.filter_by(id=assignment_id, student_id=current_user.id).first()
    if not assignment:
        return jsonify({"success": False, "message": "Assigned test not found."}), 404
    test = assignment.test
    now = datetime.utcnow()
    if not test.teaching_class.is_active:
        return jsonify({"success": False, "message": "This class is archived."}), 409
    if test.opens_at and now < test.opens_at:
        return jsonify({"success": False, "message": "This test is not open yet."}), 403
    if test.due_at and now > test.due_at:
        return jsonify({"success": False, "message": "The test deadline has passed."}), 410
    if assignment.submission:
        return jsonify({"success": False, "message": "You have already submitted this test."}), 409
    return jsonify({
        "success": True,
        "assignment_id": assignment.id,
        "test": {"id": test.id, "title": test.title, "instructions": test.instructions or "",
                 "question_type": test.question_type, "due_at": test.due_at.isoformat() if test.due_at else None},
        "questions": [
            {"id": question.id, "prompt": question.prompt, "points": question.points,
             "choices": question.choices if test.question_type == "mcq" else None}
            for question in test.questions
        ],
    })


@mobile_api_bp.post("/teaching/test-assignments/<int:assignment_id>/submit")
@mobile_login_required
def teaching_submit_test(assignment_id):
    if current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Only students can submit class tests."}), 403
    assignment = TeachingTestAssignment.query.filter_by(id=assignment_id, student_id=current_user.id).first()
    if not assignment:
        return jsonify({"success": False, "message": "Assigned test not found."}), 404
    test = assignment.test
    now = datetime.utcnow()
    if not test.teaching_class.is_active:
        return jsonify({"success": False, "message": "This class is archived."}), 409
    if test.opens_at and now < test.opens_at:
        return jsonify({"success": False, "message": "This test is not open yet."}), 403
    if test.due_at and now > test.due_at:
        return jsonify({"success": False, "message": "The test deadline has passed."}), 410
    if assignment.submission:
        return jsonify({"success": False, "message": "This test was already submitted."}), 409
    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if not isinstance(answers, dict):
        return jsonify({"success": False, "message": "Provide one answer for each test question."}), 400
    staged, score = [], 0
    for question in test.questions:
        response = answers.get(str(question.id))
        if not isinstance(response, str) or not response.strip() or len(response.strip()) > 5000:
            return jsonify({"success": False, "message": "Answer every question using up to 5,000 characters."}), 400
        response = response.strip()
        is_correct = None
        if test.question_type == "mcq":
            response = response.upper()
            if response not in {"A", "B", "C", "D"}:
                return jsonify({"success": False, "message": "Choose one listed option for every question."}), 400
            is_correct = response == question.correct_option
            if is_correct:
                score += question.points
        staged.append((question, response, is_correct))
    submission = TeachingTestSubmission(
        assignment_id=assignment.id,
        score=score if test.question_type == "mcq" else None,
        graded_at=now if test.question_type == "mcq" else None,
    )
    db.session.add(submission)
    db.session.flush()
    db.session.add_all([
        TeachingTestAnswer(submission_id=submission.id, question_id=question.id,
                           response=response, is_correct=is_correct)
        for question, response, is_correct in staged
    ])
    db.session.commit()
    log_user_action("Submit Class Test", f"Submitted test {test.id} from native app")
    return jsonify({"success": True, "message": "Test submitted.", "score": score if test.question_type == "mcq" else None}), 201


@mobile_api_bp.post("/teaching/test-submissions/<int:submission_id>/grade")
@mobile_login_required
def teaching_grade_test_submission(submission_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can grade test submissions."}), 403
    submission = TeachingTestSubmission.query.get(submission_id)
    if not submission or not _teaching_class_access(submission.assignment.test.class_id):
        return jsonify({"success": False, "message": "Submission not found or you do not have access."}), 404
    test = submission.assignment.test
    if test.question_type != "short_answer":
        return jsonify({"success": False, "message": "Multiple-choice tests are graded automatically."}), 409
    data = request.get_json(silent=True) or {}
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a numeric score."}), 400
    max_score = sum(question.points for question in test.questions)
    feedback = data.get("feedback", "")
    if not 0 <= score <= max_score:
        return jsonify({"success": False, "message": f"Score must be from 0 to {max_score}."}), 400
    if not isinstance(feedback, str) or len(feedback) > 5000:
        return jsonify({"success": False, "message": "Feedback must be 5,000 characters or fewer."}), 400
    submission.score = score
    submission.feedback = feedback.strip() or None
    submission.graded_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Test score and feedback saved."})


@mobile_api_bp.post("/teaching/classes/<int:class_id>/announcements")
@mobile_login_required
def teaching_add_announcement(class_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can post class announcements."}), 403
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if not teaching_class.is_active:
        return jsonify({"success": False, "message": "Archived classes cannot be changed."}), 409
    data = request.get_json(silent=True) or {}
    title, body = data.get("title"), data.get("body")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140 or not isinstance(body, str) or not body.strip():
        return jsonify({"success": False, "message": "Announcement title and message are required."}), 400
    announcement = TeachingAnnouncement(
        class_id=teaching_class.id, author_id=current_user.id,
        title=title.strip(), body=body.strip(),
    )
    db.session.add(announcement)
    db.session.commit()
    return jsonify({"success": True, "message": "Announcement posted."}), 201


@mobile_api_bp.post("/teaching/classes/<int:class_id>/assignments")
@mobile_login_required
def teaching_add_assignment(class_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can publish assignments."}), 403
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    if not teaching_class.is_active:
        return jsonify({"success": False, "message": "Archived classes cannot be changed."}), 409
    data = request.get_json(silent=True) or {}
    title, instructions = data.get("title"), data.get("instructions")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160 or not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 10000:
        return jsonify({"success": False, "message": "Enter an assignment title and instructions."}), 400
    due_at = None
    due_raw = data.get("due_at")
    if due_raw:
        try:
            due_at = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
            if due_at.tzinfo:
                due_at = due_at.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            return jsonify({"success": False, "message": "Enter a valid due date and time."}), 400
    try:
        points = int(data["points"]) if data.get("points") not in (None, "") else None
        if points is not None and not 1 <= points <= 10000:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Points must be between 1 and 10,000."}), 400
    assignment = TeachingAssignment(
        class_id=teaching_class.id, title=title.strip(), instructions=instructions.strip(),
        due_at=due_at, points=points,
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({"success": True, "message": "Assignment published."}), 201


@mobile_api_bp.post("/teaching/assignments/<int:assignment_id>/submit")
@mobile_login_required
def teaching_submit_assignment(assignment_id):
    if current_user.role != UserRole.STUDENT.value:
        return jsonify({"success": False, "message": "Only students can submit class assignments."}), 403
    assignment = TeachingAssignment.query.get(assignment_id)
    if not assignment or not TeachingEnrollment.query.filter_by(
        class_id=assignment.class_id, student_id=current_user.id
    ).first():
        return jsonify({"success": False, "message": "Assignment not found or you are not enrolled."}), 404
    if not assignment.teaching_class.is_active:
        return jsonify({"success": False, "message": "This class is archived."}), 409
    if assignment.due_at and assignment.due_at < datetime.utcnow():
        return jsonify({"success": False, "message": "The assignment due date has passed."}), 410
    data = request.get_json(silent=True) or {}
    response = data.get("response")
    if not isinstance(response, str) or not response.strip() or len(response) > 20000:
        return jsonify({"success": False, "message": "Enter a response of up to 20,000 characters."}), 400
    submission = TeachingSubmission.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
    if not submission:
        submission = TeachingSubmission(assignment_id=assignment.id, student_id=current_user.id, response=response.strip())
        db.session.add(submission)
    else:
        submission.response = response.strip()
        submission.submitted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Assignment response submitted."}), 201


@mobile_api_bp.post("/teaching/submissions/<int:submission_id>/grade")
@mobile_login_required
def teaching_grade_submission(submission_id):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Only teachers can grade submissions."}), 403
    submission = TeachingSubmission.query.get(submission_id)
    if not submission or not _teaching_class_access(submission.assignment.class_id):
        return jsonify({"success": False, "message": "Submission not found or you do not have access."}), 404
    data = request.get_json(silent=True) or {}
    try:
        grade = float(data["grade"]) if data.get("grade") not in (None, "") else None
        if grade is not None and (grade < 0 or (submission.assignment.points is not None and grade > submission.assignment.points)):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a grade within the assignment point range."}), 400
    feedback = data.get("feedback", "")
    if not isinstance(feedback, str) or len(feedback) > 5000:
        return jsonify({"success": False, "message": "Feedback must be 5,000 characters or fewer."}), 400
    submission.grade = grade
    submission.feedback = feedback.strip() or None
    submission.graded_at = datetime.utcnow() if grade is not None or feedback.strip() else None
    db.session.commit()
    return jsonify({"success": True, "message": "Feedback saved."})


@mobile_api_bp.get("/developer/dashboard")
@mobile_login_required
def developer_dashboard():
    denied = _require_role("developer")
    if denied:
        return denied
    activities = ActivityUpdate.query.order_by(ActivityUpdate.timestamp.desc()).limit(50).all()
    snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id).order_by(CodeSnippet.timestamp.desc()).limit(50).all()
    return jsonify({
        "success": True,
        "activities": [
            {
                "id": activity.id,
                "content": activity.content,
                "author": activity.author.username if activity.author else "",
                "created_at": activity.timestamp.isoformat() if activity.timestamp else None,
            }
            for activity in activities
        ],
        "snippets": [
            {
                "id": snippet.id,
                "sender": snippet.snippet_sender.username if snippet.snippet_sender else "",
                "code": snippet.code,
                "language": snippet.language,
                "created_at": snippet.timestamp.isoformat() if snippet.timestamp else None,
            }
            for snippet in snippets
        ],
    })


@mobile_api_bp.post("/developer/activities")
@mobile_login_required
def developer_post_activity():
    denied = _require_role("developer")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return jsonify({"success": False, "message": "Activity text is required."}), 400
    activity = ActivityUpdate(content=content.strip(), author=current_user)
    db.session.add(activity)
    db.session.commit()
    log_user_action("Post Activity", "Posted developer activity from native app")
    return jsonify({"success": True, "message": "Activity posted.", "id": activity.id}), 201


@mobile_api_bp.delete("/developer/snippets/<int:snippet_id>")
@mobile_login_required
def developer_delete_snippet(snippet_id):
    denied = _require_role("developer")
    if denied:
        return denied
    snippet = CodeSnippet.query.filter_by(id=snippet_id, recipient_id=current_user.id).first()
    if not snippet:
        return jsonify({"success": False, "message": "Snippet not found."}), 404
    db.session.delete(snippet)
    db.session.commit()
    return jsonify({"success": True, "message": "Snippet deleted."})


@mobile_api_bp.get("/recruiter/dashboard")
@mobile_login_required
def recruiter_dashboard():
    denied = _require_role("recruiter")
    if denied:
        return denied
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).all()
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value).order_by(User.username).all()
    moderators = User.query.filter_by(role=UserRole.MODERATOR.value).order_by(User.username).all()
    return jsonify({
        "success": True,
        "jobs": [
            {"id": job.id, "title": job.title, "description": job.description,
             "is_open": job.is_open, "created_at": job.created_at.isoformat() if job.created_at else None,
             "application_count": len(job.applications)}
            for job in jobs
        ],
        "applications": [
            {"id": application.id, "job_id": application.job_id,
             "job_title": application.job.title if application.job else "",
             "candidate_id": application.user_id,
             "candidate": application.candidate.username if application.candidate else "",
             "status": application.status,
             "applied_at": application.applied_at.isoformat() if application.applied_at else None,
             "resume_url": application.resume_url or ""}
            for application in applications
        ],
        "candidates": [
            {"id": user.id, "username": user.username, "email": user.email,
             "primary_skill": user.primary_skill or "", "resume_available": bool(user.resume_filename),
             "has_test": bool(user.assigned_problem), "moderator_id": user.moderator_id}
            for user in candidates
        ],
        "moderators": [{"id": user.id, "username": user.username} for user in moderators],
    })


@mobile_api_bp.post("/recruiter/jobs")
@mobile_login_required
def recruiter_post_job():
    denied = _require_role("recruiter")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    description = data.get("description")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 150:
        return jsonify({"success": False, "message": "Enter a job title of 1 to 150 characters."}), 400
    if not isinstance(description, str) or not description.strip():
        return jsonify({"success": False, "message": "Job description is required."}), 400
    job = JobOpening(title=title.strip(), description=description.strip())
    db.session.add(job)
    db.session.commit()
    log_user_action("Post Job", f"Recruiter posted job {job.title} from native app")
    return jsonify({"success": True, "message": "Job opening posted.", "job_id": job.id}), 201


@mobile_api_bp.patch("/recruiter/applications/<int:application_id>")
@mobile_login_required
def recruiter_update_application(application_id):
    denied = _require_role("recruiter")
    if denied:
        return denied
    application = JobApplication.query.get(application_id)
    if not application:
        return jsonify({"success": False, "message": "Application not found."}), 404
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    statuses = {"accept": ApplicationStatus.ACCEPTED.value, "reject": ApplicationStatus.REJECTED.value}
    if action not in statuses:
        return jsonify({"success": False, "message": "Choose accept or reject."}), 400
    application.status = statuses[action]
    db.session.commit()
    try:
        send_email(
            to=application.candidate.email,
            subject=f"Update on your application for {application.job.title}",
            template="mail/application_status_update.html",
            candidate=application.candidate,
            job=application.job,
            status=application.status,
            now=datetime.utcnow(),
        )
    except Exception:
        current_app.logger.exception("Application status saved but candidate notification failed")
    log_user_action(f"{action.title()} Application", f"Updated application {application.id} from native app")
    return jsonify({"success": True, "message": f"Application marked {application.status}.", "status": application.status})


@mobile_api_bp.post("/recruiter/moderator-assignments")
@mobile_login_required
def recruiter_assign_moderator():
    denied = _require_role("recruiter")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        candidate_id = int(data.get("candidate_id"))
        moderator_id = int(data.get("moderator_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a candidate and moderator."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    moderator = User.query.filter_by(id=moderator_id, role=UserRole.MODERATOR.value).first()
    if not candidate or not moderator:
        return jsonify({"success": False, "message": "Candidate or moderator was not found."}), 404
    if not candidate.assigned_problem:
        return jsonify({"success": False, "message": "Schedule a coding test for the candidate before assigning a moderator."}), 400
    candidate.moderator_id = moderator.id
    db.session.add(ModeratorAssignmentHistory(
        candidate_id=candidate.id,
        moderator_id=moderator.id,
        problem_statement_id=candidate.problem_statement_id,
    ))
    db.session.commit()
    log_user_action("Assign Moderator", f"Assigned {moderator.username} to {candidate.username} from native app")
    return jsonify({"success": True, "message": f"{moderator.username} assigned to {candidate.username}."}), 201


@mobile_api_bp.get("/moderator/dashboard")
@mobile_login_required
def moderator_dashboard():
    denied = _require_role("moderator")
    if denied:
        return denied
    candidates = User.query.filter_by(moderator_id=current_user.id).order_by(User.username).all()
    interviews = Interview.query.join(InterviewParticipant).filter(
        InterviewParticipant.user_id == current_user.id,
        InterviewParticipant.role == "moderator",
    ).order_by(Interview.scheduled_time.desc()).all()
    return jsonify({
        "success": True,
        "candidates": [
            {"id": user.id, "username": user.username, "primary_skill": user.primary_skill or "",
             "test_completed": user.test_completed,
             "resume_available": bool(user.resume_filename)}
            for user in candidates
        ],
        "interviews": [
            {
                "id": interview.id,
                "title": interview.title,
                "description": interview.description or "",
                "candidate": interview.candidate.username if interview.candidate else "",
                "candidate_id": interview.candidate_id,
                "scheduled_time": interview.scheduled_time.isoformat() if interview.scheduled_time else None,
                "duration_minutes": interview.duration_minutes,
                "meeting_url": interview.google_meet_link or "",
                "status": interview.status,
                "feedback_submitted": bool(InterviewFeedback.query.filter_by(
                    interview_id=interview.id, moderator_id=current_user.id
                ).first()),
            }
            for interview in interviews
        ],
    })


@mobile_api_bp.post("/moderator/interviews/<int:interview_id>/feedback")
@mobile_login_required
def moderator_submit_interview_feedback(interview_id):
    denied = _require_role("moderator")
    if denied:
        return denied
    interview = Interview.query.get(interview_id)
    participant = InterviewParticipant.query.filter_by(
        interview_id=interview_id, user_id=current_user.id, role="moderator"
    ).first()
    if not interview or not participant:
        return jsonify({"success": False, "message": "Interview not found or not assigned to you."}), 404
    if InterviewFeedback.query.filter_by(interview_id=interview.id, moderator_id=current_user.id).first():
        return jsonify({"success": False, "message": "Feedback has already been submitted."}), 409
    data = request.get_json(silent=True) or {}
    rating_fields = (
        "communication_skills", "technical_knowledge", "problem_solving",
        "cultural_fit", "overall_impression",
    )
    ratings = {}
    try:
        for field in rating_fields:
            value = int(data.get(field))
            if value < 1 or value > 5:
                raise ValueError
            ratings[field] = value
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Rate each interview category from 1 to 5."}), 400
    recommendation = data.get("recommendation")
    if recommendation not in {"hire", "maybe", "no_hire"}:
        return jsonify({"success": False, "message": "Choose a valid recommendation."}), 400
    remarks = data.get("remarks", "")
    if not isinstance(remarks, str) or len(remarks) > 5000:
        return jsonify({"success": False, "message": "Remarks must be 5,000 characters or fewer."}), 400
    feedback = InterviewFeedback(
        interview_id=interview.id, moderator_id=current_user.id,
        candidate_id=interview.candidate_id, recommendation=recommendation,
        remarks=remarks.strip() or None, **ratings,
    )
    db.session.add(feedback)
    db.session.commit()
    for admin in User.query.filter_by(role=UserRole.ADMIN.value).all():
        try:
            send_email(
                to=admin.email,
                subject=f"Interview feedback submitted: {interview.title}",
                template="mail/interview_feedback_submitted.html",
                moderator=current_user,
                candidate=interview.candidate,
                interview=interview,
                feedback=feedback,
            )
        except Exception:
            current_app.logger.exception("Interview feedback saved but admin notification failed")
    log_user_action("Submit Interview Feedback", f"Submitted feedback for interview {interview.id} from native app")
    return jsonify({"success": True, "message": "Interview feedback submitted."}), 201


@mobile_api_bp.get("/admin/overview")
@mobile_login_required
def admin_overview():
    denied = _require_role("admin")
    if denied:
        return denied
    pending_users = User.query.filter_by(is_approved=False).order_by(User.id.desc()).all()
    return jsonify({
        "success": True,
        "counts": {
            "users": User.query.count(),
            "pending_users": len(pending_users),
            "products": Product.query.count(),
            "orders": Order.query.count(),
            "open_jobs": JobOpening.query.filter_by(is_open=True).count(),
        },
        "pending_users": [
            {"id": user.id, "username": user.username, "email": user.email,
             "role": user.role, "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None}
            for user in pending_users
        ],
    })


@mobile_api_bp.post("/admin/users/<int:user_id>/decision")
@mobile_login_required
def admin_user_decision(user_id):
    denied = _require_role("admin")
    if denied:
        return denied
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision == "approve" and not user.is_approved:
        user.is_approved = True
        db.session.commit()
        try:
            send_email(
                to=user.email,
                subject="Your SourcePoint account is approved",
                template="mail/account_approved.html",
                user=user,
                now=datetime.utcnow(),
            )
        except Exception:
            current_app.logger.exception("User approved but approval notification failed")
        log_user_action("Approve User", f"Approved user {user.username} from native app")
        return jsonify({"success": True, "message": f"{user.username} has been approved."})
    if decision == "reject" and not user.is_approved:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        log_user_action("Reject User", f"Rejected registration for {username} from native app")
        return jsonify({"success": True, "message": f"Registration for {username} was rejected."})
    return jsonify({"success": False, "message": "Choose approve or reject for a pending user."}), 409
