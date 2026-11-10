"""JSON API used by the native SourcePoint Android client.

The mobile client authenticates through Flask-Login and uses the same User
records and application database as the website. Responses intentionally expose
only fields needed by the signed-in user's own app session.
"""

from functools import wraps
from threading import Thread
import csv
import json
import os
import re
import requests
from html import escape

from datetime import datetime, timedelta
import secrets
from datetime import timezone
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request, send_file, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename
from io import BytesIO

from extensions import db, bcrypt
from enums import (
    OrderStatus, GiftCardStatus, VoucherOrderStatus, UserRole, ApplicationStatus,
    InvoiceStatus, RollbackRequestStatus, RollbackTermsDecision,
    AssetType, AssetStatus, AssetCondition,
)
from models.commerce import (
    AffiliateAd, Cart, CartItem, Order, OrderItem, Product, ProductImage, SellerInventory, StockRequest, VoucherOrder,
    Invoice, InvoiceItem, InvoicePayment, InvoiceRefund, ShareableLink, SupersCoinWallet, SupersCoinTransaction,
    SupersCoinInvoice, InventoryRollbackRequest, InventoryRollbackTerms, InventoryRollbackTermsDecision,
)
from models.auth import User, ActivityUpdate, Message, ActivityLog
from models.hiring import JobApplication, JobOpening, CodeSnippet, CodeTestSubmission, ModeratorAssignmentHistory
from models.learning import ChatHistory, LearningContent, ProblemStatement
from models.newsletter import NewsArticle
from models.gift_card import GiftCard
from models.asset import Asset
from models.finance import Project, Transaction, BRD, EMIPlan, EMIPayment
from models.mcq import MCQQuestion, Test, TestAssignment, TestResult
from models.app_release import AndroidAppRelease, AppFeature
from models.teaching import (
    TeachingAnnouncement, TeachingAssignment, TeachingClass, TeachingEnrollment,
    TeachingMaterial, TeachingSession, TeachingSubmission, TeachingTest,
    TeachingTestQuestion, TeachingTestAssignment, TeachingTestSubmission, TeachingTestAnswer,
    TeachingAttendance, TeachingSessionFeedback, TeachingEffortLog,
)
from models.interview import Interview, InterviewParticipant, InterviewFeedback
from services.invoice_recipient import invoice_recipient_id
from services.auth_service import AuthService
from services.commerce_service import CommerceService
from services.hiring_service import HiringService
from services.rollback_terms_service import RollbackTermsService
from utils import enqueue_email_job, log_user_action, send_email


mobile_api_bp = Blueprint("mobile_api", __name__, url_prefix="/api/v1")
LEARNING_ROLES = {"admin", "candidate", "developer", "recruiter", "moderator", "seller", "buyer"}
LEARNING_LANGUAGES = ("java", "cpp", "c", "sql", "dbms", "plsql", "mysql")


def _public_article_payload(article):
    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary or "",
        "source_name": article.source_name or "",
        "source_url": article.source_url,
        "image_url": article.image_url or "",
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "content": article.content or "",
        "author": article.author or "",
        "reading_time": article.reading_time,
    }


def _public_product_payload(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description or "",
        "category": product.category or "",
        "brand": product.brand or "",
        "price": float(product.price or 0),
        "mrp": float(product.mrp) if product.mrp is not None else None,
        "image_url": product.image_url or "",
        "images": [image.image_url for image in product.images],
    }


@mobile_api_bp.get("/public/home")
def public_home():
    featured_products = Product.query.filter(Product.stock > 0).order_by(Product.id.desc()).limit(8).all()
    offers = AffiliateAd.query.order_by(AffiliateAd.id.desc()).limit(6).all()
    try:
        articles = NewsArticle.query.order_by(
            NewsArticle.published_at.desc().nullslast(),
            NewsArticle.fetched_at.desc(),
        ).limit(5).all()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Public mobile home could not load news")
        articles = []
    return jsonify({
        "success": True,
        "products": [_public_product_payload(product) for product in featured_products],
        "offers": [
            {"id": offer.id, "name": offer.ad_name, "url": offer.affiliate_link}
            for offer in offers
        ],
        "news": [_public_article_payload(article) for article in articles],
    })


@mobile_api_bp.get("/public/offers")
def public_offers():
    offers = AffiliateAd.query.order_by(AffiliateAd.id.desc()).all()
    return jsonify({
        "success": True,
        "offers": [
            {"id": offer.id, "name": offer.ad_name, "url": offer.affiliate_link}
            for offer in offers
        ],
    })


@mobile_api_bp.get("/public/news")
def public_news():
    page = max(request.args.get("page", 1, type=int), 1)
    query_text = request.args.get("q", "", type=str).strip()[:200]
    query = NewsArticle.query
    if query_text:
        pattern = f"%{query_text}%"
        query = query.filter(or_(
            NewsArticle.title.ilike(pattern),
            NewsArticle.summary.ilike(pattern),
            NewsArticle.source_name.ilike(pattern),
        ))
    pagination = query.order_by(
        NewsArticle.published_at.desc().nullslast(),
        NewsArticle.fetched_at.desc(),
    ).paginate(page=page, per_page=12, error_out=False)
    return jsonify({
        "success": True,
        "items": [_public_article_payload(article) for article in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@mobile_api_bp.get("/public/news/<int:article_id>")
def public_news_article(article_id):
    article = NewsArticle.query.filter_by(id=article_id).first()
    if not article:
        return jsonify({"success": False, "message": "Article not found."}), 404
    related = NewsArticle.query.filter(
        NewsArticle.id != article.id,
        NewsArticle.source_name == article.source_name,
    ).order_by(NewsArticle.published_at.desc().nullslast()).limit(4).all()
    payload = _public_article_payload(article)
    payload["related"] = [_public_article_payload(item) for item in related]
    return jsonify({"success": True, "article": payload})


@mobile_api_bp.post("/public/contact")
def public_contact():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:120]
    email = str(data.get("email", "")).strip()[:254]
    subject = str(data.get("subject", "SourcePoint support request")).strip()[:160]
    message = str(data.get("message", "")).strip()
    if not name or not email or not message:
        return jsonify({"success": False, "message": "Name, email, and message are required."}), 400
    if len(message) > 10000 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"success": False, "message": "Enter a valid email and a message under 10,000 characters."}), 400
    admin = User.query.filter_by(role=UserRole.ADMIN.value).first()
    recipient = admin.email if admin else "admin@sourcepoint.in"
    safe_body = (
        "<h3>Support request from the SourcePoint Android app</h3>"
        f"<p><strong>Name:</strong> {escape(name)}</p>"
        f"<p><strong>Email:</strong> {escape(email)}</p>"
        f"<p><strong>Subject:</strong> {escape(subject)}</p>"
        f"<p><strong>Message:</strong></p><p>{escape(message).replace(chr(10), '<br>')}</p>"
    )
    try:
        send_email(
            to=[recipient],
            subject=f"SourcePoint support: {subject}",
            template="mail/broadcast.html",
            user=admin or type("SupportRecipient", (), {"username": "Admin", "email": recipient})(),
            body=safe_body,
        )
    except Exception:
        current_app.logger.exception("Native public contact email could not be queued")
        return jsonify({"success": False, "message": "Your message could not be sent. Try again later."}), 503
    return jsonify({"success": True, "message": "Your message has been sent to SourcePoint support."}), 202


def _public_store_products(link, search="", category=""):
    seller = User.query.filter_by(id=link.seller_id).first()
    if not seller:
        return None, None
    if seller.role == UserRole.ADMIN.value:
        query = Product.query.filter(Product.stock > 0)
    else:
        query = Product.query.join(
            SellerInventory, SellerInventory.product_id == Product.id,
        ).filter(
            SellerInventory.seller_id == seller.id,
            SellerInventory.stock > 0,
        )
    if search:
        pattern = f"%{search[:200]}%"
        query = query.filter(or_(
            Product.name.ilike(pattern),
            Product.description.ilike(pattern),
            Product.category.ilike(pattern),
        ))
    if category:
        query = query.filter(Product.category == category[:100])
    return seller, query


@mobile_api_bp.get("/public/shop/<token>")
@mobile_api_bp.get("/public/shop/<token>/products")
def public_shop_products(token):
    link = ShareableLink.query.filter_by(token=token, is_active=True).first()
    if not link:
        return jsonify({"success": False, "message": "This seller catalog is unavailable."}), 404
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    seller, query = _public_store_products(link, search, category)
    if not seller:
        return jsonify({"success": False, "message": "This seller catalog is unavailable."}), 404
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = query.order_by(Product.id.desc()).paginate(page=page, per_page=24, error_out=False)
    categories_query = db.session.query(Product.category)
    if seller.role == UserRole.ADMIN.value:
        categories_query = categories_query.filter(Product.stock > 0)
    else:
        categories_query = categories_query.join(
            SellerInventory, SellerInventory.product_id == Product.id,
        ).filter(SellerInventory.seller_id == seller.id, SellerInventory.stock > 0)
    categories = [value for (value,) in categories_query.distinct().all() if value]
    return jsonify({
        "success": True,
        "seller": {"username": seller.username, "avatar_url": seller.avatar_url},
        "categories": categories,
        "products": [_public_product_payload(product) for product in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "search": search,
        "category": category,
    })


@mobile_api_bp.get("/public/shop/<token>/products/<int:product_id>")
def public_shop_product(token, product_id):
    link = ShareableLink.query.filter_by(token=token, is_active=True).first()
    if not link:
        return jsonify({"success": False, "message": "This seller catalog is unavailable."}), 404
    seller = User.query.filter_by(id=link.seller_id).first()
    product = Product.query.filter_by(id=product_id).first()
    if not seller or not product:
        return jsonify({"success": False, "message": "Product not found in this seller catalog."}), 404
    if seller.role == UserRole.ADMIN.value:
        if product.stock <= 0:
            return jsonify({"success": False, "message": "Product is unavailable."}), 404
    else:
        allocation = SellerInventory.query.filter_by(
            seller_id=seller.id,
            product_id=product.id,
        ).first()
        if not allocation or allocation.stock <= 0:
            return jsonify({"success": False, "message": "Product not found in this seller catalog."}), 404
    return jsonify({
        "success": True,
        "seller": {"username": seller.username, "avatar_url": seller.avatar_url},
        "product": _public_product_payload(product),
    })


def _public_asset_payload(asset):
    date_fields = (
        "purchase_date", "warranty_expiry", "allocation_date", "sold_date",
        "cancelled_at", "sale_terms_accepted_at", "delivery_receipt_sent_at",
    )
    fields = (
        "asset_code", "name", "asset_type", "serial_number", "brand", "model_number",
        "purchase_price", "status", "condition", "processor", "ram", "storage_spec",
        "display", "graphics", "operating_system", "battery", "color", "asset_action",
        "location", "sold_to_name", "sold_to_email", "sale_price", "terms_and_conditions",
        "cancellation_reason", "notes",
    )
    payload = {name: getattr(asset, name) for name in fields}
    for name in date_fields:
        value = getattr(asset, name)
        payload[name] = value.isoformat() if value else None
    for name in ("purchase_price", "sale_price"):
        value = getattr(asset, name)
        payload[name] = float(value) if value is not None else None
    payload.update({
        "assigned_to": asset.assigned_to.username if asset.assigned_to else None,
        "authorized_by": asset.authorized_by.username if asset.authorized_by else None,
    })
    return payload


@mobile_api_bp.get("/public/asset/<token>")
def public_asset(token):
    """Return the public asset document linked from an assignment or sale email."""
    asset = Asset.query.filter_by(share_token=token).first()
    if not asset or (not asset.assigned_to and not asset.sold_to_email):
        return jsonify({"success": False, "message": "This asset link is unavailable."}), 404
    return jsonify({"success": True, "asset": _public_asset_payload(asset)})


@mobile_api_bp.post("/public/asset/<token>/accept")
def public_asset_accept(token):
    """Record explicit sale-terms acceptance and send the same delivery receipt as the website."""
    asset = Asset.query.filter_by(share_token=token).first()
    if not asset or asset.asset_action != "sold" or not asset.sold_to_email:
        return jsonify({"success": False, "message": "This asset sale is unavailable."}), 404
    data = request.get_json(silent=True) or {}
    if data.get("accept_terms") is not True:
        return jsonify({"success": False, "message": "Confirm that you accept the asset sale terms."}), 400

    if not asset.sale_terms_accepted_at:
        forwarded_for = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
        asset.sale_terms_accepted_at = datetime.utcnow()
        asset.sale_terms_accepted_ip = forwarded_for.split(",")[0].strip()[:64]
        asset.sale_terms_acceptance_user_agent = (request.headers.get("User-Agent", "") or "")[:255]
        db.session.commit()

    receipt_sent = bool(asset.delivery_receipt_sent_at)
    if not receipt_sent:
        from services.asset_email_service import send_asset_delivery_receipt_email
        receipt_sent = send_asset_delivery_receipt_email(asset)
    return jsonify({
        "success": True,
        "message": "Terms accepted. " + ("The delivery receipt was emailed." if receipt_sent else "Acceptance was saved, but the receipt email could not be sent."),
        "accepted_at": asset.sale_terms_accepted_at.isoformat() if asset.sale_terms_accepted_at else None,
        "receipt_sent": receipt_sent,
    })


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
        "teacher_id": teaching_class.teacher_id,
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
        "product_code": product.product_code or "",
        "name": product.name,
        "description": product.description or "",
        "category": product.category or "",
        "brand": product.brand or "",
        "price": float(product.price or 0),
        "mrp": float(product.mrp) if product.mrp is not None else None,
        "warranty": product.warranty or "",
        "return_policy": product.return_policy or "",
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


def _admin_commerce_invoice_payload(item):
    return {
        "id": item.id,
        "invoice_number": item.invoice_number,
        "recipient_name": item.recipient_name,
        "recipient_email": item.recipient_email,
        "status": item.status,
        "invoice_type": item.invoice_type,
        "subtotal": float(item.subtotal or 0),
        "tax": float(item.tax or 0),
        "total_amount": float(item.total_amount or 0),
        "amount_paid": float(item.amount_paid or 0),
        "amount_refunded": float(item.amount_refunded or 0),
        "pending_amount": float(item.pending_amount or 0),
        "due_date": item.due_date.isoformat() if item.due_date else None,
        "notes": item.notes or "",
        "payment_details": item.payment_details or "",
        "bill_to_address": item.bill_to_address or "",
        "ship_to_address": item.ship_to_address or "",
        "order_id": item.order_id or "",
        "booking_details": item.booking_details or {},
        "items": [
            {"id": row.id, "description": row.description, "quantity": row.quantity,
             "price": float(row.price or 0)}
            for row in item.items
        ],
        "payments": [
            {"id": row.id, "amount": float(row.amount or 0), "note": row.note or "",
             "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None}
            for row in item.payments
        ],
        "refunds": [
            {"id": row.id, "amount": float(row.amount or 0), "refund_type": row.refund_type,
             "reason": row.reason or "", "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None}
            for row in item.refunds
        ],
        "created_at": item.created_at.isoformat() if item.created_at else None,
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
    card = GiftCard.query.filter_by(id=card_id, status=GiftCardStatus.AVAILABLE.value).with_for_update().first()
    if not card or card.is_expired:
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
                "subtotal": float(invoice.subtotal or 0),
                "tax": float(invoice.tax or 0),
                "total_amount": float(invoice.total_amount or 0),
                "amount_paid": float(invoice.amount_paid or 0),
                "pending_amount": invoice.pending_amount,
                "bill_to_address": invoice.bill_to_address or "",
                "ship_to_address": invoice.ship_to_address or "",
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
        recipient_user_id=invoice_recipient_id(recipient_email),
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


@mobile_api_bp.post("/seller/invoices/<int:invoice_id>/send")
@mobile_login_required
def seller_send_invoice(invoice_id):
    denied = _require_role("seller")
    if denied:
        return denied
    invoice = Invoice.query.filter_by(id=invoice_id, admin_id=current_user.id).first()
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    data = request.get_json(silent=True) or {}
    raw_recipients = data.get("recipient_emails")
    if raw_recipients is None:
        raw_recipients = [invoice.recipient_email]
    if isinstance(raw_recipients, str):
        raw_recipients = raw_recipients.split(",")
    if not isinstance(raw_recipients, list):
        return jsonify({"success": False, "message": "Recipient emails must be a list or comma-separated string."}), 400
    recipients = []
    seen = set()
    for value in raw_recipients:
        if not isinstance(value, str):
            continue
        email = value.strip()
        if not email:
            continue
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            return jsonify({"success": False, "message": f"Invalid email address: {email}"}), 400
        if email.lower() not in seen:
            recipients.append(email)
            seen.add(email.lower())
    if not recipients:
        return jsonify({"success": False, "message": "Add at least one recipient email."}), 400
    try:
        from invoice_service import InvoiceGenerator
        pdf = InvoiceGenerator(invoice).generate_pdf()
        send_email(
            to=recipients,
            subject=f"Resent: Invoice {invoice.invoice_number}",
            template="mail/ecommerce_invoice_email.html",
            invoice=invoice,
            attachments=[{"filename": f"{invoice.invoice_number}.pdf", "content_type": "application/pdf", "data": pdf}],
        )
    except Exception:
        current_app.logger.exception("Seller invoice resend failed")
        return jsonify({"success": False, "message": "Invoice email could not be queued."}), 500
    return jsonify({"success": True, "message": "Invoice resend queued successfully."})


@mobile_api_bp.post("/seller/invoices/<int:invoice_id>/remind")
@mobile_login_required
def seller_remind_invoice(invoice_id):
    denied = _require_role("seller")
    if denied:
        return denied
    invoice = Invoice.query.filter_by(id=invoice_id, admin_id=current_user.id).first()
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    if invoice.status == InvoiceStatus.PAID.value:
        return jsonify({"success": False, "message": "This invoice is already paid."}), 400
    if not invoice.recipient_email:
        return jsonify({"success": False, "message": "This invoice has no recipient email."}), 400
    created_at = invoice.created_at.strftime("%B %d, %Y") if invoice.created_at else "Unknown"
    due_date = invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Immediate"
    try:
        send_email(
            to=invoice.recipient_email,
            subject=f"Payment Reminder: Invoice {invoice.invoice_number}",
            template="mail/reminder_invoice_email.html",
            recipient_name=invoice.recipient_name,
            invoice_number=invoice.invoice_number,
            created_at=created_at,
            total_amount=invoice.total_amount,
            due_date=due_date,
            invoice=invoice,
            amount_paid=float(invoice.amount_paid or 0),
            pending_amount=invoice.pending_amount,
        )
    except Exception:
        current_app.logger.exception("Seller invoice reminder failed")
        return jsonify({"success": False, "message": "Payment reminder could not be queued."}), 500
    return jsonify({"success": True, "message": "Payment reminder queued."})


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


@mobile_api_bp.get("/seller/superscoins/invoices/<int:invoice_id>/download")
@mobile_login_required
def seller_download_superscoins_invoice(invoice_id):
    denied = _require_role("seller")
    if denied:
        return denied
    try:
        from services.superscoins_service import SupersCoinsService
        if not SupersCoinsService.tables_ready():
            return jsonify({"success": False, "message": "SupersCoins wallet setup is pending."}), 503
        invoice = SupersCoinInvoice.query.filter_by(id=invoice_id, seller_id=current_user.id).first()
        if not invoice:
            return jsonify({"success": False, "message": "Invoice not found."}), 404
        from invoice_service import SupersCoinInvoiceGenerator
        pdf_bytes = SupersCoinInvoiceGenerator(invoice).generate_pdf()
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{invoice.invoice_number}.pdf",
        )
    except Exception:
        current_app.logger.exception("Native seller SupersCoins invoice download failed")
        return jsonify({"success": False, "message": "Invoice PDF could not be generated."}), 500


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
        "token": link.token if link else "",
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
        "token": link.token,
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


@mobile_api_bp.get("/candidate/applications")
@mobile_login_required
def candidate_applications():
    denied = _require_role("candidate")
    if denied:
        return denied
    applications = JobApplication.query.filter_by(user_id=current_user.id).order_by(
        JobApplication.applied_at.desc()
    ).all()
    return jsonify({
        "success": True,
        "applications": [
            {
                "id": item.id,
                "job_id": item.job_id,
                "job_title": item.job.title if item.job else "Unavailable job",
                "job_open": bool(item.job and item.job.is_open),
                "status": item.status,
                "resume_url": item.resume_url or "",
                "applied_at": item.applied_at.isoformat() if item.applied_at else None,
            }
            for item in applications
        ],
    })


@mobile_api_bp.get("/candidate/snippet-recipients")
@mobile_login_required
def candidate_snippet_recipients():
    denied = _require_role("candidate")
    if denied:
        return denied
    recipients = User.query.filter(
        User.role.in_([UserRole.ADMIN.value, UserRole.DEVELOPER.value]),
        User.is_active.is_(True),
    ).order_by(User.username.asc()).all()
    return jsonify({
        "success": True,
        "recipients": [
            {"id": item.id, "username": item.username, "role": item.role}
            for item in recipients
        ],
    })


@mobile_api_bp.post("/candidate/snippets")
@mobile_login_required
def candidate_share_snippet():
    denied = _require_role("candidate")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    language = data.get("language", "java")
    try:
        recipient_id = int(data.get("recipient_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a SourcePoint recipient."}), 400
    if not isinstance(code, str) or not code.strip() or len(code) > 100_000:
        return jsonify({"success": False, "message": "Enter code (up to 100,000 characters)."}), 400
    if not isinstance(language, str) or not language.strip() or len(language.strip()) > 50:
        return jsonify({"success": False, "message": "Choose a valid programming language."}), 400
    recipient = User.query.filter(
        User.id == recipient_id,
        User.role.in_([UserRole.ADMIN.value, UserRole.DEVELOPER.value]),
        User.is_active.is_(True),
    ).first()
    if not recipient:
        return jsonify({"success": False, "message": "That recipient is not available."}), 404
    try:
        success, message = HiringService.share_code_snippet(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            code=code.strip(),
            language=language.strip(),
        )
        if success:
            log_user_action("Share Code", f"Shared a {language.strip()} code snippet from native app")
        return jsonify({"success": success, "message": message}), (201 if success else 400)
    except Exception:
        current_app.logger.exception("Candidate code snippet could not be shared")
        return jsonify({"success": False, "message": "Code could not be shared. Try again."}), 500


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


@mobile_api_bp.post("/candidate/code-test/run")
@mobile_login_required
def candidate_run_code_test():
    denied = _require_role("candidate")
    if denied:
        return denied
    if not current_user.assigned_problem:
        return jsonify({"success": False, "message": "No coding test has been assigned."}), 404
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    stdin = data.get("stdin", "")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"success": False, "message": "Enter code before running it."}), 400
    if len(code) > 50000 or not isinstance(stdin, str) or len(stdin) > 10000:
        return jsonify({"success": False, "message": "Code or input is too large."}), 413
    now = datetime.utcnow()
    if current_user.test_start_time and now < current_user.test_start_time:
        return jsonify({"success": False, "message": "The coding test is not available yet."}), 403
    if current_user.test_end_time and now > current_user.test_end_time:
        current_user.test_completed = True
        db.session.commit()
        return jsonify({"success": False, "message": "The coding test deadline has passed."}), 410
    client_id = os.environ.get("JDOODLE_CLIENT_ID")
    client_secret = os.environ.get("JDOODLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return jsonify({"success": False, "message": "Code execution is not configured on the server."}), 503
    try:
        response = requests.post(
            "https://api.jdoodle.com/v1/execute",
            json={
                "clientId": client_id,
                "clientSecret": client_secret,
                "script": code,
                "stdin": stdin,
                "language": "java",
                "versionIndex": "0",
            },
            headers={"Content-Type": "application/json"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException:
        current_app.logger.exception("Candidate code execution service failed")
        return jsonify({"success": False, "message": "Code execution service is temporarily unavailable."}), 502
    except ValueError:
        return jsonify({"success": False, "message": "Code execution returned an invalid response."}), 502
    return jsonify(result)


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


@mobile_api_bp.get("/learning/<language>/chat/history")
@mobile_login_required
def mobile_learning_chat_history(language):
    subject = str(language or "").strip().lower()
    if current_user.role not in LEARNING_ROLES:
        return jsonify({"success": False, "message": "Learning content is not available for this account type."}), 403
    if subject not in LEARNING_LANGUAGES:
        return jsonify({"success": False, "message": "Choose a supported learning topic."}), 404
    history = ChatHistory.query.filter_by(
        user_id=current_user.id,
        subject=subject,
    ).order_by(ChatHistory.timestamp.asc()).all()
    return jsonify({
        "success": True,
        "subject": subject,
        "history": [
            {
                "id": item.id,
                "role": item.role,
                "text": item.message,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            }
            for item in history
        ],
    })


@mobile_api_bp.post("/learning/chat")
@mobile_login_required
def mobile_ask_learning_ai():
    if current_user.role not in LEARNING_ROLES:
        return jsonify({"success": False, "message": "Learning content is not available for this account type."}), 403
    data = request.get_json(silent=True) or {}
    subject = str(data.get("subject", "")).strip().lower()
    question = str(data.get("question", "")).strip()
    if subject not in LEARNING_LANGUAGES:
        return jsonify({"success": False, "message": "Choose a supported learning topic."}), 400
    if not question:
        return jsonify({"success": False, "message": "Enter a question for the tutor."}), 400
    if len(question) > 4000:
        return jsonify({"success": False, "message": "Keep your question under 4,000 characters."}), 413
    api_key = current_app.config.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"success": False, "message": "The learning tutor is not configured on the server."}), 503

    try:
        db.session.add(ChatHistory(
            user_id=current_user.id,
            subject=subject,
            role="user",
            message=question,
        ))
        db.session.commit()
        from blueprints.main import background_ai_task
        Thread(
            target=background_ai_task,
            args=(current_app._get_current_object(), current_user.id, subject, question, api_key),
            daemon=True,
        ).start()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native learning tutor request could not be started")
        return jsonify({"success": False, "message": "The learning tutor could not start this request."}), 503

    return jsonify({
        "success": True,
        "status": "processing",
        "subject": subject,
        "message": "Your question was sent. The answer will appear in this conversation shortly.",
    }), 202


@mobile_api_bp.delete("/learning/chat/history")
@mobile_login_required
def mobile_delete_learning_chat_history():
    if current_user.role not in LEARNING_ROLES:
        return jsonify({"success": False, "message": "Learning content is not available for this account type."}), 403
    subject = str(request.args.get("subject", "")).strip().lower()
    if subject not in LEARNING_LANGUAGES:
        return jsonify({"success": False, "message": "Choose a supported learning topic."}), 400
    try:
        ChatHistory.query.filter_by(user_id=current_user.id, subject=subject).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native learning history could not be cleared")
        return jsonify({"success": False, "message": "Learning history could not be cleared."}), 500
    return jsonify({"success": True, "message": "Learning history cleared."})


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
        "teachers": ([{"id": user.id, "username": user.username, "email": user.email}
                      for user in User.query.filter_by(role=UserRole.TEACHER.value, is_active=True, is_approved=True).order_by(User.username).all()]
                     if role == UserRole.ADMIN.value else []),
    })


@mobile_api_bp.post("/teaching/classes")
@mobile_login_required
def teaching_create_class():
    if current_user.role not in {UserRole.TEACHER.value, UserRole.ADMIN.value}:
        return jsonify({"success": False, "message": "Only teachers and administrators can create classes."}), 403
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
        return jsonify({"success": False, "message": "Enter a class title of 1 to 140 characters."}), 400
    teacher_id = current_user.id
    if current_user.role == UserRole.ADMIN.value:
        try:
            teacher_id = int(data.get("teacher_id"))
        except (TypeError, ValueError):
            teacher_id = 0
        teacher = User.query.filter_by(id=teacher_id, role=UserRole.TEACHER.value, is_active=True, is_approved=True).first()
        if not teacher:
            return jsonify({"success": False, "message": "Select an active, approved teacher for this class."}), 400
    teaching_class = TeachingClass(
        teacher_id=teacher_id,
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


@mobile_api_bp.patch("/teaching/classes/<int:class_id>")
@mobile_login_required
def teaching_update_class(class_id):
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class or current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    data = request.get_json(silent=True) or {}
    title = data.get("title", teaching_class.title)
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
        return jsonify({"success": False, "message": "Enter a class name with 1 to 140 characters."}), 400
    teaching_class.title = title.strip()
    for field, limit in (("subject", 100), ("level", 80), ("description", 4000)):
        if field in data:
            value = data[field]
            if not isinstance(value, str):
                return jsonify({"success": False, "message": f"{field.title()} must be text."}), 400
            setattr(teaching_class, field, value.strip()[:limit] or None)
    teacher_reassigned = False
    if current_user.role == UserRole.ADMIN.value and data.get("teacher_id") not in (None, ""):
        try:
            teacher_id = int(data["teacher_id"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Choose a valid teacher."}), 400
        teacher = User.query.filter_by(id=teacher_id, role=UserRole.TEACHER.value,
                                       is_active=True, is_approved=True).first()
        if not teacher:
            return jsonify({"success": False, "message": "Choose an active, approved teacher."}), 400
        teacher_reassigned = teacher.id != teaching_class.teacher_id
        teaching_class.teacher_id = teacher.id
    db.session.commit()
    if teacher_reassigned:
        try:
            from blueprints.teaching import _notify_teaching_participants
            _notify_teaching_participants(teaching_class, subject=f"Class teacher updated: {teaching_class.title}",
                                          template="mail/teaching_class_created.html", actor=current_user,
                                          class_action="reassigned")
        except Exception:
            current_app.logger.exception("Class was reassigned but participant notifications failed")
    return jsonify({"success": True, "message": "Class details updated.",
                    "class": _teaching_class_payload(teaching_class, True)})


@mobile_api_bp.post("/teaching/classes/<int:class_id>/status")
@mobile_login_required
def teaching_update_class_status(class_id):
    teaching_class = _teaching_class_access(class_id)
    if not teaching_class or current_user.role not in {UserRole.ADMIN.value, UserRole.TEACHER.value}:
        return jsonify({"success": False, "message": "Class not found or you do not have access."}), 404
    action = (request.get_json(silent=True) or {}).get("action")
    if action == "archive":
        teaching_class.is_active = False
        message = "Class archived. Existing history remains available."
    elif action == "restore":
        teaching_class.is_active = True
        message = "Class reopened. Students can join and new class work can be added."
    else:
        return jsonify({"success": False, "message": "Choose archive or restore."}), 400
    db.session.commit()
    return jsonify({"success": True, "message": message,
                    "class": _teaching_class_payload(teaching_class, True)})


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
        "teachers": ([{"id": user.id, "username": user.username, "email": user.email}
                      for user in User.query.filter_by(role=UserRole.TEACHER.value, is_active=True, is_approved=True)
                      .order_by(User.username).all()] if current_user.role == UserRole.ADMIN.value else []),
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


@mobile_api_bp.get("/recruiter/candidates/<int:candidate_id>")
@mobile_login_required
def recruiter_candidate_profile(candidate_id):
    denied = _require_role("recruiter")
    if denied:
        return denied
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    if not candidate:
        return jsonify({"success": False, "message": "Candidate not found."}), 404
    applications = JobApplication.query.filter_by(user_id=candidate.id).order_by(
        JobApplication.applied_at.desc()
    ).all()
    return jsonify({
        "success": True,
        "candidate": {
            "id": candidate.id,
            "username": candidate.username,
            "email": candidate.email,
            "mobile_number": candidate.mobile_number or "",
            "primary_skill": candidate.primary_skill or "",
            "primary_skill_experience": candidate.primary_skill_experience or "",
            "secondary_skill": candidate.secondary_skill or "",
            "secondary_skill_experience": candidate.secondary_skill_experience or "",
            "resume_url": candidate.resume_filename or "",
            "test_completed": bool(candidate.test_completed),
            "has_assigned_test": bool(candidate.assigned_problem),
            "applications": [
                {
                    "id": item.id,
                    "job_title": item.job.title if item.job else "Unavailable job",
                    "status": item.status,
                    "applied_at": item.applied_at.isoformat() if item.applied_at else None,
                }
                for item in applications
            ],
        },
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
            "pending_orders": Order.query.filter(Order.status.in_(CommerceService.placed_status_values)).count(),
            "pending_stock_requests": StockRequest.query.filter_by(status="Pending").count(),
            "pending_applications": JobApplication.query.filter_by(status=ApplicationStatus.PENDING.value).count(),
            "interviews": Interview.query.count(),
            "assets": Asset.query.count(),
            "gift_cards": GiftCard.query.count(),
            "projects": Project.query.count(),
            "teaching_classes": TeachingClass.query.count(),
        },
        "pending_users": [
            {"id": user.id, "username": user.username, "email": user.email,
             "role": user.role, "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None}
            for user in pending_users
        ],
    })


@mobile_api_bp.get("/admin/users")
@mobile_login_required
def admin_users_directory():
    denied = _require_role("admin")
    if denied:
        return denied
    search = request.args.get("q", "", type=str).strip()[:120]
    role = request.args.get("role", "all", type=str).strip().lower()
    status = request.args.get("status", "all", type=str).strip().lower()
    page = max(request.args.get("page", 1, type=int), 1)
    query = User.query
    if search:
        query = query.filter(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if role != "all":
        if role not in {item.value for item in UserRole}:
            return jsonify({"success": False, "message": "Choose a valid account role."}), 400
        query = query.filter_by(role=role)
    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)
    elif status == "pending":
        query = query.filter_by(is_approved=False)
    elif status != "all":
        return jsonify({"success": False, "message": "Choose all, active, inactive, or pending."}), 400
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=30, error_out=False)
    return jsonify({
        "success": True,
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "is_approved": bool(user.is_approved),
                "mobile_number": user.mobile_number or "",
                "primary_skill": user.primary_skill or "",
                "primary_skill_experience": user.primary_skill_experience or "",
                "secondary_skill": user.secondary_skill or "",
                "secondary_skill_experience": user.secondary_skill_experience or "",
                "resume_filename": user.resume_filename or "",
                "avatar_url": user.avatar_url or "",
                "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
            }
            for user in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "roles": [item.value for item in UserRole],
        "search": search,
        "role_filter": role,
        "status_filter": status,
    })


@mobile_api_bp.post("/admin/users")
@mobile_login_required
def admin_create_user():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    role = str(data.get("role", "")).strip().lower()
    if not username or len(username) > 100 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"success": False, "message": "Enter a valid username and email address."}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters."}), 400
    if role not in {item.value for item in UserRole}:
        return jsonify({"success": False, "message": "Choose a valid account role."}), 400
    if User.query.filter(or_(User.username == username, User.email == email)).first():
        return jsonify({"success": False, "message": "That username or email is already in use."}), 409
    user = User(
        username=username,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
        avatar_url=f"https://api.dicebear.com/8.x/initials/svg?seed={username}",
        is_approved=True,
    )
    db.session.add(user)
    db.session.commit()
    log_user_action("Create User", f"Admin created {role} account {username} from native app")
    return jsonify({"success": True, "message": f"Account for {username} created.", "user": _user_payload(user)}), 201


@mobile_api_bp.patch("/admin/users/<int:user_id>")
@mobile_login_required
def admin_update_user(user_id):
    denied = _require_role("admin")
    if denied:
        return denied
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    data = request.get_json(silent=True) or {}
    editable = ("mobile_number", "primary_skill", "primary_skill_experience", "secondary_skill", "secondary_skill_experience")
    for field in editable:
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, str):
                return jsonify({"success": False, "message": f"Invalid value for {field}."}), 400
            setattr(user, field, value.strip() or None if isinstance(value, str) else value)
    db.session.commit()
    log_user_action("Update User Profile", f"Admin updated profile for {user.username} from native app")
    return jsonify({"success": True, "message": "User profile updated.", "user": _user_payload(user)})


@mobile_api_bp.post("/admin/users/<int:user_id>/password")
@mobile_login_required
def admin_set_user_password(user_id):
    denied = _require_role("admin")
    if denied:
        return denied
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    data = request.get_json(silent=True) or {}
    password = data.get("new_password")
    confirmation = data.get("confirm_password")
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters."}), 400
    if password != confirmation:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400
    user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    db.session.commit()
    log_user_action("Admin Change Password", f"Admin changed password for {user.username} from native app")
    return jsonify({"success": True, "message": f"Password updated for {user.username}."})


@mobile_api_bp.post("/admin/users/<int:user_id>/resume")
@mobile_login_required
def admin_upload_candidate_resume(user_id):
    denied = _require_role("admin")
    if denied:
        return denied
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    if user.role != UserRole.CANDIDATE.value:
        return jsonify({"success": False, "message": "A resume can only be uploaded to a candidate account."}), 400
    resume = request.files.get("resume")
    if not resume or not resume.filename or not secure_filename(resume.filename).lower().endswith(".pdf"):
        return jsonify({"success": False, "message": "Choose a PDF resume."}), 400
    content = resume.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        return jsonify({"success": False, "message": "Resume must be 10 MB or smaller."}), 413
    if not content.startswith(b"%PDF-"):
        return jsonify({"success": False, "message": "The selected file is not a valid PDF."}), 400
    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(BytesIO(content), resource_type="raw", folder="resumes",
                                           public_id=f"resume_{user.id}")
        user.resume_filename = result["secure_url"]
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native admin candidate resume upload failed")
        return jsonify({"success": False, "message": "Resume upload failed. Try again."}), 502
    log_user_action("Update User Profile", f"Admin uploaded resume for {user.username} from native app")
    return jsonify({"success": True, "message": f"Resume updated for {user.username}.", "resume_url": user.resume_filename})


@mobile_api_bp.post("/admin/users/<int:user_id>/status")
@mobile_login_required
def admin_toggle_user_status(user_id):
    denied = _require_role("admin")
    if denied:
        return denied
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    if user.id == current_user.id:
        return jsonify({"success": False, "message": "You cannot change your own account status."}), 409
    user.is_active = not user.is_active
    db.session.commit()
    state = "activated" if user.is_active else "deactivated"
    log_user_action("Toggle User Status", f"Admin {state} user {user.username} from native app")
    try:
        send_email(
            to=user.email,
            subject=f"SourcePoint: Your account has been {state}",
            template="mail/account_status_email.html",
            user=user,
            is_active=user.is_active,
            now=datetime.utcnow(),
            login_url=url_for("auth.login_register", _external=True),
        )
    except Exception:
        current_app.logger.exception("User status saved but notification email failed")
    return jsonify({"success": True, "message": f"User {user.username} {state}.", "is_active": user.is_active})


@mobile_api_bp.get("/admin/commerce")
@mobile_login_required
def admin_commerce_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    product_search = request.args.get("product_q", "").strip()[:150]
    product_page = max(1, request.args.get("product_page", 1, type=int))
    invoice_search = request.args.get("invoice_q", "").strip()[:150]
    invoice_status = request.args.get("invoice_status", "all").strip().lower()
    invoice_page = max(1, request.args.get("invoice_page", 1, type=int))
    invoice_status_values = {status.value.lower(): status.value for status in InvoiceStatus}
    if invoice_status not in {"all", "open"} and invoice_status not in invoice_status_values:
        return jsonify({"success": False, "message": "Choose a valid invoice status filter."}), 400
    product_query = Product.query
    if product_search:
        product_query = product_query.filter(or_(Product.name.ilike(f"%{product_search}%"),
            Product.product_code.ilike(f"%{product_search}%"), Product.category.ilike(f"%{product_search}%")))
    product_total = product_query.count()
    product_page_size = 50
    products = product_query.order_by(Product.name.asc()).offset((product_page - 1) * product_page_size).limit(product_page_size).all()
    orders = Order.query.options(joinedload(Order.items)).order_by(Order.created_at.desc()).limit(100).all()
    requests = StockRequest.query.order_by(StockRequest.request_date.desc()).limit(100).all()
    invoice_query = Invoice.query
    if invoice_search:
        pattern = f"%{invoice_search}%"
        invoice_query = invoice_query.filter(or_(
            Invoice.invoice_number.ilike(pattern),
            Invoice.recipient_name.ilike(pattern),
            Invoice.recipient_email.ilike(pattern),
            Invoice.invoice_type.ilike(pattern),
        ))
    if invoice_status == "open":
        invoice_query = invoice_query.filter(Invoice.status.in_([
            InvoiceStatus.UNPAID.value, InvoiceStatus.OVERDUE.value,
        ]))
    elif invoice_status != "all":
        invoice_query = invoice_query.filter(Invoice.status == invoice_status_values[invoice_status])
    invoice_total = invoice_query.count()
    invoice_page_size = 20
    invoices = invoice_query.options(
        selectinload(Invoice.items), selectinload(Invoice.payments), selectinload(Invoice.refunds),
    ).order_by(Invoice.created_at.desc(), Invoice.id.desc()).offset(
        (invoice_page - 1) * invoice_page_size
    ).limit(invoice_page_size).all()
    invoice_status_counts = dict(db.session.query(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status).all())
    ads = AffiliateAd.query.order_by(AffiliateAd.ad_name.asc()).all()
    sellers = User.query.filter_by(role=UserRole.SELLER.value, is_active=True).order_by(User.username.asc()).all()
    buyers = User.query.filter_by(role=UserRole.BUYER.value, is_active=True, is_approved=True).order_by(User.username.asc()).all()
    seller_stock = db.session.query(SellerInventory, Product, User).join(
        Product, SellerInventory.product_id == Product.id
    ).join(User, SellerInventory.seller_id == User.id).order_by(User.username, Product.name).limit(500).all()
    rollback_requests = InventoryRollbackRequest.query.order_by(InventoryRollbackRequest.request_date.desc()).limit(100).all()
    share_link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    return jsonify({
        "success": True,
        "counts": {
            "products": Product.query.count(),
            "orders": Order.query.count(),
            "pending_orders": Order.query.filter(Order.status.in_(CommerceService.placed_status_values)).count(),
            "pending_stock_requests": StockRequest.query.filter_by(status="Pending").count(),
            "invoices": Invoice.query.count(),
            "ads": len(ads),
        },
        "invoice_counts": {
            "all": sum(invoice_status_counts.values()),
            "open": invoice_status_counts.get(InvoiceStatus.UNPAID.value, 0) + invoice_status_counts.get(InvoiceStatus.OVERDUE.value, 0),
            "unpaid": invoice_status_counts.get(InvoiceStatus.UNPAID.value, 0),
            "overdue": invoice_status_counts.get(InvoiceStatus.OVERDUE.value, 0),
            "paid": invoice_status_counts.get(InvoiceStatus.PAID.value, 0),
            "cancelled": invoice_status_counts.get(InvoiceStatus.CANCELLED.value, 0),
            "refunded": invoice_status_counts.get(InvoiceStatus.REFUNDED.value, 0),
        },
        "invoice_pagination": {
            "page": invoice_page, "per_page": invoice_page_size, "total": invoice_total,
            "pages": max(1, (invoice_total + invoice_page_size - 1) // invoice_page_size),
            "query": invoice_search, "status": invoice_status,
        },
        "products": [_product_payload(product) for product in products],
        "product_search": product_search,
        "product_pagination": {"page": product_page, "per_page": product_page_size, "total": product_total,
                               "pages": max(1, (product_total + product_page_size - 1) // product_page_size)},
        "orders": [_order_payload(order) for order in orders],
        "stock_requests": [
            {"id": item.id, "seller_id": item.seller_id, "seller": item.seller.username if item.seller else "",
             "product_id": item.product_id, "product": item.product.name if item.product else "",
             "quantity": item.quantity, "status": item.status,
             "request_date": item.request_date.isoformat() if item.request_date else None}
            for item in requests
        ],
        "invoices": [_admin_commerce_invoice_payload(item) for item in invoices],
        "ads": [{"id": item.id, "name": item.ad_name, "url": item.affiliate_link or ""} for item in ads],
        "seller_inventory": [
            {"id": allocation.id, "seller_id": seller.id, "seller": seller.username,
             "product_id": product.id, "product": product.name, "stock": allocation.stock}
            for allocation, product, seller in seller_stock
        ],
        "rollback_requests": [
            {"id": item.id, "request_number": item.request_number, "seller": item.seller.username if item.seller else "",
             "product": item.product.name if item.product else "", "quantity": item.quantity, "reason": item.reason or "",
             "status": item.status, "admin_note": item.admin_note or "", "request_date": item.request_date.isoformat() if item.request_date else None}
            for item in rollback_requests
        ],
        "sellers": [{"id": item.id, "username": item.username, "email": item.email} for item in sellers],
        "buyers": [{"id": item.id, "username": item.username, "email": item.email} for item in buyers],
        "share_link": ({"url": url_for("public.shared_catalog", token=share_link.token, _external=True),
                        "token": share_link.token, "is_active": bool(share_link.is_active)} if share_link else None),
        "order_statuses": list(CommerceService.order_status_choices),
    })


@mobile_api_bp.post("/admin/commerce/share-link")
@mobile_login_required
def admin_create_commerce_share_link():
    denied = _require_role("admin")
    if denied:
        return denied
    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        link = ShareableLink(token=secrets.token_hex(16), seller_id=current_user.id, is_active=True)
        db.session.add(link)
        db.session.commit()
    return jsonify({"success": True, "url": url_for("public.shared_catalog", token=link.token, _external=True),
                    "token": link.token, "is_active": bool(link.is_active)})


@mobile_api_bp.post("/admin/commerce/share-link/toggle")
@mobile_login_required
def admin_toggle_commerce_share_link():
    denied = _require_role("admin")
    if denied:
        return denied
    link = ShareableLink.query.filter_by(seller_id=current_user.id).first()
    if not link:
        return jsonify({"success": False, "message": "Generate a catalog link first."}), 404
    link.is_active = not link.is_active
    db.session.commit()
    return jsonify({"success": True, "message": f"Catalog link {'activated' if link.is_active else 'disabled'}.",
                    "is_active": bool(link.is_active)})


@mobile_api_bp.post("/admin/commerce/products")
@mobile_login_required
def admin_create_product():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    product_code = str(data.get("product_code", "")).strip()
    name = data.get("name")
    description = data.get("description", "")
    category = data.get("category", "Other")
    brand = data.get("brand", "")
    try:
        price = float(data.get("price"))
        stock = int(data.get("stock", 0))
        mrp = float(data["mrp"]) if data.get("mrp") not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter valid price, stock, and MRP values."}), 400
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150 or not product_code or len(product_code) > 50 or price < 0 or stock < 0 or mrp is not None and mrp < 0:
        return jsonify({"success": False, "message": "Enter a product code, product name, and non-negative price and stock."}), 400
    if Product.query.filter_by(product_code=product_code).first():
        return jsonify({"success": False, "message": "That product code is already in use."}), 409
    if not all(isinstance(value, str) for value in (description, category, brand)):
        return jsonify({"success": False, "message": "Product text fields must be strings."}), 400
    image_urls = data.get("image_urls", [])
    if not isinstance(image_urls, list) or any(not isinstance(value, str) for value in image_urls):
        return jsonify({"success": False, "message": "Product image URLs must be a list of text values."}), 400
    image_urls = list(dict.fromkeys(value.strip()[:1000] for value in image_urls if value.strip()))[:10]
    primary_image = str(data.get("image_url", "")).strip()[:1000] or (image_urls[0] if image_urls else None)
    product = Product(
        product_code=product_code,
        name=name.strip(), description=description.strip(), category=category.strip()[:100] or "Other",
        brand=brand.strip()[:100], price=price, stock=stock, mrp=mrp,
        warranty=str(data.get("warranty", "")).strip()[:200] or None,
        return_policy=str(data.get("return_policy", "")).strip()[:200] or None,
        image_url=primary_image,
    )
    db.session.add(product)
    for image_url in image_urls:
        db.session.add(ProductImage(product=product, image_url=image_url))
    db.session.commit()
    log_user_action("Create Product", f"Created product {product.name} from native admin")
    return jsonify({"success": True, "message": "Product added to inventory.", "product": _product_payload(product)}), 201


@mobile_api_bp.patch("/admin/commerce/products/<int:product_id>")
@mobile_login_required
def admin_update_product(product_id):
    denied = _require_role("admin")
    if denied:
        return denied
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
            return jsonify({"success": False, "message": "Enter a product name up to 150 characters."}), 400
        product.name = name.strip()
    if "description" in data and isinstance(data["description"], str):
        product.description = data["description"].strip()
    if "category" in data and isinstance(data["category"], str):
        product.category = data["category"].strip()[:100]
    if "brand" in data and isinstance(data["brand"], str):
        product.brand = data["brand"].strip()[:100]
    if "warranty" in data and isinstance(data["warranty"], str):
        product.warranty = data["warranty"].strip()[:200] or None
    if "return_policy" in data and isinstance(data["return_policy"], str):
        product.return_policy = data["return_policy"].strip()[:200] or None
    if "image_urls" in data:
        image_urls = data["image_urls"]
        if not isinstance(image_urls, list) or any(not isinstance(value, str) for value in image_urls):
            return jsonify({"success": False, "message": "Product image URLs must be a list of text values."}), 400
        image_urls = list(dict.fromkeys(value.strip()[:1000] for value in image_urls if value.strip()))[:10]
        product.image_url = image_urls[0] if image_urls else None
        ProductImage.query.filter_by(product_id=product.id).delete()
        for image_url in image_urls:
            db.session.add(ProductImage(product_id=product.id, image_url=image_url))
    for field, converter in (("price", float), ("mrp", float), ("stock", int)):
        if field in data:
            try:
                value = None if field == "mrp" and data[field] in (None, "") else converter(data[field])
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": f"Enter a valid {field}."}), 400
            if value is not None and value < 0:
                return jsonify({"success": False, "message": f"{field.title()} cannot be negative."}), 400
            setattr(product, field, value)
    db.session.commit()
    log_user_action("Update Product", f"Updated product {product.name} from native admin")
    return jsonify({"success": True, "message": "Product updated.", "product": _product_payload(product)})


@mobile_api_bp.delete("/admin/commerce/products/<int:product_id>")
@mobile_login_required
def admin_delete_product(product_id):
    denied = _require_role("admin")
    if denied:
        return denied
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404
    name = product.name
    try:
        db.session.delete(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Product is referenced by existing commerce records and could not be deleted."}), 409
    log_user_action("Delete Product", f"Deleted product {name} from native admin")
    return jsonify({"success": True, "message": f"{name} deleted."})


@mobile_api_bp.patch("/admin/commerce/orders/<int:order_id>")
@mobile_login_required
def admin_update_order(order_id):
    denied = _require_role("admin")
    if denied:
        return denied
    order = Order.query.options(joinedload(Order.items)).get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    success, message, restored_items, missing_items = CommerceService.transition_order_status(order, new_status)
    if not success:
        db.session.rollback()
        return jsonify({"success": False, "message": message}), 400
    db.session.commit()
    normalized_status = CommerceService.normalize_order_status(new_status)
    if order.buyer and order.buyer.email:
        try:
            send_email(
                to=order.buyer.email,
                subject=f"Order Update: {order.status}",
                template="mail/order_status_update.html",
                buyer_name=order.buyer.username,
                order_number=order.order_number,
                status=order.status,
                order_date=order.created_at.strftime("%Y-%m-%d") if order.created_at else "",
                total_amount=order.total_amount,
                shipping_address=order.shipping_address,
                now=datetime.utcnow(),
            )
        except Exception:
            current_app.logger.exception("Order status saved but buyer notification failed")
    log_user_action("Update Order Status", f"Admin set order {order.order_number} to {normalized_status} from native app")
    if missing_items:
        message += f" Inventory could not be restored for: {', '.join(missing_items)}."
    return jsonify({"success": True, "message": message, "order": _order_payload(order)})


@mobile_api_bp.post("/admin/commerce/orders")
@mobile_login_required
def admin_create_order():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        buyer_id = int(data.get("buyer_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose an approved buyer account."}), 400
    buyer = User.query.filter_by(id=buyer_id, role=UserRole.BUYER.value, is_approved=True, is_active=True).first()
    shipping = str(data.get("shipping_address", "")).strip()
    items = data.get("items")
    if not buyer or not shipping or not isinstance(items, list) or not items:
        return jsonify({"success": False, "message": "Buyer, shipping address, and at least one product are required."}), 400
    resolved, total = [], 0.0
    try:
        for entry in items:
            product = Product.query.get(int(entry.get("product_id")))
            quantity = int(entry.get("quantity"))
            if not product or quantity < 1:
                raise ValueError
            if product.stock < quantity:
                return jsonify({"success": False, "message": f"Only {product.stock} units of {product.name} are available."}), 409
            resolved.append((product, quantity))
            total += float(product.price or 0) * quantity
    except (TypeError, ValueError, AttributeError):
        return jsonify({"success": False, "message": "Choose valid products and positive quantities."}), 400
    now = datetime.utcnow()
    order_number = f"ORD-ADMIN-{now.strftime('%Y%m%d%H%M%S%f')}-{buyer.id}"
    order = Order(order_number=order_number, user_id=buyer.id, total_amount=total, shipping_address=shipping,
                  billing_address=str(data.get("billing_address", "")).strip() or shipping, status=OrderStatus.PLACED.value)
    for product, quantity in resolved:
        product.stock -= quantity
        order.items.append(OrderItem(product_name=product.name, quantity=quantity, price_at_purchase=product.price))
    db.session.add(order)
    db.session.commit()
    try:
        send_email(to=buyer.email, subject=f"Order Confirmation: {order.order_number}", template="mail/order_status_update.html",
                   buyer_name=buyer.username, order_number=order.order_number, status=OrderStatus.PLACED.value,
                   order_date=now.strftime("%B %d, %Y"), total_amount=order.total_amount, shipping_address=shipping, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Admin order saved but buyer email failed")
    log_user_action("Admin Create Order", f"Created order {order.order_number} from native admin")
    return jsonify({"success": True, "message": "Order created and inventory reserved.", "order": _order_payload(order)}), 201


@mobile_api_bp.post("/admin/commerce/stock-requests/<int:request_id>/decision")
@mobile_login_required
def admin_stock_request_decision(request_id):
    denied = _require_role("admin")
    if denied:
        return denied
    stock_request = StockRequest.query.get(request_id)
    if not stock_request or stock_request.status != "Pending":
        return jsonify({"success": False, "message": "Pending stock request not found."}), 404
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in {"approve", "reject"}:
        return jsonify({"success": False, "message": "Choose approve or reject."}), 400
    if decision == "approve":
        if stock_request.product.stock < stock_request.quantity:
            return jsonify({"success": False, "message": f"Insufficient master stock. Available: {stock_request.product.stock}."}), 409
        stock_request.product.stock -= stock_request.quantity
        seller_inventory = SellerInventory.query.filter_by(
            seller_id=stock_request.seller_id, product_id=stock_request.product_id
        ).first()
        if seller_inventory:
            seller_inventory.stock += stock_request.quantity
        else:
            db.session.add(SellerInventory(seller_id=stock_request.seller_id, product_id=stock_request.product_id, stock=stock_request.quantity))
        stock_request.status = "Approved"
    else:
        stock_request.status = "Rejected"
    stock_request.response_date = datetime.utcnow()
    db.session.commit()
    try:
        send_email(
            to=stock_request.seller.email,
            subject=f"Stock Request {stock_request.status}: {stock_request.product.name}",
            template="mail/request_status_update.html",
            request=stock_request,
            product=stock_request.product,
            status=stock_request.status,
        )
    except Exception:
        current_app.logger.exception("Stock request decision saved but seller notification failed")
    log_user_action(f"{stock_request.status} Stock Request", f"Processed stock request {stock_request.id} from native admin")
    return jsonify({"success": True, "message": f"Stock request {stock_request.status.lower()}.", "status": stock_request.status})


@mobile_api_bp.post("/admin/commerce/assignments")
@mobile_login_required
def admin_assign_inventory():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get("product_id"))
        seller_id = int(data.get("seller_id"))
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Select a product, seller, and quantity."}), 400
    product = Product.query.get(product_id)
    seller = User.query.filter_by(id=seller_id, role=UserRole.SELLER.value).first()
    if not product or not seller or quantity < 1:
        return jsonify({"success": False, "message": "Product, seller, or quantity is invalid."}), 400
    if product.stock < quantity:
        return jsonify({"success": False, "message": f"Only {product.stock} units remain in master stock."}), 409
    product.stock -= quantity
    allocation = SellerInventory.query.filter_by(seller_id=seller.id, product_id=product.id).first()
    if allocation:
        allocation.stock += quantity
    else:
        allocation = SellerInventory(seller_id=seller.id, product_id=product.id, stock=quantity)
        db.session.add(allocation)
    db.session.commit()
    try:
        send_email(
            to=seller.email,
            subject=f"Inventory Assigned: {product.name}",
            template="mail/inventory_assigned.html",
            user=seller,
            item=product,
            quantity=quantity,
            current_stock=allocation.stock,
            now=datetime.utcnow(),
        )
    except Exception:
        current_app.logger.exception("Inventory assigned but seller notification failed")
    log_user_action("Assign Inventory", f"Assigned {quantity} of {product.name} to seller {seller.username} from native admin")
    return jsonify({"success": True, "message": f"Assigned {quantity} units of {product.name} to {seller.username}."}), 201


@mobile_api_bp.post("/admin/commerce/bulk-assignments")
@mobile_login_required
def admin_bulk_assign_inventory():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        seller_id = int(data.get("seller_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a seller."}), 400
    seller = User.query.filter_by(id=seller_id, role=UserRole.SELLER.value).first()
    items = data.get("items")
    if not seller or not isinstance(items, list) or not items or len(items) > 200:
        return jsonify({"success": False, "message": "Choose a seller and one or more products to assign."}), 400
    assigned, errors = [], []
    for row in items:
        try:
            product_id, quantity = int(row.get("product_id")), int(row.get("quantity"))
        except (TypeError, ValueError, AttributeError):
            errors.append("A product row had invalid values.")
            continue
        product = Product.query.get(product_id)
        if quantity < 1 or not product or product.stock < quantity:
            errors.append(f"Product #{product_id}: invalid quantity, missing product, or insufficient master stock.")
            continue
        product.stock -= quantity
        allocation = SellerInventory.query.filter_by(seller_id=seller.id, product_id=product.id).first()
        if allocation:
            allocation.stock += quantity
        else:
            allocation = SellerInventory(seller_id=seller.id, product_id=product.id, stock=quantity)
            db.session.add(allocation)
        assigned.append({"product": product, "quantity": quantity, "current_stock": allocation.stock})
    if not assigned:
        db.session.rollback()
        return jsonify({"success": False, "message": "No inventory was assigned.", "errors": errors}), 400
    db.session.commit()
    try:
        send_email(to=seller.email, subject=f"Bulk Inventory Assigned: {len(assigned)} Product(s)",
                   template="mail/bulk_inventory_assigned.html", user=seller, assigned_items=assigned,
                   total_items=len(assigned), now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Bulk inventory assigned but seller notification failed")
    log_user_action("Bulk Assign Inventory", f"Assigned {len(assigned)} products to {seller.username} from native admin")
    message = f"Assigned {len(assigned)} product(s) to {seller.username}."
    if errors:
        message += f" {len(errors)} row(s) skipped."
    return jsonify({"success": True, "message": message, "errors": errors})


@mobile_api_bp.post("/admin/commerce/inventory/import")
@mobile_login_required
def admin_import_inventory_csv():
    denied = _require_role("admin")
    if denied:
        return denied
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"success": False, "message": "Choose a CSV or XLSX with product_code, name, stock, price, and optional category columns."}), 400
    filename = secure_filename(upload.filename).lower()
    if not filename.endswith((".csv", ".xlsx")):
        return jsonify({"success": False, "message": "Choose a CSV or XLSX inventory file."}), 400
    try:
        source = upload.stream.read(5_000_001)
        if len(source) > 5_000_000:
            return jsonify({"success": False, "message": "Inventory file must be no larger than 5 MB."}), 413
        if filename.endswith(".csv"):
            text = source.decode("utf-8-sig")
            reader = csv.DictReader(text.splitlines())
            raw_headers = reader.fieldnames or []
            normalized_headers = {key.strip().lower(): key for key in raw_headers}
            rows = ({key: row.get(original) for key, original in normalized_headers.items()} for row in reader)
        else:
            import openpyxl
            workbook = openpyxl.load_workbook(BytesIO(source), read_only=True, data_only=True)
            sheet = workbook.active
            rows_iter = sheet.iter_rows(values_only=True)
            raw_headers = [str(value or "").strip() for value in next(rows_iter, ())]
            header_indexes = {key.strip().lower(): index for index, key in enumerate(raw_headers) if key.strip()}
            normalized_headers = {key: key for key in header_indexes}
            def excel_rows():
                for row in rows_iter:
                    yield {header: row[index] if index < len(row) else None for header, index in header_indexes.items()}
            rows = excel_rows()
        required = {"product_code", "name", "stock", "price"}
        if not raw_headers or not required.issubset(normalized_headers):
            return jsonify({"success": False, "message": "Inventory file header must include product_code, name, stock, and price."}), 400
        added, skipped = 0, 0
        seen = set()
        for row_number, row in enumerate(rows, 2):
            if row_number > 1002:
                raise ValueError("Inventory import is limited to 1,000 data rows.")
            value = lambda name: str(row.get(name) or "").strip()
            code, name = value("product_code"), value("name")
            if not code or not name:
                raise ValueError(f"Row {row_number}: product_code and name are required.")
            if code in seen or Product.query.filter_by(product_code=code).first():
                skipped += 1
                continue
            try:
                stock_number, price = float(value("stock") or "0"), float(value("price") or "0")
                if not stock_number.is_integer():
                    raise ValueError
                stock = int(stock_number)
            except ValueError:
                raise ValueError(f"Row {row_number}: stock and price must be numbers.")
            if stock < 0 or price < 0:
                raise ValueError(f"Row {row_number}: stock and price cannot be negative.")
            category = value("category") if "category" in normalized_headers else "General"
            db.session.add(Product(product_code=code[:50], name=name[:150], stock=stock, price=price,
                                   category=category[:50] or "General", seller_id=None))
            db.session.flush()
            seen.add(code)
            added += 1
        db.session.commit()
    except (UnicodeDecodeError, csv.Error, ValueError, StopIteration) as error:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Inventory import failed: {error}"}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native admin inventory CSV import failed")
        return jsonify({"success": False, "message": "Inventory CSV could not be imported."}), 500
    log_user_action("Import Inventory", f"Imported {added} products from native admin; skipped {skipped} duplicate codes")
    return jsonify({"success": True, "message": f"Imported {added} products; skipped {skipped} existing product code(s).", "added": added, "skipped": skipped}), 201


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


# Admin workspace APIs keep the native app on the same records and workflows as the website.
@mobile_api_bp.get("/admin/hiring")
@mobile_login_required
def admin_hiring_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).limit(250).all()
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value, is_approved=True).order_by(User.username).all()
    developers = User.query.filter_by(role=UserRole.DEVELOPER.value, is_approved=True, is_active=True).order_by(User.username).all()
    moderators = User.query.filter_by(role=UserRole.MODERATOR.value, is_approved=True).order_by(User.username).all()
    reviewers = User.query.filter(
        User.role.in_([UserRole.MODERATOR.value, UserRole.DEVELOPER.value]),
        User.is_approved.is_(True),
    ).order_by(User.username).all()
    scheduled_candidates = User.query.filter(
        User.role == UserRole.CANDIDATE.value,
        User.problem_statement_id.isnot(None),
        User.moderator_id.is_(None),
        User.test_start_time.isnot(None),
        User.test_end_time.isnot(None),
    ).order_by(User.test_start_time.asc()).all()
    interviews = Interview.query.order_by(Interview.scheduled_time.desc()).limit(200).all()
    questions = MCQQuestion.query.order_by(MCQQuestion.created_at.desc()).all()
    tests = Test.query.order_by(Test.created_at.desc()).all()
    assignments = TestAssignment.query.order_by(TestAssignment.scheduled_start_time.desc()).all()
    submissions = CodeTestSubmission.query.order_by(CodeTestSubmission.submitted_at.desc()).limit(100).all()
    code_feedback = []
    interview_feedback = []
    assignment_history = []
    try:
        from models.hiring import Feedback
        code_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(100).all()
        interview_feedback = InterviewFeedback.query.order_by(InterviewFeedback.created_at.desc()).limit(100).all()
        assignment_history = ModeratorAssignmentHistory.query.order_by(ModeratorAssignmentHistory.assigned_at.desc()).limit(100).all()
    except Exception:
        current_app.logger.exception("Admin feedback records could not be loaded")
    return jsonify({
        "success": True,
        "jobs": [{"id": j.id, "title": j.title, "description": j.description, "is_open": j.is_open,
                  "created_at": j.created_at.isoformat() if j.created_at else None, "application_count": len(j.applications)} for j in jobs],
        "applications": [{"id": a.id, "job_id": a.job_id, "job_title": a.job.title if a.job else "",
                           "candidate_id": a.user_id, "candidate": a.candidate.username if a.candidate else "",
                           "linked_developer_ids": [developer.id for developer in a.candidate.allowed_contacts] if a.candidate else [],
                           "email": a.candidate.email if a.candidate else "", "status": a.status,
                           "applied_at": a.applied_at.isoformat() if a.applied_at else None, "resume_url": a.resume_url or ""} for a in applications],
        "candidates": [{"id": u.id, "username": u.username, "email": u.email,
                        "linked_developer_ids": [developer.id for developer in u.allowed_contacts]} for u in candidates],
        "developers": [{"id": u.id, "username": u.username, "email": u.email} for u in developers],
        "moderators": [{"id": u.id, "username": u.username, "email": u.email} for u in moderators],
        "reviewers": [{"id": u.id, "username": u.username, "email": u.email, "role": u.role} for u in reviewers],
        "scheduled_candidates": [{
            "id": u.id, "username": u.username, "email": u.email,
            "problem": u.assigned_problem.title if u.assigned_problem else "",
            "start_time": u.test_start_time.isoformat() if u.test_start_time else None,
            "end_time": u.test_end_time.isoformat() if u.test_end_time else None,
            "meeting_link": u.meeting_link or "",
        } for u in scheduled_candidates],
        "interviews": [{"id": i.id, "title": i.title, "description": i.description or "", "candidate_id": i.candidate_id,
                        "candidate": i.candidate.username if i.candidate else "", "scheduled_time": i.scheduled_time.isoformat() if i.scheduled_time else None,
                        "duration_minutes": i.duration_minutes, "meeting_url": i.google_meet_link or "", "status": i.status,
                        "moderators": [p.user.username for p in i.participants if p.user]} for i in interviews],
        "questions": [{"id": q.id, "text": q.question_text, "option_a": q.option_a, "option_b": q.option_b,
                       "option_c": q.option_c, "option_d": q.option_d, "correct_option": q.correct_option,
                       "category": q.category or ""} for q in questions],
        "tests": [{"id": t.id, "title": t.title, "description": t.description or "", "duration_minutes": t.duration_minutes,
                   "question_count": len(t.questions), "question_ids": [q.id for q in t.questions]} for t in tests],
        "assignments": [{"id": a.id, "test_id": a.test_id, "test": a.test.title if a.test else "",
                         "candidate": a.candidate.username if a.candidate else "", "reviewer": a.reviewer.username if a.reviewer else "",
                         "scheduled_start_time": a.scheduled_start_time.isoformat() if a.scheduled_start_time else None,
                         "status": a.status, "score": a.result.score if a.result else None,
                         "total_questions": a.result.total_questions if a.result else None} for a in assignments],
        "submissions": [{"id": s.id, "candidate": s.candidate.username if s.candidate else "", "recipient": s.recipient.username if s.recipient else "",
                         "language": s.language, "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                         "code": s.code, "output": s.output or "", "feedback": s.ai_feedback or ""} for s in submissions],
        "code_feedback": [{"id": f.id, "candidate": f.candidate.username if f.candidate else "", "moderator": f.moderator.username if f.moderator else "",
                           "rating": f.rating, "remarks": f.remarks or "", "created_at": f.created_at.isoformat() if f.created_at else None} for f in code_feedback],
        "interview_feedback": [{"id": f.id, "candidate": f.candidate.username if f.candidate else "", "moderator": f.moderator.username if f.moderator else "",
                                "recommendation": f.recommendation, "rating": f.rating, "remarks": f.remarks or "",
                                "created_at": f.created_at.isoformat() if f.created_at else None} for f in interview_feedback],
        "assignment_history": [{"id": h.id, "candidate": h.candidate.username if h.candidate else "",
                                "moderator": h.moderator.username if h.moderator else "",
                                "problem": h.problem.title if h.problem else "",
                                "assigned_at": h.assigned_at.isoformat() if h.assigned_at else None} for h in assignment_history],
    })


@mobile_api_bp.post("/admin/hiring/candidate-contacts")
@mobile_login_required
def admin_link_candidate_developer():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        candidate_id = int(data.get("candidate_id"))
        developer_id = int(data.get("developer_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a candidate and developer."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    developer = User.query.filter_by(id=developer_id, role=UserRole.DEVELOPER.value,
                                     is_active=True, is_approved=True).first()
    if not candidate or not developer:
        return jsonify({"success": False, "message": "Candidate or active developer was not found."}), 404
    if not candidate.allowed_contacts.filter(User.id == developer.id).first():
        candidate.allowed_contacts.append(developer)
        db.session.commit()
        log_user_action("Link Contacts", f"Linked developer {developer.username} to {candidate.username} from native admin")
    return jsonify({"success": True, "message": f"{developer.username} is now an allowed contact for {candidate.username}."})


@mobile_api_bp.post("/admin/hiring/quick-assign")
@mobile_login_required
def admin_hiring_quick_assign_test():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    try:
        candidate_id = int(data.get("candidate_id"))
        reviewer_id = int(data.get("reviewer_id"))
        question_limit = int(data.get("question_count", 40))
        duration = int(data.get("duration_minutes", 60))
        scheduled_value = str(data.get("scheduled_start_time", "")).strip()
        scheduled = datetime.fromisoformat(scheduled_value.replace("Z", "+00:00"))
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        scheduled_utc = scheduled.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a category, candidate, reviewer and valid schedule."}), 400
    if not category or question_limit < 10 or question_limit > 100 or duration < 1 or duration > 480:
        return jsonify({"success": False, "message": "Use a category, 10–100 questions and a duration from 1–480 minutes."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value, is_approved=True).first()
    reviewer = User.query.filter(
        User.id == reviewer_id,
        User.role.in_([UserRole.MODERATOR.value, UserRole.DEVELOPER.value]),
        User.is_approved.is_(True),
    ).first()
    if not candidate or not reviewer:
        return jsonify({"success": False, "message": "The selected candidate or reviewer is unavailable."}), 400

    per_option, remainder = divmod(question_limit, 4)
    selected = []
    for index, option in enumerate(("A", "B", "C", "D")):
        amount = per_option + (1 if index < remainder else 0)
        if amount:
            selected.extend(MCQQuestion.query.filter_by(category=category, correct_option=option).order_by(func.random()).limit(amount).all())
    if len(selected) < question_limit:
        selected_ids = [question.id for question in selected]
        fallback_query = MCQQuestion.query.filter(MCQQuestion.category == category)
        if selected_ids:
            fallback_query = fallback_query.filter(~MCQQuestion.id.in_(selected_ids))
        fallback = fallback_query.order_by(func.random()).limit(question_limit - len(selected)).all()
        selected.extend(fallback)
    if len(selected) < 10:
        return jsonify({"success": False, "message": f'Category "{category}" needs at least 10 questions; found {len(selected)}.'}), 400

    import random
    random.shuffle(selected)
    test_title = f"{category} Assessment - {candidate.username}"[:200]
    test = Test(title=test_title, description=f"Auto-generated {category} assessment for {candidate.username}.",
                duration_minutes=duration, created_by_id=current_user.id, questions=selected)
    assignment = TestAssignment(test=test, candidate=candidate, reviewer=reviewer,
                                scheduled_start_time=scheduled_utc, status="pending")
    db.session.add_all([test, assignment])
    db.session.commit()

    scheduled_ist = scheduled_utc + timedelta(hours=5, minutes=30)
    scheduled_display = scheduled_ist.strftime("%d %b %Y, %I:%M %p") + " IST"
    try:
        send_email(to=candidate.email, subject=f"MCQ Test Assigned: {test.title}", template="mail/mcq_test_assigned.html",
                   candidate=candidate, test=test, reviewer=reviewer, scheduled_time=scheduled_display)
        send_email(to=reviewer.email, subject=f"New MCQ Test Review Assignment: {candidate.username} - {test.title}",
                   template="mail/mcq_test_assigned_reviewer.html", candidate=candidate, test=test,
                   reviewer=reviewer, scheduled_time=scheduled_display)
    except Exception:
        current_app.logger.exception("Quick MCQ assignment was saved, but notifications could not be sent")
    log_user_action("Quick Assign Test", f"Created {test.title} and assigned it from native admin")
    return jsonify({"success": True, "message": f'Created and assigned "{test.title}".', "assignment_id": assignment.id}), 201


@mobile_api_bp.get("/admin/hiring/assignments/<int:assignment_id>")
@mobile_login_required
def admin_hiring_assignment_detail(assignment_id):
    denied = _require_role("admin")
    if denied:
        return denied
    assignment = TestAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assessment assignment not found."}), 404
    result = assignment.result
    answers = result.get_answers() if result else {}
    questions = []
    for question in assignment.test.questions:
        answer = str(answers.get(str(question.id), "Not answered"))
        questions.append({
            "id": question.id, "text": question.question_text,
            "option_a": question.option_a, "option_b": question.option_b,
            "option_c": question.option_c, "option_d": question.option_d,
            "candidate_answer": answer, "correct_answer": question.correct_option,
            "is_correct": answer == question.correct_option,
        })
    return jsonify({"success": True, "assignment": {
        "id": assignment.id, "test": assignment.test.title if assignment.test else "",
        "candidate": assignment.candidate.username if assignment.candidate else "",
        "reviewer": assignment.reviewer.username if assignment.reviewer else "",
        "status": assignment.status,
        "scheduled_start_time": assignment.scheduled_start_time.isoformat() if assignment.scheduled_start_time else None,
        "started_at": assignment.started_at.isoformat() if assignment.started_at else None,
        "submitted_at": result.submitted_at.isoformat() if result and result.submitted_at else None,
        "score": result.score if result else None,
        "total_questions": result.total_questions if result else len(questions),
        "percentage": result.percentage if result else None,
        "time_taken_minutes": result.time_taken_minutes if result else None,
    }, "questions": questions})


@mobile_api_bp.post("/admin/hiring/assignments/<int:assignment_id>/cancel")
@mobile_login_required
def admin_hiring_cancel_assignment(assignment_id):
    denied = _require_role("admin")
    if denied:
        return denied
    assignment = TestAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assessment assignment not found."}), 404
    if assignment.status == "completed" or assignment.result is not None:
        return jsonify({"success": False, "message": "Completed assessment assignments cannot be cancelled."}), 409
    assignment.status = "expired"
    db.session.commit()
    log_user_action("Cancel Test Assignment", f"Cancelled assessment assignment {assignment_id} from native admin")
    return jsonify({"success": True, "message": "Assessment assignment cancelled."})


@mobile_api_bp.post("/admin/hiring/scheduled-candidates/<int:candidate_id>/moderator")
@mobile_login_required
def admin_hiring_assign_scheduled_moderator(candidate_id):
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        moderator_id = int(data.get("moderator_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a moderator."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    moderator = User.query.filter_by(id=moderator_id, role=UserRole.MODERATOR.value, is_approved=True).first()
    if not candidate or not moderator:
        return jsonify({"success": False, "message": "The candidate or moderator was not found."}), 404
    if not candidate.assigned_problem or not candidate.test_start_time or not candidate.test_end_time:
        return jsonify({"success": False, "message": "This candidate does not have a complete coding test schedule."}), 409
    if candidate.moderator_id:
        return jsonify({"success": False, "message": "A moderator is already assigned to this candidate."}), 409
    candidate.moderator_id = moderator.id
    history = ModeratorAssignmentHistory(candidate_id=candidate.id, moderator_id=moderator.id,
                                         problem_statement_id=candidate.problem_statement_id)
    db.session.add(history)
    db.session.commit()
    ist_offset = timedelta(hours=5, minutes=30)
    try:
        send_email(to=moderator.email, cc=[candidate.email], subject=f"Moderator Assignment for {candidate.username}'s Test",
                   template="mail/moderator_assigned.html", moderator=moderator, candidate=candidate,
                   problem_title=candidate.assigned_problem.title, start_time_ist=candidate.test_start_time + ist_offset,
                   end_time_ist=candidate.test_end_time + ist_offset, meeting_link=candidate.meeting_link,
                   now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Moderator assignment saved, but the notification could not be sent")
    log_user_action("Assign Moderator", f"Assigned moderator {moderator.username} to {candidate.username} from native admin")
    return jsonify({"success": True, "message": "Moderator assigned and the notification was queued."})


@mobile_api_bp.delete("/admin/hiring/records/<record_type>/<int:record_id>")
@mobile_login_required
def admin_delete_hiring_record(record_type, record_id):
    denied = _require_role("admin")
    if denied:
        return denied
    from models.hiring import Feedback
    model = {"submission": CodeTestSubmission, "code-feedback": Feedback,
             "interview-feedback": InterviewFeedback, "assignment-history": ModeratorAssignmentHistory}.get(record_type)
    record = model.query.get(record_id) if model else None
    if not record:
        return jsonify({"success": False, "message": "Hiring record not found."}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"success": True, "message": "Hiring record deleted."})


@mobile_api_bp.post("/admin/hiring/jobs")
@mobile_login_required
def admin_hiring_create_job():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title, description = data.get("title"), data.get("description")
    if not isinstance(title, str) or not title.strip() or not isinstance(description, str) or not description.strip():
        return jsonify({"success": False, "message": "Job title and description are required."}), 400
    job = JobOpening(title=title.strip()[:150], description=description.strip(), is_open=True)
    db.session.add(job)
    db.session.commit()
    log_user_action("Post Job", f"Posted job {job.title} from native admin")
    return jsonify({"success": True, "message": "Job listing created.", "id": job.id}), 201


@mobile_api_bp.patch("/admin/hiring/jobs/<int:job_id>")
@mobile_login_required
def admin_hiring_update_job(job_id):
    denied = _require_role("admin")
    if denied:
        return denied
    job = JobOpening.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job listing not found."}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return jsonify({"success": False, "message": "Job title cannot be empty."}), 400
        job.title = data["title"].strip()[:150]
    if "description" in data:
        if not isinstance(data["description"], str) or not data["description"].strip():
            return jsonify({"success": False, "message": "Job description cannot be empty."}), 400
        job.description = data["description"].strip()
    if "is_open" in data:
        job.is_open = bool(data["is_open"])
    db.session.commit()
    log_user_action("Edit Job", f"Updated job {job.title} from native admin")
    return jsonify({"success": True, "message": "Job listing updated."})


@mobile_api_bp.delete("/admin/hiring/jobs/<int:job_id>")
@mobile_login_required
def admin_hiring_delete_job(job_id):
    denied = _require_role("admin")
    if denied:
        return denied
    job = JobOpening.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job listing not found."}), 404
    db.session.delete(job)
    db.session.commit()
    log_user_action("Delete Job", f"Deleted job {job.title} from native admin")
    return jsonify({"success": True, "message": "Job listing deleted."})


@mobile_api_bp.post("/admin/hiring/jobs/<int:job_id>/invite")
@mobile_login_required
def admin_hiring_invite_candidate(job_id):
    denied = _require_role("admin")
    if denied:
        return denied
    job = JobOpening.query.get(job_id)
    data = request.get_json(silent=True) or {}
    try:
        candidate_id = int(data.get("candidate_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a candidate."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    if not job or not candidate:
        return jsonify({"success": False, "message": "Job or candidate not found."}), 404
    try:
        send_email(to=candidate.email, subject=f"You're Invited to Apply — {job.title} at SourcePoint",
                   template="mail/job_invite_candidate.html", candidate=candidate, job=job,
                   admin_user=current_user, custom_message=str(data.get("custom_message", "")).strip(), now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Candidate job invitation failed")
        return jsonify({"success": False, "message": "Invitation could not be sent."}), 502
    log_user_action("Invite Candidate", f"Invited {candidate.username} to apply for {job.title} from native admin")
    return jsonify({"success": True, "message": f"Job invitation sent to {candidate.username}."})


@mobile_api_bp.patch("/admin/hiring/applications/<int:application_id>")
@mobile_login_required
def admin_hiring_update_application(application_id):
    denied = _require_role("admin")
    if denied:
        return denied
    application = JobApplication.query.get(application_id)
    if not application:
        return jsonify({"success": False, "message": "Application not found."}), 404
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in {item.value for item in ApplicationStatus}:
        return jsonify({"success": False, "message": "Choose a valid application status."}), 400
    application.status = status
    db.session.commit()
    return jsonify({"success": True, "message": "Application status updated."})


@mobile_api_bp.post("/admin/hiring/questions")
@mobile_login_required
def admin_hiring_create_question():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    values = [data.get("text"), data.get("option_a"), data.get("option_b"), data.get("option_c"), data.get("option_d")]
    correct = str(data.get("correct_option", "")).upper()
    if any(not isinstance(value, str) or not value.strip() for value in values) or correct not in {"A", "B", "C", "D"}:
        return jsonify({"success": False, "message": "Question text, four options, and the correct option are required."}), 400
    question = MCQQuestion(question_text=values[0].strip(), option_a=values[1].strip(), option_b=values[2].strip(),
                           option_c=values[3].strip(), option_d=values[4].strip(), correct_option=correct,
                           category=str(data.get("category", "")).strip() or None, created_by_id=current_user.id)
    db.session.add(question)
    db.session.commit()
    log_user_action("Create MCQ Question", f"Created question {question.id} from native admin")
    return jsonify({"success": True, "message": "Question created.", "id": question.id}), 201


@mobile_api_bp.patch("/admin/hiring/questions/<int:question_id>")
@mobile_login_required
def admin_update_question(question_id):
    denied = _require_role("admin")
    if denied:
        return denied
    question = MCQQuestion.query.get(question_id)
    if not question:
        return jsonify({"success": False, "message": "Question not found."}), 404
    data = request.get_json(silent=True) or {}
    for key, attr in {"text": "question_text", "option_a": "option_a", "option_b": "option_b", "option_c": "option_c", "option_d": "option_d"}.items():
        if key in data:
            value = data[key]
            if not isinstance(value, str) or not value.strip():
                return jsonify({"success": False, "message": "Question text and four options cannot be empty."}), 400
            setattr(question, attr, value.strip())
    if "correct_option" in data:
        correct = str(data["correct_option"]).upper()
        if correct not in {"A", "B", "C", "D"}:
            return jsonify({"success": False, "message": "Choose a valid correct option."}), 400
        question.correct_option = correct
    if "category" in data:
        question.category = str(data["category"]).strip() or None
    db.session.commit()
    return jsonify({"success": True, "message": "Question updated."})


@mobile_api_bp.delete("/admin/hiring/questions/<int:question_id>")
@mobile_login_required
def admin_delete_question(question_id):
    denied = _require_role("admin")
    if denied:
        return denied
    question = MCQQuestion.query.get(question_id)
    if not question:
        return jsonify({"success": False, "message": "Question not found."}), 404
    if question.tests.count() > 0:
        return jsonify({"success": False, "message": "This question is used in an assessment and cannot be deleted."}), 409
    db.session.delete(question)
    db.session.commit()
    return jsonify({"success": True, "message": "Question deleted."})


@mobile_api_bp.post("/admin/hiring/tests")
@mobile_login_required
def admin_hiring_create_test():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    try:
        duration = int(data.get("duration_minutes"))
        question_ids = [int(value) for value in data.get("question_ids", [])]
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a duration and select questions."}), 400
    if not isinstance(title, str) or not title.strip() or duration < 1 or not question_ids:
        return jsonify({"success": False, "message": "Test title, positive duration, and at least one question are required."}), 400
    questions = MCQQuestion.query.filter(MCQQuestion.id.in_(set(question_ids))).all()
    if len(questions) != len(set(question_ids)):
        return jsonify({"success": False, "message": "One or more selected questions are unavailable."}), 400
    test = Test(title=title.strip()[:200], description=str(data.get("description", ""))[:4000],
                duration_minutes=duration, created_by_id=current_user.id, questions=questions)
    db.session.add(test)
    db.session.commit()
    return jsonify({"success": True, "message": "Assessment created.", "id": test.id}), 201


@mobile_api_bp.patch("/admin/hiring/tests/<int:test_id>")
@mobile_login_required
def admin_hiring_update_test(test_id):
    denied = _require_role("admin")
    if denied:
        return denied
    test = Test.query.get(test_id)
    if not test:
        return jsonify({"success": False, "message": "Assessment not found."}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return jsonify({"success": False, "message": "Assessment title cannot be empty."}), 400
        test.title = data["title"].strip()[:200]
    if "description" in data and isinstance(data["description"], str):
        test.description = data["description"][:4000]
    if "duration_minutes" in data:
        try:
            duration = int(data["duration_minutes"])
            if duration < 1:
                raise ValueError
            test.duration_minutes = duration
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Duration must be positive."}), 400
    if "question_ids" in data:
        try:
            ids = {int(value) for value in data["question_ids"]}
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Question selection is invalid."}), 400
        questions = MCQQuestion.query.filter(MCQQuestion.id.in_(ids)).all() if ids else []
        if len(questions) != len(ids):
            return jsonify({"success": False, "message": "One or more questions are unavailable."}), 400
        test.questions = questions
    db.session.commit()
    return jsonify({"success": True, "message": "Assessment updated."})


@mobile_api_bp.delete("/admin/hiring/tests/<int:test_id>")
@mobile_login_required
def admin_hiring_delete_test(test_id):
    denied = _require_role("admin")
    if denied:
        return denied
    test = Test.query.get(test_id)
    if not test:
        return jsonify({"success": False, "message": "Assessment not found."}), 404
    if test.assignments:
        return jsonify({"success": False, "message": "This assessment has candidate assignments and cannot be deleted."}), 409
    db.session.delete(test)
    db.session.commit()
    return jsonify({"success": True, "message": "Assessment deleted."})


@mobile_api_bp.post("/admin/hiring/assignments")
@mobile_login_required
def admin_hiring_assign_test():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        test_id, candidate_id, reviewer_id = int(data.get("test_id")), int(data.get("candidate_id")), int(data.get("reviewer_id"))
        scheduled = datetime.fromisoformat(str(data.get("scheduled_start_time", "")).replace("Z", "+00:00"))
        if scheduled.tzinfo:
            scheduled = scheduled.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a test, candidate, reviewer, and valid start time."}), 400
    test = Test.query.get(test_id)
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value, is_approved=True).first()
    reviewer = User.query.filter(User.id == reviewer_id, User.role.in_([UserRole.MODERATOR.value, UserRole.DEVELOPER.value]), User.is_approved.is_(True)).first()
    if not test or not candidate or not reviewer:
        return jsonify({"success": False, "message": "The selected test, candidate, or reviewer is unavailable."}), 400
    assignment = TestAssignment(test_id=test.id, candidate_id=candidate.id, reviewer_id=reviewer.id, scheduled_start_time=scheduled)
    db.session.add(assignment)
    db.session.commit()
    return jsonify({"success": True, "message": "Assessment assigned.", "id": assignment.id}), 201


@mobile_api_bp.post("/admin/hiring/interviews")
@mobile_login_required
def admin_hiring_create_interview():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    try:
        candidate_id = int(data.get("candidate_id"))
        moderators_ids = list(dict.fromkeys(int(value) for value in data.get("moderator_ids", [])))
        scheduled = datetime.fromisoformat(str(data.get("scheduled_time", "")).replace("Z", "+00:00"))
        if scheduled.tzinfo:
            scheduled = scheduled.astimezone(timezone.utc).replace(tzinfo=None)
        duration = int(data.get("duration_minutes", 60))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Provide a candidate, moderator, date/time, and valid duration."}), 400
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    moderators = User.query.filter(User.id.in_(moderators_ids), User.role == UserRole.MODERATOR.value, User.is_approved.is_(True)).all()
    if not isinstance(title, str) or not title.strip() or not candidate or not moderators_ids or len(moderators) != len(moderators_ids) or duration < 1 or duration > 480:
        return jsonify({"success": False, "message": "Interview details or participant selection are invalid."}), 400
    from services.jitsi_meet_service import JitsiMeetService
    meet_link = JitsiMeetService().create_meeting(title.strip(), scheduled_time=scheduled)["meet_link"]
    interview = Interview(title=title.strip()[:200], description=str(data.get("description", ""))[:5000],
                          scheduled_time=scheduled, duration_minutes=duration, candidate_id=candidate.id,
                          google_meet_link=meet_link, status="scheduled", created_by=current_user.id)
    db.session.add(interview)
    db.session.flush()
    for moderator in moderators:
        db.session.add(InterviewParticipant(interview_id=interview.id, user_id=moderator.id, role="moderator", notified_at=datetime.utcnow()))
    db.session.commit()
    ist_time = scheduled + timedelta(hours=5, minutes=30)
    for moderator in moderators:
        try:
            send_email(to=moderator.email, subject=f"Interview Scheduled: {interview.title}", template="mail/interview_scheduled_moderator.html",
                       moderator=moderator, candidate=candidate, interview=interview, other_moderators=[m for m in moderators if m.id != moderator.id],
                       scheduled_time_ist=ist_time, meet_link=meet_link, now=datetime.utcnow())
        except Exception:
            current_app.logger.exception("Interview created but moderator notification failed")
    try:
        send_email(to=candidate.email, subject=f"Interview Scheduled: {interview.title}", template="mail/interview_scheduled_candidate.html",
                   candidate=candidate, interview=interview, moderators=moderators, scheduled_time_ist=ist_time, meet_link=meet_link, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Interview created but candidate notification failed")
    log_user_action("Schedule Interview", f"Scheduled interview {interview.title} from native admin")
    return jsonify({"success": True, "message": "Interview scheduled.", "id": interview.id, "meeting_url": meet_link}), 201


@mobile_api_bp.post("/admin/hiring/interviews/<int:interview_id>/cancel")
@mobile_login_required
def admin_hiring_cancel_interview(interview_id):
    denied = _require_role("admin")
    if denied:
        return denied
    interview = Interview.query.get(interview_id)
    if not interview:
        return jsonify({"success": False, "message": "Interview not found."}), 404
    if interview.status == "cancelled":
        return jsonify({"success": False, "message": "Interview is already cancelled."}), 409
    interview.status = "cancelled"
    interview.updated_at = datetime.utcnow()
    db.session.commit()
    scheduled_time_ist = interview.scheduled_time + timedelta(hours=5, minutes=30)
    for participant in interview.participants:
        if participant.user and participant.user.email:
            try:
                send_email(to=participant.user.email, subject=f"Interview Cancelled: {interview.title}",
                           template="mail/interview_cancelled.html", user=participant.user, interview=interview,
                           candidate=interview.candidate, scheduled_time_ist=scheduled_time_ist, now=datetime.utcnow())
            except Exception:
                current_app.logger.exception("Interview cancelled but moderator notification failed")
    if interview.candidate and interview.candidate.email:
        try:
            send_email(to=interview.candidate.email, subject=f"Interview Cancelled: {interview.title}",
                       template="mail/interview_cancelled.html", user=interview.candidate, interview=interview,
                       candidate=interview.candidate, scheduled_time_ist=scheduled_time_ist, now=datetime.utcnow())
        except Exception:
            current_app.logger.exception("Interview cancelled but candidate notification failed")
    return jsonify({"success": True, "message": "Interview cancelled."})


@mobile_api_bp.patch("/admin/hiring/interviews/<int:interview_id>")
@mobile_login_required
def admin_hiring_reschedule_interview(interview_id):
    denied = _require_role("admin")
    if denied:
        return denied
    interview = Interview.query.get(interview_id)
    if not interview or interview.status == "cancelled":
        return jsonify({"success": False, "message": "Active interview not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        scheduled = datetime.fromisoformat(str(data.get("scheduled_time", "")).replace("Z", "+00:00"))
        if scheduled.tzinfo:
            scheduled = scheduled.astimezone(timezone.utc).replace(tzinfo=None)
        duration = int(data.get("duration_minutes", interview.duration_minutes))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid date/time and duration."}), 400
    if duration < 1 or duration > 480:
        return jsonify({"success": False, "message": "Duration must be between 1 and 480 minutes."}), 400
    interview.scheduled_time, interview.duration_minutes = scheduled, duration
    interview.updated_at = datetime.utcnow()
    from services.jitsi_meet_service import JitsiMeetService
    interview.google_meet_link = JitsiMeetService().create_meeting(interview.title, interview_id=interview.id, scheduled_time=scheduled)["meet_link"]
    db.session.commit()
    ist_time = scheduled + timedelta(hours=5, minutes=30)
    moderators = [participant.user for participant in interview.participants if participant.user]
    for moderator in moderators:
        try:
            send_email(to=moderator.email, subject=f"Interview Rescheduled: {interview.title}", template="mail/interview_scheduled_moderator.html",
                       moderator=moderator, candidate=interview.candidate, interview=interview,
                       other_moderators=[m for m in moderators if m.id != moderator.id], scheduled_time_ist=ist_time,
                       meet_link=interview.google_meet_link, now=datetime.utcnow())
        except Exception:
            current_app.logger.exception("Interview rescheduled but moderator notification failed")
    try:
        send_email(to=interview.candidate.email, subject=f"Interview Rescheduled: {interview.title}", template="mail/interview_scheduled_candidate.html",
                   candidate=interview.candidate, interview=interview, moderators=moderators, scheduled_time_ist=ist_time,
                   meet_link=interview.google_meet_link, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Interview rescheduled but candidate notification failed")
    return jsonify({"success": True, "message": "Interview rescheduled and participants notified."})


@mobile_api_bp.post("/admin/hiring/interviews/<int:interview_id>/resend-invites")
@mobile_login_required
def admin_hiring_resend_interview_invites(interview_id):
    denied = _require_role("admin")
    if denied:
        return denied
    interview = Interview.query.get(interview_id)
    if not interview or interview.status == "cancelled":
        return jsonify({"success": False, "message": "Active interview not found."}), 404
    ist_time = interview.scheduled_time + timedelta(hours=5, minutes=30)
    moderators = [participant.user for participant in interview.participants if participant.user]
    try:
        for moderator in moderators:
            send_email(to=moderator.email, subject=f"Interview Reminder: {interview.title}", template="mail/interview_scheduled_moderator.html",
                       moderator=moderator, candidate=interview.candidate, interview=interview,
                       other_moderators=[m for m in moderators if m.id != moderator.id], scheduled_time_ist=ist_time,
                       meet_link=interview.google_meet_link, now=datetime.utcnow())
        send_email(to=interview.candidate.email, subject=f"Interview Reminder: {interview.title}", template="mail/interview_scheduled_candidate.html",
                   candidate=interview.candidate, interview=interview, moderators=moderators, scheduled_time_ist=ist_time,
                   meet_link=interview.google_meet_link, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Interview reminders failed to send")
        return jsonify({"success": False, "message": "One or more interview reminder emails could not be sent."}), 502
    return jsonify({"success": True, "message": "Interview reminders sent."})


@mobile_api_bp.get("/admin/events")
@mobile_login_required
def admin_events_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value).order_by(User.username).all()
    problems = ProblemStatement.query.order_by(ProblemStatement.created_at.desc()).all()
    scheduled = User.query.filter(User.problem_statement_id.isnot(None)).order_by(User.test_start_time.desc()).all()
    return jsonify({"success": True,
        "problems": [{"id": p.id, "title": p.title, "description": p.description, "difficulty": p.difficulty or "Medium",
                      "assigned_count": len(p.users)} for p in problems],
        "candidates": [{"id": u.id, "username": u.username, "email": u.email} for u in candidates],
        "moderators": [{"id": u.id, "username": u.username, "email": u.email}
                       for u in User.query.filter_by(role=UserRole.MODERATOR.value, is_approved=True, is_active=True).order_by(User.username).all()],
        "events": [{"id": u.id, "candidate": u.username, "candidate_email": u.email,
                    "problem_id": u.problem_statement_id, "problem": u.assigned_problem.title if u.assigned_problem else "",
                    "start_time": u.test_start_time.isoformat() if u.test_start_time else None,
                    "end_time": u.test_end_time.isoformat() if u.test_end_time else None,
                    "moderator_id": u.moderator_id, "moderator": u.moderator.username if u.moderator else "",
                    "meeting_link": u.meeting_link or "", "completed": bool(u.test_completed)} for u in scheduled]})


@mobile_api_bp.post("/admin/events/problems")
@mobile_login_required
def admin_events_create_problem():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title, description = data.get("title"), data.get("description")
    difficulty = data.get("difficulty", "Medium")
    if not isinstance(title, str) or not title.strip() or not isinstance(description, str) or not description.strip() or difficulty not in {"Easy", "Medium", "Hard"}:
        return jsonify({"success": False, "message": "Enter a problem title, description, and valid difficulty."}), 400
    problem = ProblemStatement(title=title.strip()[:200], description=description.strip(), difficulty=difficulty, created_by_id=current_user.id)
    db.session.add(problem)
    db.session.commit()
    log_user_action("Create Problem", f"Created coding problem {problem.title} from native admin")
    return jsonify({"success": True, "message": "Problem created.", "id": problem.id}), 201


@mobile_api_bp.patch("/admin/events/problems/<int:problem_id>")
@mobile_login_required
def admin_events_update_problem(problem_id):
    denied = _require_role("admin")
    if denied:
        return denied
    problem = ProblemStatement.query.get(problem_id)
    if not problem:
        return jsonify({"success": False, "message": "Problem not found."}), 404
    data = request.get_json(silent=True) or {}
    for field, max_len in (("title", 200), ("description", 50000)):
        if field in data:
            if not isinstance(data[field], str) or not data[field].strip():
                return jsonify({"success": False, "message": f"{field.title()} cannot be empty."}), 400
            setattr(problem, field, data[field].strip()[:max_len])
    if "difficulty" in data:
        if data["difficulty"] not in {"Easy", "Medium", "Hard"}:
            return jsonify({"success": False, "message": "Choose Easy, Medium, or Hard."}), 400
        problem.difficulty = data["difficulty"]
    db.session.commit()
    return jsonify({"success": True, "message": "Problem updated."})


@mobile_api_bp.delete("/admin/events/problems/<int:problem_id>")
@mobile_login_required
def admin_events_delete_problem(problem_id):
    denied = _require_role("admin")
    if denied:
        return denied
    problem = ProblemStatement.query.get(problem_id)
    if not problem:
        return jsonify({"success": False, "message": "Problem not found."}), 404
    if User.query.filter_by(problem_statement_id=problem.id).first():
        return jsonify({"success": False, "message": "This problem is assigned to a candidate and cannot be deleted yet."}), 409
    db.session.delete(problem)
    db.session.commit()
    return jsonify({"success": True, "message": "Problem deleted."})


@mobile_api_bp.post("/admin/events/assign")
@mobile_login_required
def admin_events_assign():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        candidate = User.query.filter_by(id=int(data.get("candidate_id")), role=UserRole.CANDIDATE.value).first()
        problem = ProblemStatement.query.get(int(data.get("problem_id")))
        start = datetime.fromisoformat(str(data.get("start_time", "")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(data.get("end_time", "")).replace("Z", "+00:00"))
        if start.tzinfo:
            start = start.astimezone(timezone.utc).replace(tzinfo=None)
        if end.tzinfo:
            end = end.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a candidate, problem, and valid start and end times."}), 400
    if not candidate or not problem or end <= start:
        return jsonify({"success": False, "message": "Candidate, problem, or time range is invalid."}), 400
    candidate.problem_statement_id = problem.id
    candidate.test_start_time = start
    candidate.test_end_time = end
    candidate.meeting_link = str(data.get("meeting_link", "")).strip()[:255] or None
    candidate.reminder_sent = False
    candidate.test_completed = False
    candidate.moderator_id = None
    db.session.commit()
    try:
        send_email(to=candidate.email, subject="You've Been Scheduled for a Coding Test", template="mail/test_scheduled.html",
                   candidate=candidate, problem=problem, start_time_ist=start + timedelta(hours=5, minutes=30),
                   end_time_ist=end + timedelta(hours=5, minutes=30), meeting_link=candidate.meeting_link)
    except Exception:
        current_app.logger.exception("Coding event saved but candidate notification failed")
    return jsonify({"success": True, "message": "Coding event scheduled."}), 201


@mobile_api_bp.post("/admin/events/<int:candidate_id>/action")
@mobile_login_required
def admin_events_action(candidate_id):
    denied = _require_role("admin")
    if denied:
        return denied
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    if not candidate:
        return jsonify({"success": False, "message": "Candidate not found."}), 404
    action = (request.get_json(silent=True) or {}).get("action")
    if action == "complete":
        candidate.test_completed = True
    elif action in {"cancel", "clear"}:
        if action == "clear":
            CodeTestSubmission.query.filter_by(candidate_id=candidate.id).delete()
        candidate.problem_statement_id = None
        candidate.test_start_time = None
        candidate.test_end_time = None
        candidate.reminder_sent = False
        candidate.moderator_id = None
        candidate.test_completed = False
    else:
        return jsonify({"success": False, "message": "Choose complete or cancel."}), 400
    db.session.commit()
    return jsonify({"success": True, "message": "Coding event history cleared." if action == "clear" else f"Coding event {action}d."})


@mobile_api_bp.patch("/admin/events/<int:candidate_id>/schedule")
@mobile_login_required
def admin_events_reschedule(candidate_id):
    denied = _require_role("admin")
    if denied:
        return denied
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    if not candidate or not candidate.problem_statement_id:
        return jsonify({"success": False, "message": "Scheduled candidate event not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        start = datetime.fromisoformat(str(data.get("start_time", "")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(data.get("end_time", "")).replace("Z", "+00:00"))
        if start.tzinfo:
            start = start.astimezone(timezone.utc).replace(tzinfo=None)
        if end.tzinfo:
            end = end.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter valid event start and end times."}), 400
    if end <= start:
        return jsonify({"success": False, "message": "Event end must be after its start."}), 400
    candidate.test_start_time, candidate.test_end_time = start, end
    candidate.reminder_sent = False
    candidate.moderator_id = None
    candidate.test_completed = False
    db.session.commit()
    try:
        send_email(to=candidate.email, subject="Your Coding Test Has Been Rescheduled", template="mail/test_rescheduled.html",
                   candidate=candidate, problem_title=candidate.assigned_problem.title if candidate.assigned_problem else "coding test",
                   start_time_ist=start + timedelta(hours=5, minutes=30), end_time_ist=end + timedelta(hours=5, minutes=30))
    except Exception:
        current_app.logger.exception("Coding event rescheduled but notification failed")
    return jsonify({"success": True, "message": "Coding event rescheduled."})


@mobile_api_bp.post("/admin/events/<int:candidate_id>/moderator")
@mobile_login_required
def admin_events_assign_moderator(candidate_id):
    denied = _require_role("admin")
    if denied:
        return denied
    candidate = User.query.filter_by(id=candidate_id, role=UserRole.CANDIDATE.value).first()
    data = request.get_json(silent=True) or {}
    try:
        moderator_id = int(data.get("moderator_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a moderator."}), 400
    moderator = User.query.filter_by(id=moderator_id, role=UserRole.MODERATOR.value, is_approved=True, is_active=True).first()
    if not candidate or not moderator or not all([candidate.assigned_problem, candidate.test_start_time, candidate.test_end_time]):
        return jsonify({"success": False, "message": "Candidate event or moderator selection is incomplete."}), 400
    candidate.moderator_id = moderator.id
    db.session.add(ModeratorAssignmentHistory(candidate_id=candidate.id, moderator_id=moderator.id,
                                              problem_statement_id=candidate.problem_statement_id))
    db.session.commit()
    try:
        ist_offset = timedelta(hours=5, minutes=30)
        send_email(to=moderator.email, cc=[candidate.email], subject=f"Moderator Assignment for {candidate.username}'s Test",
                   template="mail/moderator_assigned.html", moderator=moderator, candidate=candidate,
                   problem_title=candidate.assigned_problem.title, start_time_ist=candidate.test_start_time + ist_offset,
                   end_time_ist=candidate.test_end_time + ist_offset, meeting_link=candidate.meeting_link, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Moderator assigned but notification failed")
    return jsonify({"success": True, "message": "Moderator assigned."})


def _admin_project_payload(project):
    brd = project.brd
    return {
        "id": project.id, "name": project.name, "description": project.description or "",
        "status": project.status, "budget": float(project.budget or 0),
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "transactions": [{"id": item.id, "description": item.description, "amount": float(item.amount or 0),
                           "date": item.date.isoformat() if item.date else None, "category": item.category}
                          for item in sorted(project.transactions, key=lambda item: (item.date or datetime.min.date(), item.id), reverse=True)],
        "brd": ({field: getattr(brd, field) or "" for field in (
            "executive_summary", "project_objectives", "project_scope", "business_requirements",
            "key_stakeholders", "project_constraints", "cost_benefit_analysis",
            "executive_summary_label", "project_objectives_label", "project_scope_label",
            "business_requirements_label", "key_stakeholders_label", "project_constraints_label",
            "cost_benefit_analysis_label",
        )} if brd else {}),
    }


@mobile_api_bp.get("/admin/projects")
@mobile_login_required
def admin_projects_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    projects = Project.query.order_by(Project.start_date.desc().nullslast(), Project.id.desc()).all()
    return jsonify({"success": True, "projects": [_admin_project_payload(project) for project in projects],
                    "statuses": ["Planning", "In-Progress", "Development", "Testing", "Deployment", "Completed", "On-Hold"]})


@mobile_api_bp.post("/admin/projects")
@mobile_login_required
def admin_create_project():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
        return jsonify({"success": False, "message": "Enter a project name up to 150 characters."}), 400
    try:
        budget = float(data.get("budget", 0) or 0)
        start_date = datetime.strptime(str(data["start_date"]), "%Y-%m-%d").date() if data.get("start_date") else None
        end_date = datetime.strptime(str(data["end_date"]), "%Y-%m-%d").date() if data.get("end_date") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid budget and project dates."}), 400
    if budget < 0 or (start_date and end_date and end_date < start_date):
        return jsonify({"success": False, "message": "Budget cannot be negative and the end date must follow the start date."}), 400
    project = Project(name=name.strip(), description=str(data.get("description", "")).strip() or None,
                      budget=budget, start_date=start_date, end_date=end_date,
                      status=str(data.get("status", "Planning")).strip() or "Planning")
    db.session.add(project)
    db.session.commit()
    log_user_action("Create Project", f"Created project {project.name} from native admin")
    return jsonify({"success": True, "message": "Project created.", "project": _admin_project_payload(project)}), 201


@mobile_api_bp.patch("/admin/projects/<int:project_id>")
@mobile_login_required
def admin_update_project(project_id):
    denied = _require_role("admin")
    if denied:
        return denied
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
            return jsonify({"success": False, "message": "Enter a project name up to 150 characters."}), 400
        project.name = name.strip()
    if "description" in data:
        project.description = str(data.get("description") or "").strip() or None
    if "status" in data:
        project.status = str(data.get("status") or "Planning").strip()[:50] or "Planning"
    if "budget" in data:
        try:
            project.budget = float(data["budget"])
            if project.budget < 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Budget must be zero or greater."}), 400
    for field in ("start_date", "end_date"):
        if field in data:
            try:
                setattr(project, field, datetime.strptime(str(data[field]), "%Y-%m-%d").date() if data[field] else None)
            except ValueError:
                return jsonify({"success": False, "message": f"Enter a valid {field.replace('_', ' ')}."}), 400
    if project.start_date and project.end_date and project.end_date < project.start_date:
        return jsonify({"success": False, "message": "The end date must follow the start date."}), 400
    db.session.commit()
    log_user_action("Update Project", f"Updated project {project.name} from native admin")
    return jsonify({"success": True, "message": "Project updated.", "project": _admin_project_payload(project)})


@mobile_api_bp.post("/admin/projects/<int:project_id>/transactions")
@mobile_login_required
def admin_create_project_transaction(project_id):
    denied = _require_role("admin")
    if denied:
        return denied
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    data = request.get_json(silent=True) or {}
    description, category = data.get("description"), data.get("category")
    try:
        amount = float(data.get("amount"))
        date = datetime.strptime(str(data["date"]), "%Y-%m-%d").date() if data.get("date") else datetime.utcnow().date()
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid amount and date."}), 400
    if not isinstance(description, str) or not description.strip() or len(description.strip()) > 200 or amount <= 0 or category not in {"funding", "expense"}:
        return jsonify({"success": False, "message": "Enter a description, positive amount, and funding or expense category."}), 400
    item = Transaction(project_id=project.id, description=description.strip(), amount=amount, category=category, date=date)
    db.session.add(item)
    db.session.commit()
    log_user_action("Add Transaction", f"Added transaction to project {project.name} from native admin")
    return jsonify({"success": True, "message": "Project transaction added.", "id": item.id}), 201


@mobile_api_bp.patch("/admin/projects/transactions/<int:transaction_id>")
@mobile_login_required
def admin_update_project_transaction(transaction_id):
    denied = _require_role("admin")
    if denied:
        return denied
    item = Transaction.query.get(transaction_id)
    if not item:
        return jsonify({"success": False, "message": "Project transaction not found."}), 404
    data = request.get_json(silent=True) or {}
    if "description" in data:
        description = str(data.get("description") or "").strip()
        if not description or len(description) > 200:
            return jsonify({"success": False, "message": "Enter a transaction description up to 200 characters."}), 400
        item.description = description
    if "amount" in data:
        try:
            item.amount = float(data["amount"])
            if item.amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Amount must be positive."}), 400
    if "category" in data:
        if data["category"] not in {"funding", "expense"}:
            return jsonify({"success": False, "message": "Choose funding or expense."}), 400
        item.category = data["category"]
    if "date" in data:
        try:
            item.date = datetime.strptime(str(data["date"]), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Enter a valid transaction date."}), 400
    db.session.commit()
    return jsonify({"success": True, "message": "Project transaction updated."})


@mobile_api_bp.delete("/admin/projects/transactions/<int:transaction_id>")
@mobile_login_required
def admin_delete_project_transaction(transaction_id):
    denied = _require_role("admin")
    if denied:
        return denied
    item = Transaction.query.get(transaction_id)
    if not item:
        return jsonify({"success": False, "message": "Project transaction not found."}), 404
    db.session.delete(item)
    db.session.commit()
    log_user_action("Delete Transaction", f"Deleted project transaction {transaction_id} from native admin")
    return jsonify({"success": True, "message": "Project transaction deleted."})


@mobile_api_bp.put("/admin/projects/<int:project_id>/brd")
@mobile_login_required
def admin_save_project_brd(project_id):
    denied = _require_role("admin")
    if denied:
        return denied
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    data = request.get_json(silent=True) or {}
    brd = project.brd or BRD(project_id=project.id)
    for field in (
        "executive_summary", "project_objectives", "project_scope", "business_requirements",
        "key_stakeholders", "project_constraints", "cost_benefit_analysis",
        "executive_summary_label", "project_objectives_label", "project_scope_label",
        "business_requirements_label", "key_stakeholders_label", "project_constraints_label",
        "cost_benefit_analysis_label",
    ):
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, str):
                return jsonify({"success": False, "message": f"Invalid BRD value for {field}."}), 400
            setattr(brd, field, value.strip() if isinstance(value, str) else None)
    if not project.brd:
        db.session.add(brd)
    db.session.commit()
    log_user_action("Update BRD", f"Updated BRD for {project.name} from native admin")
    return jsonify({"success": True, "message": "Business requirements document saved."})


@mobile_api_bp.post("/admin/projects/<int:project_id>/brd/share")
@mobile_login_required
def admin_share_project_brd(project_id):
    denied = _require_role("admin")
    if denied:
        return denied
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    data = request.get_json(silent=True) or {}
    recipient = str(data.get("recipient_email", "")).strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        return jsonify({"success": False, "message": "Enter a valid recipient email."}), 400
    try:
        from brd_generator import BrdGenerator
        pdf = BrdGenerator(project).generate_pdf()
        send_email(to=recipient, subject=f"Business Requirement Document for {project.name}",
                   template="mail/brd_shared.html", project_name=project.name,
                   attachments=[{"filename": f"BRD_{secure_filename(project.name) or 'project'}.pdf",
                                 "content_type": "application/pdf", "data": pdf}], now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Native admin could not email project BRD")
        return jsonify({"success": False, "message": "BRD could not be generated or emailed."}), 502
    log_user_action("Share BRD", f"Shared BRD for {project.name} to {recipient} from native admin")
    return jsonify({"success": True, "message": "BRD emailed."})


@mobile_api_bp.get("/admin/finance")
@mobile_login_required
def admin_finance_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    start_value, end_value = request.args.get("start_date", "").strip(), request.args.get("end_date", "").strip()
    try:
        start_day = datetime.strptime(start_value, "%Y-%m-%d").date() if start_value else datetime(2000, 1, 1).date()
        end_day = datetime.strptime(end_value, "%Y-%m-%d").date() + timedelta(days=1) if end_value else (datetime.utcnow() + timedelta(days=1)).date()
    except ValueError:
        return jsonify({"success": False, "message": "Analytics dates must use YYYY-MM-DD."}), 400
    if end_day <= start_day:
        return jsonify({"success": False, "message": "End date must be after the start date."}), 400
    plans = EMIPlan.query.order_by(EMIPlan.created_at.desc()).limit(100).all()
    cards = GiftCard.query.order_by(GiftCard.created_at.desc()).limit(200).all()
    voucher_orders = VoucherOrder.query.order_by(VoucherOrder.created_at.desc()).limit(100).all()
    projects = Project.query.order_by(Project.start_date.desc().nullslast()).limit(100).all()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).limit(500).all()
    funding = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.category == "funding", Transaction.date >= start_day, Transaction.date < end_day
    ).scalar() or 0
    expenses = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.category == "expense", Transaction.date >= start_day, Transaction.date < end_day
    ).scalar() or 0
    period_start = datetime.combine(start_day, datetime.min.time())
    period_end = datetime.combine(end_day, datetime.min.time())
    app_counts = dict(db.session.query(JobApplication.status, func.count(JobApplication.id)).filter(
        JobApplication.applied_at >= period_start, JobApplication.applied_at < period_end
    ).group_by(JobApplication.status).all())
    project_statuses = [{"status": status, "count": count} for status, count in db.session.query(
        Project.status, func.count(Project.id)
    ).filter(Project.start_date >= start_day, Project.start_date < end_day).group_by(Project.status).all()]
    try:
        from services.superscoins_service import SupersCoinsService
        coins_ready = SupersCoinsService.tables_ready()
        wallets = SupersCoinWallet.query.order_by(SupersCoinWallet.balance.desc()).all() if coins_ready else []
        coin_invoices = SupersCoinInvoice.query.order_by(SupersCoinInvoice.created_at.desc()).limit(200).all() if coins_ready else []
    except Exception:
        coins_ready, wallets, coin_invoices = False, [], []
    return jsonify({"success": True,
        "analytics": {"users": User.query.count(), "pending_users": User.query.filter_by(is_approved=False).count(),
                      "pending_applications": app_counts.get(ApplicationStatus.PENDING.value, 0),
                      "accepted_applications": app_counts.get(ApplicationStatus.ACCEPTED.value, 0),
                      "rejected_applications": app_counts.get(ApplicationStatus.REJECTED.value, 0),
                      "funding": float(funding), "expenses": float(expenses), "projects": sum(row["count"] for row in project_statuses),
                      "project_statuses": project_statuses, "start_date": start_value, "end_date": end_value},
        "plans": [{"id": p.id, "title": p.title, "borrower_id": p.borrower_id, "borrower": p.borrower.username if p.borrower else "",
                   "lender_id": p.lender_id, "lender": p.lender.username if p.lender else "", "total_principal": float(p.total_principal or 0),
                   "is_active": p.is_active, "payments": [{"id": x.id, "installment_number": x.installment_number,
                   "due_date": x.due_date.isoformat() if x.due_date else None, "amount": float(x.amount or 0),
                   "description": x.description or "", "status": x.status, "payment_date": x.payment_date.isoformat() if x.payment_date else None}
                   for x in p.payments]} for p in plans],
        "users": [{"id": u.id, "username": u.username, "email": u.email, "role": u.role} for u in users],
        "gift_cards": [{"id": c.id, "brand": c.brand, "denomination": float(c.denomination or 0),
                        "masked_card_number": c.masked_card_number, "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                        "status": c.status, "recipient_name": c.recipient_name or "", "recipient_email": c.recipient_email or "",
                        "notes": c.notes or ""} for c in cards],
        "voucher_orders": [{"id": v.id, "buyer": v.user.username if v.user else "", "buyer_email": v.user.email if v.user else "",
                            "brand": v.gift_card.brand if v.gift_card else "", "denomination": float(v.gift_card.denomination or 0) if v.gift_card else 0,
                            "status": v.status, "created_at": v.created_at.isoformat() if v.created_at else None,
                            "rejection_reason": v.rejection_reason or ""} for v in voucher_orders],
        "projects": [{"id": p.id, "name": p.name, "description": p.description or "", "status": p.status,
                      "budget": float(p.budget or 0), "start_date": p.start_date.isoformat() if p.start_date else None,
                      "end_date": p.end_date.isoformat() if p.end_date else None,
                      "transactions": [{"id": t.id, "description": t.description, "amount": float(t.amount or 0),
                                        "date": t.date.isoformat() if t.date else None, "category": t.category} for t in p.transactions]} for p in projects],
        "logs": [{"id": l.id, "user": l.user.username if l.user else "", "action": l.action, "details": l.details or "",
                  "ip_address": l.ip_address or "", "timestamp": l.timestamp.isoformat() if l.timestamp else None} for l in logs],
        "superscoins": {"available": coins_ready, "wallets": [{"seller_id": w.seller_id, "seller": w.seller.username if w.seller else "",
                          "balance": float(w.balance or 0),
                          "transactions": [{"id": tx.id, "type": tx.transaction_type, "amount": float(tx.amount or 0),
                                            "balance_after": float(tx.balance_after or 0), "note": tx.note or "",
                                            "created_at": tx.created_at.isoformat() if tx.created_at else None}
                                           for tx in list(w.transactions)[:100]]} for w in wallets],
                          "invoices": [{"id": i.id, "invoice_number": i.invoice_number, "seller_id": i.seller_id,
                                        "seller": i.seller.username if i.seller else "", "amount": float(i.amount or 0),
                                        "status": i.status, "description": i.description, "notes": i.notes or "",
                                        "spending_category": i.spending_category or "", "booking_details": i.booking_details or "",
                                        "created_at": i.created_at.isoformat() if i.created_at else None,
                                        "due_date": i.due_date.isoformat() if i.due_date else None}
                                       for i in coin_invoices]}})


@mobile_api_bp.get("/admin/emi")
@mobile_login_required
def admin_emi_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    plans = EMIPlan.query.options(
        joinedload(EMIPlan.borrower), joinedload(EMIPlan.lender), selectinload(EMIPlan.payments),
    ).order_by(EMIPlan.created_at.desc(), EMIPlan.id.desc()).all()
    today = datetime.utcnow().date()
    plan_payloads = []
    installment_count = 0
    paid_count = 0
    overdue_count = 0
    pending_total = 0.0
    overdue_total = 0.0
    completed_count = 0
    for plan in plans:
        payments = sorted(plan.payments, key=lambda row: (row.installment_number, row.id))
        installment_count += len(payments)
        plan_paid = sum(float(row.amount or 0) for row in payments if row.status == "Paid")
        plan_pending = sum(float(row.amount or 0) for row in payments if row.status != "Paid")
        plan_overdue = [row for row in payments if row.status != "Paid" and row.due_date and row.due_date < today]
        paid_count += sum(1 for row in payments if row.status == "Paid")
        overdue_count += len(plan_overdue)
        pending_total += plan_pending
        overdue_total += sum(float(row.amount or 0) for row in plan_overdue)
        completed = bool(payments) and all(row.status == "Paid" for row in payments)
        completed_count += 1 if completed else 0
        plan_payloads.append({
            "id": plan.id,
            "title": plan.title,
            "borrower_id": plan.borrower_id,
            "borrower": plan.borrower.username if plan.borrower else "",
            "lender_id": plan.lender_id,
            "lender": plan.lender.username if plan.lender else "",
            "total_principal": float(plan.total_principal or 0),
            "is_active": bool(plan.is_active),
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "payments": [{
                "id": row.id,
                "installment_number": row.installment_number,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "amount": float(row.amount or 0),
                "description": row.description or "",
                "status": row.status,
                "payment_date": row.payment_date.isoformat() if row.payment_date else None,
                "reminder_days_before": row.reminder_days_before,
            } for row in payments],
        })
    users = User.query.filter(User.role != UserRole.ADMIN.value, User.is_active.is_(True)).order_by(User.username.asc()).limit(500).all()
    return jsonify({
        "success": True,
        "summary": {
            "plan_count": len(plans),
            "active_count": sum(1 for plan in plans if plan.is_active),
            "completed_count": completed_count,
            "installment_count": installment_count,
            "paid_count": paid_count,
            "pending_count": max(0, installment_count - paid_count),
            "overdue_count": overdue_count,
            "pending_amount": round(pending_total, 2),
            "overdue_amount": round(overdue_total, 2),
            "today": today.isoformat(),
        },
        "plans": plan_payloads,
        "users": [{"id": user.id, "username": user.username, "email": user.email, "role": user.role} for user in users],
    })


@mobile_api_bp.post("/admin/communications/email")
@mobile_login_required
def admin_send_email():
    denied = _require_role("admin")
    if denied:
        return denied
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        try:
            data = json.loads(request.form.get("payload", "{}"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Email request data is invalid."}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Email request data is invalid."}), 400
    subject, body = data.get("subject"), data.get("body")
    if not isinstance(subject, str) or not subject.strip() or not isinstance(body, str) or not body.strip() or len(body) > 20000:
        return jsonify({"success": False, "message": "Enter a subject and a message under 20,000 characters."}), 400
    attachments = []
    attachment = request.files.get("attachment")
    if attachment and attachment.filename:
        filename = secure_filename(attachment.filename)
        content = attachment.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            return jsonify({"success": False, "message": "Email attachment must be 10 MB or smaller."}), 413
        attachments.append({"filename": filename, "content_type": attachment.mimetype or "application/octet-stream", "data": content})
    ids = data.get("user_ids", [])
    if not isinstance(ids, list):
        return jsonify({"success": False, "message": "Recipient selection is invalid."}), 400
    if data.get("all_active"):
        recipients = User.query.filter_by(is_active=True).all()
        excluded = {str(value) for value in data.get("excluded_ids", [])}
        recipients = [u for u in recipients if str(u.id) not in excluded]
    else:
        try:
            wanted = {int(value) for value in ids}
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Recipient selection is invalid."}), 400
        if not wanted:
            return jsonify({"success": False, "message": "Choose at least one recipient."}), 400
        recipients = User.query.filter(User.id.in_(wanted), User.is_active.is_(True)).all()
    if not recipients:
        return jsonify({"success": False, "message": "No active recipients were selected."}), 400
    sender_email = os.environ.get("MAIL_DEFAULT_SENDER_EMAIL", current_user.email)
    count = 0
    try:
        if data.get("all_active"):
            to_email = sender_email
            bcc = [u.email for u in recipients if u.email and u.email != sender_email]
            send_email(to=to_email, bcc=bcc, subject=subject.strip(), template="mail/broadcast.html", user=current_user, body=body.strip(), attachments=attachments)
            count = len(recipients)
        else:
            for user in recipients:
                if user.email:
                    send_email(to=user.email, subject=subject.strip(), template="mail/broadcast.html", recipient=user, message=body.strip(), attachments=attachments)
                    count += 1
    except Exception:
        current_app.logger.exception("Admin native email dispatch failed")
        return jsonify({"success": False, "message": "Email could not be sent. Check server mail configuration."}), 502
    log_user_action("Broadcast Email" if data.get("all_active") else "Send Specific Email", f"Sent native admin email to {count} account(s)")
    return jsonify({"success": True, "message": f"Email sent to {count} account(s).", "recipient_count": count})


@mobile_api_bp.post("/admin/emi/plans")
@mobile_login_required
def admin_create_emi_plan():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        borrower = User.query.get(int(data.get("borrower_id")))
        lender = User.query.get(int(data.get("lender_id")))
        installments = data.get("installments")
        if not isinstance(installments, list) or not installments:
            raise ValueError
        rows = []
        for row in installments:
            amount = float(row.get("amount"))
            due_date = datetime.strptime(str(row.get("due_date")), "%Y-%m-%d").date()
            if amount <= 0:
                raise ValueError
            rows.append((amount, due_date, str(row.get("description", "")).strip()[:200]))
    except (TypeError, ValueError, AttributeError):
        return jsonify({"success": False, "message": "Enter borrower, lender, title, and valid positive installments."}), 400
    title = data.get("title")
    if not borrower or not lender or borrower.id == lender.id or not isinstance(title, str) or not title.strip():
        return jsonify({"success": False, "message": "Borrower, lender, and plan title are required. They must be different users."}), 400
    total = sum(row[0] for row in rows)
    plan = EMIPlan(title=title.strip()[:150], total_principal=total, borrower_id=borrower.id, lender_id=lender.id)
    db.session.add(plan)
    db.session.flush()
    for index, (amount, due_date, description) in enumerate(sorted(rows, key=lambda row: row[1]), 1):
        db.session.add(EMIPayment(plan_id=plan.id, installment_number=index, due_date=due_date, amount=amount,
                                 description=description or f"Installment {index}", reminder_days_before=max(0, min(int(data.get("reminder_days", 3)), 60))))
    db.session.commit()
    log_user_action("Create EMI Plan", f"Created plan {plan.title} from native admin")
    return jsonify({"success": True, "message": "EMI plan created.", "id": plan.id}), 201


@mobile_api_bp.patch("/admin/emi/payments/<int:payment_id>")
@mobile_login_required
def admin_update_emi_payment(payment_id):
    denied = _require_role("admin")
    if denied:
        return denied
    payment = EMIPayment.query.get(payment_id)
    if not payment:
        return jsonify({"success": False, "message": "EMI payment not found."}), 404
    data = request.get_json(silent=True) or {}
    became_paid = payment.status != "Paid" and data.get("status") == "Paid"
    if "amount" in data:
        try:
            payment.amount = float(data["amount"])
            if payment.amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Amount must be positive."}), 400
    if "due_date" in data:
        try:
            payment.due_date = datetime.strptime(str(data["due_date"]), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Enter a valid due date."}), 400
    if "description" in data:
        payment.description = str(data["description"]).strip()[:200]
    if "status" in data:
        if data["status"] not in {"Pending", "Paid"}:
            return jsonify({"success": False, "message": "Choose Pending or Paid."}), 400
        payment.status = data["status"]
        payment.payment_date = datetime.utcnow() if payment.status == "Paid" else None
    db.session.commit()
    email_task_id = None
    if became_paid:
        try:
            lender = payment.plan.lender
            email_task_id = send_email(
                to=lender.email, subject=f"Payment Received: {payment.description}",
                template="mail/emi_paid_notification_lender.html", lender=lender,
                borrower=payment.plan.borrower, payment=payment, paid_date=payment.payment_date,
                return_task_id=True, require_worker=True,
            ) if lender and lender.email else None
        except Exception:
            current_app.logger.exception("EMI saved but lender notification failed")
        if not email_task_id:
            current_app.logger.warning("EMI payment %s was marked paid but its lender email was not accepted", payment.id)
            return jsonify({
                "success": True,
                "message": "EMI was marked paid, but the lender email was not sent. Use Resend lender notification to retry.",
                "email_sent": False,
            })
        return jsonify({
            "success": True,
            "message": "EMI marked paid. Lender notification queued.",
            "email_status": "queued",
            "email_task_id": email_task_id,
        }), 202
    return jsonify({"success": True, "message": "EMI payment updated."})


@mobile_api_bp.post("/admin/emi/payments/<int:payment_id>/notify-lender")
@mobile_login_required
def admin_resend_emi_paid_notification(payment_id):
    denied = _require_role("admin")
    if denied:
        return denied
    payment = EMIPayment.query.get(payment_id)
    if not payment:
        return jsonify({"success": False, "message": "EMI payment not found."}), 404
    if payment.status != "Paid":
        return jsonify({"success": False, "message": "Only paid installments can send a payment notification."}), 409
    lender = payment.plan.lender
    if not lender or not lender.email:
        return jsonify({"success": False, "message": "The lender has no email address on file."}), 409
    try:
        email_task_id = send_email(
            to=lender.email, subject=f"Payment Received: {payment.description}",
            template="mail/emi_paid_notification_lender.html", lender=lender,
            borrower=payment.plan.borrower, payment=payment, paid_date=payment.payment_date,
            return_task_id=True, require_worker=True,
        )
    except Exception:
        current_app.logger.exception("EMI lender notification retry failed for payment %s", payment.id)
        email_task_id = None
    if not email_task_id:
        current_app.logger.warning("EMI lender notification retry was not accepted for payment %s", payment.id)
        return jsonify({
            "success": False,
            "message": "The notification could not be queued. Check Redis and the Celery email worker, then retry.",
        }), 502
    return jsonify({
        "success": True,
        "message": "Lender notification queued.",
        "email_status": "queued",
        "email_task_id": email_task_id,
    }), 202


@mobile_api_bp.get("/admin/email-jobs/<string:task_id>")
@mobile_login_required
def admin_email_job_status(task_id):
    denied = _require_role("admin")
    if denied:
        return denied
    from worker import send_email_task

    task = send_email_task.AsyncResult(task_id)
    if task.state in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
        return jsonify({
            "success": True,
            "email_status": "sending" if task.state in {"STARTED", "RETRY"} else "queued",
            "message": "Email delivery is still processing.",
        }), 202
    if task.state == "SUCCESS" and task.result is True:
        return jsonify({"success": True, "email_status": "sent", "message": "The email provider accepted the message."})
    current_app.logger.error("Email delivery task %s failed with state %s", task_id, task.state)
    return jsonify({
        "success": False,
        "email_status": "failed",
        "message": "The email worker or provider could not send the message. Check the server email logs and retry.",
    }), 502


@mobile_api_bp.delete("/admin/emi/plans/<int:plan_id>")
@mobile_login_required
def admin_delete_emi_plan(plan_id):
    denied = _require_role("admin")
    if denied:
        return denied
    plan = EMIPlan.query.get(plan_id)
    if not plan:
        return jsonify({"success": False, "message": "EMI plan not found."}), 404
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"success": True, "message": "EMI plan deleted."})


@mobile_api_bp.post("/admin/gift-cards")
@mobile_login_required
def admin_create_gift_card():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    brand, number, pin = data.get("brand"), data.get("card_number"), data.get("pin")
    try:
        denomination = float(data.get("denomination"))
        expiry = datetime.strptime(str(data["expiry_date"]), "%Y-%m-%d").date() if data.get("expiry_date") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid denomination and expiry date."}), 400
    if not isinstance(brand, str) or not brand.strip() or not isinstance(number, str) or not number.strip() or not isinstance(pin, str) or not pin.strip() or denomination <= 0:
        return jsonify({"success": False, "message": "Brand, positive denomination, card number, and PIN are required."}), 400
    try:
        card = GiftCard(brand=brand.strip()[:50], denomination=denomination, expiry_date=expiry,
                        notes=str(data.get("notes", "")).strip()[:4000] or None, created_by_id=current_user.id)
        card.set_card_number(number.strip())
        card.set_pin(pin.strip())
        db.session.add(card)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native gift card creation failed")
        return jsonify({"success": False, "message": "Gift card could not be saved. Check the server encryption key."}), 503
    log_user_action("Gift Card Added", f"Added {card.brand} gift card from native admin")
    return jsonify({"success": True, "message": "Gift card added.", "id": card.id}), 201


@mobile_api_bp.post("/admin/gift-cards/bulk")
@mobile_login_required
def admin_bulk_create_gift_cards():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    brand = str(data.get("brand", "")).strip()[:50]
    try:
        denomination = float(data.get("denomination"))
        expiry = datetime.strptime(str(data["expiry_date"]), "%Y-%m-%d").date() if data.get("expiry_date") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid denomination and expiry date."}), 400
    rows = data.get("cards")
    if not brand or denomination <= 0 or not isinstance(rows, list) or not rows or len(rows) > 500:
        return jsonify({"success": False, "message": "Enter a brand, positive denomination, and between 1 and 500 card/PIN pairs."}), 400
    if any(not isinstance(row, dict) or not str(row.get("card_number", "")).strip() or not str(row.get("pin", "")).strip() for row in rows):
        return jsonify({"success": False, "message": "Every card needs both a card number and PIN."}), 400
    try:
        for row in rows:
            card = GiftCard(brand=brand, denomination=denomination, expiry_date=expiry,
                            notes=str(data.get("notes", "")).strip()[:4000] or None, created_by_id=current_user.id)
            card.set_card_number(str(row["card_number"]).strip())
            card.set_pin(str(row["pin"]).strip())
            db.session.add(card)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native bulk gift card import failed")
        return jsonify({"success": False, "message": "Gift cards could not be saved. Check server encryption settings."}), 503
    log_user_action("Bulk Gift Cards Added", f"Added {len(rows)} {brand} gift cards from native admin")
    return jsonify({"success": True, "message": f"Added {len(rows)} gift cards."}), 201


@mobile_api_bp.patch("/admin/gift-cards/<int:card_id>")
@mobile_login_required
def admin_update_gift_card(card_id):
    denied = _require_role("admin")
    if denied:
        return denied
    card = GiftCard.query.get(card_id)
    if not card:
        return jsonify({"success": False, "message": "Gift card not found."}), 404
    if card.status != GiftCardStatus.AVAILABLE.value:
        return jsonify({"success": False, "message": "Only available gift cards can be edited."}), 409
    data = request.get_json(silent=True) or {}
    if "brand" in data:
        brand = str(data.get("brand") or "").strip()
        if not brand:
            return jsonify({"success": False, "message": "Brand is required."}), 400
        card.brand = brand[:50]
    if "denomination" in data:
        try:
            card.denomination = float(data["denomination"])
            if card.denomination <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Denomination must be greater than zero."}), 400
    if "expiry_date" in data:
        try:
            card.expiry_date = datetime.strptime(str(data["expiry_date"]), "%Y-%m-%d").date() if data["expiry_date"] else None
        except ValueError:
            return jsonify({"success": False, "message": "Enter a valid expiry date."}), 400
    if "notes" in data:
        card.notes = str(data.get("notes") or "").strip()[:4000] or None
    if str(data.get("card_number", "")).strip():
        card.set_card_number(str(data["card_number"]).strip())
    if str(data.get("pin", "")).strip():
        card.set_pin(str(data["pin"]).strip())
    db.session.commit()
    log_user_action("Gift Card Edited", f"Updated available gift card {card.id} from native admin")
    return jsonify({"success": True, "message": "Gift card updated."})


@mobile_api_bp.post("/admin/gift-cards/<int:card_id>/send")
@mobile_login_required
def admin_send_gift_card(card_id):
    denied = _require_role("admin")
    if denied:
        return denied
    card = GiftCard.query.filter_by(id=card_id).with_for_update().first()
    data = request.get_json(silent=True) or {}
    name, email = data.get("recipient_name"), data.get("recipient_email")
    if not card or card.status != GiftCardStatus.AVAILABLE.value or card.is_expired:
        return jsonify({"success": False, "message": "Available gift card not found."}), 404
    if VoucherOrder.query.filter_by(
        gift_card_id=card.id, status=VoucherOrderStatus.PENDING.value
    ).first():
        return jsonify({"success": False, "message": "This gift card has a pending buyer request."}), 409
    if not isinstance(name, str) or not name.strip() or not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        return jsonify({"success": False, "message": "Enter a recipient name and valid email."}), 400
    custom_message = data.get("custom_message", "")
    if not isinstance(custom_message, str) or len(custom_message) > 1500:
        return jsonify({"success": False, "message": "Personal message must be 1,500 characters or fewer."}), 400
    sender_name = data.get("sender_name", "Source Point")
    if not isinstance(sender_name, str) or not sender_name.strip() or len(sender_name.strip()) > 150:
        return jsonify({"success": False, "message": "Enter a sender name of 150 characters or fewer."}), 400
    sender_name = " ".join(sender_name.split())
    try:
        send_email(to=email.strip(), subject=f"A gift card from {sender_name}", template="mail/gift_card_email.html",
                   recipient_name=name.strip(), brand=card.brand, card_number=card.get_card_number(), pin=card.get_pin(),
                   denomination=card.denomination, expiry_date=card.expiry_date, custom_message=custom_message,
                   sender_name=sender_name,
                   include_default_cc=False)
    except Exception:
        current_app.logger.exception("Gift card email could not be sent")
        return jsonify({"success": False, "message": "Gift card email could not be sent."}), 502
    card.status = GiftCardStatus.SENT.value
    card.recipient_name, card.recipient_email = name.strip(), email.strip()
    card.sent_at, card.sent_by_id = datetime.utcnow(), current_user.id
    db.session.commit()
    return jsonify({"success": True, "message": "Gift card sent."})


@mobile_api_bp.post("/admin/voucher-orders/<int:order_id>/decision")
@mobile_login_required
def admin_voucher_order_decision(order_id):
    denied = _require_role("admin")
    if denied:
        return denied
    order = VoucherOrder.query.filter_by(id=order_id).with_for_update().first()
    if not order or order.status != VoucherOrderStatus.PENDING.value:
        return jsonify({"success": False, "message": "Pending voucher order not found."}), 404
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in {"approve", "reject"}:
        return jsonify({"success": False, "message": "Choose approve or reject."}), 400
    if decision == "approve":
        card = GiftCard.query.filter_by(id=order.gift_card_id).with_for_update().first()
        try:
            if not card or card.status != GiftCardStatus.AVAILABLE.value or card.is_expired:
                return jsonify({"success": False, "message": "The gift card is no longer available."}), 409
            send_email(to=order.user.email, subject=f"Your {card.brand} Gift Card from SourcePoint", template="mail/gift_card_email.html",
                       recipient_name=order.user.username, brand=card.brand, card_number=card.get_card_number(), pin=card.get_pin(),
                       denomination=card.denomination, expiry_date=card.expiry_date, custom_message='',
                       include_default_cc=False)
            card.status = GiftCardStatus.SENT.value
            card.recipient_name, card.recipient_email = order.user.username, order.user.email
            card.sent_at, card.sent_by_id = datetime.utcnow(), current_user.id
            order.status = VoucherOrderStatus.APPROVED.value
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Voucher approval email failed")
            return jsonify({"success": False, "message": "Voucher could not be approved or emailed."}), 502
    else:
        order.status = VoucherOrderStatus.REJECTED.value
        order.rejection_reason = str(data.get("reason", "")).strip()[:2000] or None
    order.reviewed_at, order.reviewed_by_id = datetime.utcnow(), current_user.id
    db.session.commit()
    log_user_action("Voucher Order " + order.status, f"Processed voucher order {order.id} from native admin")
    return jsonify({"success": True, "message": f"Voucher request {order.status.lower()}."})


def _admin_asset_payload(asset):
    return {
        "id": asset.id, "asset_code": asset.asset_code, "name": asset.name, "asset_type": asset.asset_type,
        "serial_number": asset.serial_number or "", "brand": asset.brand or "", "model_number": asset.model_number or "",
        "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
        "purchase_price": float(asset.purchase_price) if asset.purchase_price is not None else None,
        "warranty_expiry": asset.warranty_expiry.isoformat() if asset.warranty_expiry else None,
        "status": asset.status, "condition": asset.condition, "processor": asset.processor or "", "ram": asset.ram or "",
        "storage_spec": asset.storage_spec or "", "display": asset.display or "", "graphics": asset.graphics or "",
        "operating_system": asset.operating_system or "", "battery": asset.battery or "", "color": asset.color or "",
        "asset_action": asset.asset_action or "", "assigned_to_id": asset.assigned_to_id,
        "assigned_to": asset.assigned_to.username if asset.assigned_to else "", "location": asset.location or "",
        "sold_to_name": asset.sold_to_name or "", "sold_to_email": asset.sold_to_email or "",
        "sold_date": asset.sold_date.isoformat() if asset.sold_date else None,
        "sale_price": float(asset.sale_price) if asset.sale_price is not None else None,
        "share_url": url_for("public.asset_public_page", token=asset.share_token, _external=True) if asset.share_token else "",
        "notes": asset.notes or "", "terms_and_conditions": asset.terms_and_conditions or "",
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


@mobile_api_bp.get("/admin/assets")
@mobile_login_required
def admin_assets_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    search = request.args.get("q", "").strip()[:150]
    asset_type = request.args.get("type", "").strip()
    query = Asset.query
    if asset_type in {item.value for item in AssetType}:
        query = query.filter(Asset.asset_type == asset_type)
    if search:
        query = query.filter(or_(Asset.asset_code.ilike(f"%{search}%"), Asset.name.ilike(f"%{search}%")))
    assets = query.order_by(Asset.created_at.desc()).limit(500).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return jsonify({"success": True,
        "assets": [_admin_asset_payload(asset) for asset in assets], "search": search, "type_filter": asset_type,
        "users": [{"id": user.id, "username": user.username, "email": user.email} for user in users],
        "asset_types": [item.value for item in AssetType],
        "statuses": [item.value for item in AssetStatus],
        "conditions": [item.value for item in AssetCondition],
        "counts": {"total": Asset.query.count(), "active": Asset.query.filter_by(status=AssetStatus.ACTIVE.value).count(),
                   "in_storage": Asset.query.filter_by(status=AssetStatus.IN_STORAGE.value).count(),
                   "repair": Asset.query.filter_by(status=AssetStatus.UNDER_REPAIR.value).count(),
                   "sold": Asset.query.filter_by(status=AssetStatus.SOLD.value).count()}})


@mobile_api_bp.post("/admin/assets")
@mobile_login_required
def admin_create_asset():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name, asset_type = data.get("name"), data.get("asset_type")
    allowed_types = {item.value for item in AssetType}
    allowed_statuses = {item.value for item in AssetStatus}
    allowed_conditions = {item.value for item in AssetCondition}
    if not isinstance(name, str) or not name.strip() or asset_type not in allowed_types:
        return jsonify({"success": False, "message": "Enter an asset name and choose a valid asset type."}), 400
    condition = data.get("condition", AssetCondition.GOOD.value)
    status = data.get("status", AssetStatus.IN_STORAGE.value)
    if condition not in allowed_conditions or status not in allowed_statuses:
        return jsonify({"success": False, "message": "Choose a valid condition and status."}), 400
    def _date_field(value):
        return datetime.strptime(str(value), "%Y-%m-%d").date() if value else None
    try:
        asset = Asset(asset_code=f"SP-AST-{(db.session.query(func.max(Asset.id)).scalar() or 0) + 1:04d}",
                      name=name.strip()[:150], asset_type=asset_type, condition=condition, status=status,
                      serial_number=str(data.get("serial_number", "")).strip()[:200] or None,
                      brand=str(data.get("brand", "")).strip()[:100] or None,
                      model_number=str(data.get("model_number", "")).strip()[:150] or None,
                      purchase_date=_date_field(data.get("purchase_date")), warranty_expiry=_date_field(data.get("warranty_expiry")),
                      purchase_price=float(data["purchase_price"]) if data.get("purchase_price") not in (None, "") else None,
                      location=str(data.get("location", "")).strip()[:200] or None,
                      notes=str(data.get("notes", "")).strip() or None,
                      processor=str(data.get("processor", "")).strip() or None, ram=str(data.get("ram", "")).strip() or None,
                      storage_spec=str(data.get("storage_spec", "")).strip() or None, display=str(data.get("display", "")).strip() or None,
                      graphics=str(data.get("graphics", "")).strip() or None, operating_system=str(data.get("operating_system", "")).strip() or None,
                      battery=str(data.get("battery", "")).strip() or None, color=str(data.get("color", "")).strip() or None,
                      authorized_by_id=current_user.id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter valid purchase date, warranty date, and price."}), 400
    asset_action = data.get("asset_action")
    if asset_action == "sold":
        sold_email = str(data.get("sold_to_email", "")).strip()
        sold_name = str(data.get("sold_to_name", "")).strip()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", sold_email):
            return jsonify({"success": False, "message": "A valid buyer email is required for a sale."}), 400
        asset.asset_action = "sold"
        asset.status = AssetStatus.SOLD.value
        asset.sold_to_name, asset.sold_to_email = sold_name or None, sold_email
        asset.sold_date = _date_field(data.get("sold_date")) or datetime.utcnow().date()
        try:
            asset.sale_price = float(data["sale_price"]) if data.get("sale_price") not in (None, "") else None
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Enter a valid sale price."}), 400
        asset.terms_and_conditions = str(data.get("terms_and_conditions", "")).strip() or None
        asset.assigned_to_id = None
        asset.generate_share_token()
    elif data.get("assigned_to_id") not in (None, ""):
        try:
            assignee = User.query.get(int(data["assigned_to_id"]))
        except (TypeError, ValueError):
            assignee = None
        if not assignee:
            return jsonify({"success": False, "message": "Selected assignee was not found."}), 400
        asset.assigned_to_id = assignee.id
        asset.asset_action = "assigned"
        asset.status = AssetStatus.ACTIVE.value
        asset.allocation_date = datetime.utcnow().date()
        asset.sold_to_name = asset.sold_to_email = None
        asset.sold_date = asset.sale_price = None
    else:
        asset.asset_action = None
    asset.generate_share_token()
    db.session.add(asset)
    db.session.commit()
    if asset.assigned_to:
        try:
            from services.asset_email_service import send_asset_assignment_email
            send_asset_assignment_email(asset, asset.assigned_to)
        except Exception:
            current_app.logger.exception("Asset saved but assignment email failed")
    elif asset.asset_action == "sold":
        try:
            from services.asset_email_service import send_asset_sale_terms_email
            send_asset_sale_terms_email(asset)
        except Exception:
            current_app.logger.exception("Sold asset saved but terms email failed")
    log_user_action("Add Asset", f"Added asset {asset.asset_code} from native admin")
    return jsonify({"success": True, "message": "Asset created.", "asset": _admin_asset_payload(asset)}), 201


@mobile_api_bp.patch("/admin/assets/<int:asset_id>")
@mobile_login_required
def admin_update_asset(asset_id):
    denied = _require_role("admin")
    if denied:
        return denied
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"success": False, "message": "Asset not found."}), 404
    data = request.get_json(silent=True) or {}
    old_action, old_assignee_id, old_sold_email = asset.asset_action, asset.assigned_to_id, asset.sold_to_email
    string_fields = {"name": 150, "asset_type": 50, "serial_number": 200, "brand": 100, "model_number": 150,
                     "status": 30, "condition": 30, "processor": 200, "ram": 100, "storage_spec": 200,
                     "display": 200, "graphics": 200, "operating_system": 100, "battery": 100, "color": 50,
                     "location": 200, "notes": 10000}
    for field, limit in string_fields.items():
        if field in data:
            value = str(data[field]).strip()
            if field == "name" and not value:
                return jsonify({"success": False, "message": "Asset name cannot be empty."}), 400
            setattr(asset, field, value[:limit] or None if field not in {"name", "asset_type", "status", "condition"} else value[:limit])
    if asset.asset_type not in {item.value for item in AssetType} or asset.status not in {item.value for item in AssetStatus} or asset.condition not in {item.value for item in AssetCondition}:
        return jsonify({"success": False, "message": "Choose valid asset type, status, and condition."}), 400
    try:
        for field in ("purchase_date", "warranty_expiry", "sold_date"):
            if field in data:
                setattr(asset, field, datetime.strptime(str(data[field]), "%Y-%m-%d").date() if data[field] else None)
        for field in ("purchase_price", "sale_price"):
            if field in data:
                setattr(asset, field, float(data[field]) if data[field] not in (None, "") else None)
        if "assigned_to_id" in data:
            asset.assigned_to_id = int(data["assigned_to_id"]) if data["assigned_to_id"] not in (None, "") else None
            if asset.assigned_to_id:
                asset.asset_action = "assigned"
                asset.status = AssetStatus.ACTIVE.value
                asset.allocation_date = datetime.utcnow().date()
            else:
                asset.asset_action = None
        if "sold_to_name" in data:
            asset.sold_to_name = str(data["sold_to_name"]).strip() or None
        if "sold_to_email" in data:
            asset.sold_to_email = str(data["sold_to_email"]).strip() or None
        if "terms_and_conditions" in data:
            asset.terms_and_conditions = str(data["terms_and_conditions"]).strip() or None
        if data.get("asset_action") == "sold":
            if not asset.sold_to_email or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", asset.sold_to_email):
                return jsonify({"success": False, "message": "A valid buyer email is required for a sale."}), 400
            asset.asset_action = "sold"
            asset.status = AssetStatus.SOLD.value
            asset.assigned_to_id = None
            asset.allocation_date = None
            asset.sold_date = asset.sold_date or datetime.utcnow().date()
            asset.sale_price = float(data["sale_price"]) if data.get("sale_price") not in (None, "") else asset.sale_price
            asset.generate_share_token()
        elif data.get("asset_action") == "assigned" and asset.assigned_to_id:
            asset.asset_action = "assigned"
            asset.status = AssetStatus.ACTIVE.value
            asset.allocation_date = asset.allocation_date or datetime.utcnow().date()
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter valid date, price, or assignee values."}), 400
    asset.authorized_by_id = current_user.id
    db.session.commit()
    if asset.asset_action == "sold" and (old_action != "sold" or old_sold_email != asset.sold_to_email):
        try:
            from services.asset_email_service import send_asset_sale_terms_email
            send_asset_sale_terms_email(asset)
        except Exception:
            current_app.logger.exception("Sold asset updated but terms email failed")
    elif asset.asset_action == "assigned" and asset.assigned_to and old_assignee_id != asset.assigned_to_id:
        try:
            from services.asset_email_service import send_asset_assignment_email
            send_asset_assignment_email(asset, asset.assigned_to)
        except Exception:
            current_app.logger.exception("Asset assigned but notification failed")
    log_user_action("Edit Asset", f"Updated asset {asset.asset_code} from native admin")
    return jsonify({"success": True, "message": "Asset updated.", "asset": _admin_asset_payload(asset)})


@mobile_api_bp.delete("/admin/assets/<int:asset_id>")
@mobile_login_required
def admin_delete_asset(asset_id):
    denied = _require_role("admin")
    if denied:
        return denied
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"success": False, "message": "Asset not found."}), 404
    name = asset.name
    db.session.delete(asset)
    db.session.commit()
    log_user_action("Delete Asset", f"Deleted asset {name} from native admin")
    return jsonify({"success": True, "message": "Asset deleted."})


@mobile_api_bp.post("/admin/assets/<int:asset_id>/cancel")
@mobile_login_required
def admin_cancel_asset(asset_id):
    denied = _require_role("admin")
    if denied:
        return denied
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"success": False, "message": "Asset not found."}), 404
    if asset.status == AssetStatus.CANCELLED.value:
        return jsonify({"success": False, "message": "Asset is already cancelled."}), 409
    recipient_email = asset.sold_to_email if asset.asset_action == "sold" else (asset.assigned_to.email if asset.assigned_to else None)
    recipient_name = asset.sold_to_name if asset.asset_action == "sold" else (asset.assigned_to.username if asset.assigned_to else None)
    data = request.get_json(silent=True) or {}
    asset.status = AssetStatus.CANCELLED.value
    asset.cancelled_at = datetime.utcnow()
    asset.cancellation_reason = str(data.get("reason", "")).strip()[:5000] or None
    asset.share_token = None
    asset.sale_terms_email_sent_at = asset.sale_terms_accepted_at = asset.delivery_receipt_sent_at = None
    db.session.commit()
    if recipient_email:
        try:
            from services.asset_email_service import send_asset_cancellation_email
            send_asset_cancellation_email(asset, recipient_email, recipient_name or recipient_email)
        except Exception:
            current_app.logger.exception("Asset cancelled but notification email failed")
    return jsonify({"success": True, "message": "Asset cancelled."})


@mobile_api_bp.post("/admin/assets/<int:asset_id>/resend-email")
@mobile_login_required
def admin_resend_asset_email(asset_id):
    denied = _require_role("admin")
    if denied:
        return denied
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"success": False, "message": "Asset not found."}), 404
    try:
        if asset.asset_action == "sold" and asset.sold_to_email:
            if asset.sale_terms_accepted_at:
                from services.asset_email_service import send_asset_delivery_receipt_email
                sent = send_asset_delivery_receipt_email(asset)
            else:
                from services.asset_email_service import send_asset_sale_terms_email
                sent = send_asset_sale_terms_email(asset)
        elif asset.assigned_to:
            from services.asset_email_service import send_asset_assignment_email
            sent = send_asset_assignment_email(asset, asset.assigned_to)
        else:
            return jsonify({"success": False, "message": "Asset is not currently assigned or sold."}), 409
    except Exception:
        current_app.logger.exception("Asset notification resend failed")
        return jsonify({"success": False, "message": "Asset notification could not be sent."}), 502
    if not sent:
        return jsonify({"success": False, "message": "Asset notification could not be sent."}), 502
    return jsonify({"success": True, "message": "Asset notification sent."})


@mobile_api_bp.get("/admin/releases")
@mobile_login_required
def admin_releases_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    releases = AndroidAppRelease.query.order_by(AndroidAppRelease.uploaded_at.desc()).all()
    features = AppFeature.query.order_by(AppFeature.sort_order, AppFeature.id).all()
    return jsonify({"success": True, "releases": [{"id": r.id, "version_name": r.version_name, "version_code": r.version_code,
                    "filename": r.original_filename, "file_size": r.file_size, "release_notes": r.release_notes or "", "is_active": r.is_active,
                    "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
                    "uploaded_by": r.uploaded_by.username if r.uploaded_by else ""} for r in releases],
        "features": [{"id": f.id, "title": f.title, "description": f.description, "icon": f.icon, "color": f.color,
                      "sort_order": f.sort_order, "is_active": f.is_active} for f in features],
        "download_page": url_for("app_release.download_app", _external=True),
        "direct_download": url_for("app_release.download_apk", _external=True)})


@mobile_api_bp.post("/admin/releases")
@mobile_login_required
def admin_upload_release():
    denied = _require_role("admin")
    if denied:
        return denied
    file = request.files.get("apk_file")
    version_name = request.form.get("version_name", "").strip()
    version_code = request.form.get("version_code", "1").strip()
    notes = request.form.get("release_notes", "").strip()
    if not version_name or not file or not file.filename or not file.filename.lower().endswith(".apk"):
        return jsonify({"success": False, "message": "Version and an APK file are required."}), 400
    if not version_code.isdigit() or int(version_code) < 1:
        return jsonify({"success": False, "message": "Version code must be a positive integer."}), 400
    safe_version = secure_filename(version_name)
    filename = f"SourcePoint-v{safe_version}-{version_code}.apk"
    directory = os.path.join(current_app.root_path, "static", "apks")
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    file.save(filepath)
    AndroidAppRelease.query.update({"is_active": False})
    release = AndroidAppRelease(version_name=version_name[:50], version_code=int(version_code), filename=filename,
                                original_filename=f"SourcePoint-v{version_name}.apk", file_size=os.path.getsize(filepath),
                                release_notes=notes, is_active=True, uploaded_by_id=current_user.id)
    db.session.add(release)
    db.session.commit()
    log_user_action("Upload APK", f"Uploaded Android release v{version_name} from native app")
    return jsonify({"success": True, "message": "Release uploaded and activated.", "id": release.id}), 201


@mobile_api_bp.post("/admin/releases/<int:release_id>/activate")
@mobile_login_required
def admin_activate_release(release_id):
    denied = _require_role("admin")
    if denied:
        return denied
    release = AndroidAppRelease.query.get(release_id)
    if not release:
        return jsonify({"success": False, "message": "Release not found."}), 404
    AndroidAppRelease.query.update({"is_active": False})
    release.is_active = True
    db.session.commit()
    return jsonify({"success": True, "message": f"Version {release.version_name} is active."})


@mobile_api_bp.delete("/admin/releases/<int:release_id>")
@mobile_login_required
def admin_delete_release(release_id):
    denied = _require_role("admin")
    if denied:
        return denied
    release = AndroidAppRelease.query.get(release_id)
    if not release:
        return jsonify({"success": False, "message": "Release not found."}), 404
    path = os.path.join(current_app.root_path, "static", "apks", release.filename)
    was_active = release.is_active
    db.session.delete(release)
    db.session.commit()
    if os.path.isfile(path):
        os.remove(path)
    if was_active:
        latest = AndroidAppRelease.query.order_by(AndroidAppRelease.uploaded_at.desc()).first()
        if latest:
            latest.is_active = True
            db.session.commit()
    return jsonify({"success": True, "message": "Release deleted."})


@mobile_api_bp.post("/admin/releases/features")
@mobile_login_required
def admin_create_release_feature():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title, description = data.get("title"), data.get("description")
    if not isinstance(title, str) or not title.strip() or not isinstance(description, str) or not description.strip():
        return jsonify({"success": False, "message": "Feature title and description are required."}), 400
    try:
        sort_order = int(data.get("sort_order", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Sort order must be a number."}), 400
    feature = AppFeature(title=title.strip()[:120], description=description.strip(), icon=str(data.get("icon", "fa-star"))[:80],
                         color=str(data.get("color", "emerald"))[:30], sort_order=sort_order)
    db.session.add(feature)
    db.session.commit()
    return jsonify({"success": True, "message": "Download page feature added.", "id": feature.id}), 201


@mobile_api_bp.post("/admin/releases/features/<int:feature_id>/toggle")
@mobile_login_required
def admin_toggle_release_feature(feature_id):
    denied = _require_role("admin")
    if denied:
        return denied
    feature = AppFeature.query.get(feature_id)
    if not feature:
        return jsonify({"success": False, "message": "Feature not found."}), 404
    feature.is_active = not feature.is_active
    db.session.commit()
    return jsonify({"success": True, "message": "Feature visibility updated.", "is_active": feature.is_active})


@mobile_api_bp.patch("/admin/releases/features/<int:feature_id>")
@mobile_login_required
def admin_update_release_feature(feature_id):
    denied = _require_role("admin")
    if denied:
        return denied
    feature = AppFeature.query.get(feature_id)
    if not feature:
        return jsonify({"success": False, "message": "Feature not found."}), 404
    data = request.get_json(silent=True) or {}
    for key, limit in (("title", 120), ("description", 5000), ("icon", 80), ("color", 30)):
        if key in data:
            value = data[key]
            if not isinstance(value, str) or (key in {"title", "description"} and not value.strip()):
                return jsonify({"success": False, "message": f"Enter a valid {key}."}), 400
            setattr(feature, key, value.strip()[:limit])
    if "sort_order" in data:
        try:
            feature.sort_order = int(data["sort_order"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Sort order must be a number."}), 400
    db.session.commit()
    return jsonify({"success": True, "message": "Feature updated."})


@mobile_api_bp.delete("/admin/releases/features/<int:feature_id>")
@mobile_login_required
def admin_delete_release_feature(feature_id):
    denied = _require_role("admin")
    if denied:
        return denied
    feature = AppFeature.query.get(feature_id)
    if not feature:
        return jsonify({"success": False, "message": "Feature not found."}), 404
    db.session.delete(feature)
    db.session.commit()
    return jsonify({"success": True, "message": "Feature deleted."})


@mobile_api_bp.get("/admin/health")
@mobile_login_required
def admin_health_status():
    denied = _require_role("admin")
    if denied:
        return denied
    import platform
    import socket
    checks, alerts = {}, []
    overall = "HEALTHY"

    def update_overall(status, message=None):
        nonlocal overall
        if status == "CRITICAL":
            overall = "CRITICAL"
        elif status == "WARNING" and overall == "HEALTHY":
            overall = "WARNING"
        if message:
            alerts.append(message)

    try:
        import psutil
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.utcnow() - boot_time
        checks["system"] = {
            "status": "OK", "hostname": socket.gethostname(),
            "platform": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(), "python_version": platform.python_version(),
            "uptime": f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m",
            "boot_time": boot_time.isoformat(),
        }
        cpu = psutil.cpu_percent(interval=0.2)
        cpu_state = "CRITICAL" if cpu > 90 else "WARNING" if cpu > 75 else "OK"
        update_overall(cpu_state, f"CPU usage is {cpu}%" if cpu_state != "OK" else None)
        checks["cpu"] = {"status": cpu_state, "usage_percent": cpu,
                         "cores_physical": psutil.cpu_count(logical=False), "cores_logical": psutil.cpu_count(),
                         "load_average": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else []}
        memory, swap = psutil.virtual_memory(), psutil.swap_memory()
        memory_state = "CRITICAL" if memory.percent > 90 else "WARNING" if memory.percent > 80 else "OK"
        update_overall(memory_state, f"Memory usage is high at {memory.percent}%" if memory_state != "OK" else None)
        checks["memory"] = {"status": memory_state, "total_gb": round(memory.total / (1024 ** 3), 1),
                            "used_gb": round(memory.used / (1024 ** 3), 1), "available_gb": round(memory.available / (1024 ** 3), 1),
                            "usage_percent": memory.percent, "swap_total_gb": round(swap.total / (1024 ** 3), 1),
                            "swap_used_gb": round(swap.used / (1024 ** 3), 1), "swap_percent": swap.percent}
        disk = psutil.disk_usage("/")
        disk_state = "CRITICAL" if disk.percent > 90 else "WARNING" if disk.percent > 80 else "OK"
        update_overall(disk_state, f"Disk usage is high at {disk.percent}%" if disk_state != "OK" else None)
        io = psutil.disk_io_counters()
        checks["disk"] = {"status": disk_state, "total_gb": round(disk.total / (1024 ** 3), 1),
                          "used_gb": round(disk.used / (1024 ** 3), 1), "free_gb": round(disk.free / (1024 ** 3), 1),
                          "usage_percent": disk.percent,
                          "read_gb": round(io.read_bytes / (1024 ** 3), 2) if io else "N/A",
                          "write_gb": round(io.write_bytes / (1024 ** 3), 2) if io else "N/A"}
        network = psutil.net_io_counters()
        checks["network"] = {"status": "OK", "bytes_sent_gb": round(network.bytes_sent / (1024 ** 3), 2),
                             "bytes_received_gb": round(network.bytes_recv / (1024 ** 3), 2),
                             "packets_sent": network.packets_sent, "packets_received": network.packets_recv,
                             "errors_in": network.errin, "errors_out": network.errout}
        checks["top_processes"] = [{"pid": process.info.get("pid"), "name": process.info.get("name"),
                                    "cpu_percent": process.info.get("cpu_percent") or 0,
                                    "memory_percent": round(process.info.get("memory_percent") or 0, 2)}
                                   for process in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                                                         key=lambda item: item.info.get("cpu_percent") or 0, reverse=True)[:8]]
    except Exception as error:
        current_app.logger.exception("Native admin system metrics could not be read")
        checks.setdefault("system", {"status": "ERROR", "error": str(error)})

    db_started = datetime.utcnow()
    try:
        db.session.execute(db.text("SELECT 1"))
        latency = (datetime.utcnow() - db_started).total_seconds() * 1000
        checks["database"] = {"status": "WARNING" if latency > 500 else "OK", "latency_ms": round(latency, 1),
                              "total_users": User.query.count(), "total_articles": NewsArticle.query.count()}
        update_overall(checks["database"]["status"], f"Database latency is {latency:.0f} ms" if latency > 500 else None)
        try:
            checks["database"]["database_size"] = db.session.execute(db.text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar() or "N/A"
            checks["database"]["active_connections"] = db.session.execute(db.text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")).scalar()
        except Exception:
            db.session.rollback()
            checks["database"]["database_size"] = "N/A"
            checks["database"]["active_connections"] = "N/A"
    except Exception as error:
        db.session.rollback()
        checks["database"] = {"status": "CRITICAL", "error": str(error)}
        update_overall("CRITICAL", "Database connection failed")

    try:
        import redis
        redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"), socket_timeout=5)
        started = datetime.utcnow()
        redis_client.ping()
        redis_info = redis_client.info()
        checks["redis"] = {"status": "OK", "latency_ms": round((datetime.utcnow() - started).total_seconds() * 1000, 1),
                            "memory_used": redis_info.get("used_memory_human", "N/A"),
                            "connected_clients": redis_info.get("connected_clients", "N/A"),
                            "total_keys": redis_client.dbsize(), "uptime_days": redis_info.get("uptime_in_days", "N/A"),
                            "redis_version": redis_info.get("redis_version", "N/A")}
    except Exception as error:
        checks["redis"] = {"status": "CRITICAL", "error": str(error)}
        update_overall("CRITICAL", "Redis connection failed")

    try:
        import requests as http_requests
        site_url = os.environ.get("SITE_URL", "http://web:5000").rstrip("/")
        started = datetime.utcnow()
        response = http_requests.get(f"{site_url}/health", timeout=10)
        latency = (datetime.utcnow() - started).total_seconds() * 1000
        state = "OK" if response.status_code == 200 else "CRITICAL"
        if latency > 2000 and state == "OK": state = "WARNING"
        checks["application"] = {"status": state, "http_status": response.status_code, "response_time_ms": round(latency)}
        update_overall(state, f"Application /health returned HTTP {response.status_code}" if state == "CRITICAL" else None)
    except Exception as error:
        checks["application"] = {"status": "CRITICAL", "error": str(error)}
        update_overall("CRITICAL", "Application health check failed")

    return jsonify({"success": True, "status": overall, "checked_at": datetime.utcnow().isoformat(),
                    "report_time": (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%d %b %Y, %I:%M %p IST"),
                    "environment": current_app.config.get("ENV", "production"), "alerts": alerts, "checks": checks})


@mobile_api_bp.post("/admin/superscoins/adjust")
@mobile_login_required
def admin_adjust_superscoins():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        seller_id = int(data.get("seller_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a seller."}), 400
    try:
        from services.superscoins_service import SupersCoinsService
        success, message, wallet, transaction = SupersCoinsService.adjust_wallet(
            seller_id=seller_id, transaction_type=data.get("transaction_type"), amount_value=data.get("amount"),
            admin_id=current_user.id, note=str(data.get("note", "")).strip() or None,
        )
        if not success:
            db.session.rollback()
            return jsonify({"success": False, "message": message}), 400
        db.session.commit()
        try:
            send_email(to=wallet.seller.email, cc=current_user.email, subject=f"SupersCoins {transaction.transaction_type.title()} Update",
                       template="mail/superscoins_activity_email.html", seller=wallet.seller, wallet=wallet,
                       transaction=transaction, admin=current_user, now=datetime.utcnow())
        except Exception:
            current_app.logger.exception("SupersCoins balance changed but seller notification failed")
        log_user_action("SupersCoins Wallet Update", f"Adjusted wallet for {wallet.seller.username} from native admin")
        return jsonify({"success": True, "message": message, "balance": float(wallet.balance)})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native SupersCoins adjustment failed")
        return jsonify({"success": False, "message": "SupersCoins is unavailable. Check that its database migration is installed."}), 503


@mobile_api_bp.post("/admin/superscoins/invoices")
@mobile_login_required
def admin_create_superscoins_invoice():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        seller_id = int(data.get("seller_id"))
        due_date = datetime.strptime(str(data["due_date"]), "%Y-%m-%d").date() if data.get("due_date") else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Select a seller and enter a valid due date."}), 400
    try:
        from services.superscoins_service import SupersCoinsService
        success, message, invoice = SupersCoinsService.create_invoice(
            seller_id=seller_id, amount_value=data.get("amount"), admin_id=current_user.id,
            description=str(data.get("description", "")).strip(), notes=str(data.get("notes", "")).strip(),
            due_date=due_date, spending_category=str(data.get("spending_category", "")).strip() or None,
            booking_details=str(data.get("booking_details", "")).strip() or None)
        if not success:
            db.session.rollback()
            return jsonify({"success": False, "message": message}), 400
        db.session.commit()
        email_task_id = None
        try:
            from worker import send_admin_superscoins_invoice_email_task
            email_task_id = enqueue_email_job(
                send_admin_superscoins_invoice_email_task,
                invoice.id, current_user.email, current_user.username, False,
            )
        except Exception:
            current_app.logger.exception("SupersCoins invoice saved but email failed")
        log_user_action("Create SupersCoins Invoice", f"Created {invoice.invoice_number} from native admin")
        if not email_task_id:
            return jsonify({"success": True, "message": "Invoice created, but its email could not be queued. Check the email worker and retry.", "email_sent": False, "id": invoice.id}), 201
        return jsonify({"success": True, "message": "Invoice created. Email queued.", "email_status": "queued", "email_task_id": email_task_id, "id": invoice.id}), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native SupersCoins invoice creation failed")
        return jsonify({"success": False, "message": "SupersCoins invoice could not be created."}), 503


@mobile_api_bp.post("/admin/superscoins/invoices/<int:invoice_id>/send")
@mobile_login_required
def admin_send_superscoins_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = SupersCoinInvoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "SupersCoins invoice not found."}), 404
    try:
        from worker import send_admin_superscoins_invoice_email_task
        email_task_id = enqueue_email_job(
            send_admin_superscoins_invoice_email_task,
            invoice.id, current_user.email, current_user.username, False,
        )
    except Exception:
        current_app.logger.exception("SupersCoins invoice email failed")
        return jsonify({"success": False, "message": "Invoice could not be emailed."}), 502
    return jsonify({"success": True, "message": "Invoice email queued.", "email_status": "queued", "email_task_id": email_task_id}), 202


@mobile_api_bp.post("/admin/superscoins/invoices/<int:invoice_id>/mark-paid")
@mobile_login_required
def admin_mark_superscoins_invoice_paid(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = SupersCoinInvoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "SupersCoins invoice not found."}), 404
    if invoice.status == "Paid":
        return jsonify({"success": False, "message": "Invoice is already paid."}), 409
    if invoice.status == "Cancelled":
        return jsonify({"success": False, "message": "Cancelled invoices cannot be marked paid."}), 409
    invoice.status, invoice.paid_at = "Paid", datetime.utcnow()
    db.session.commit()
    try:
        from worker import send_admin_superscoins_invoice_email_task
        email_task_id = enqueue_email_job(
            send_admin_superscoins_invoice_email_task,
            invoice.id, current_user.email, current_user.username, True,
        )
    except Exception:
        current_app.logger.exception("SupersCoins invoice paid but notification failed")
        email_task_id = None
    if not email_task_id:
        current_app.logger.warning("SupersCoins invoice %s was marked paid but its email could not be queued", invoice.id)
        return jsonify({"success": True, "message": "Invoice marked paid, but the seller email could not be queued. Check the email worker and retry.", "email_sent": False})
    return jsonify({"success": True, "message": "Invoice marked paid. Seller email queued.", "email_status": "queued", "email_task_id": email_task_id}), 202


@mobile_api_bp.get("/admin/superscoins/invoices/<int:invoice_id>/download")
@mobile_login_required
def admin_download_superscoins_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = SupersCoinInvoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "SupersCoins invoice not found."}), 404
    try:
        from invoice_service import SupersCoinInvoiceGenerator
        pdf = SupersCoinInvoiceGenerator(invoice).generate_pdf()
    except Exception:
        current_app.logger.exception("Native admin could not generate SupersCoins invoice PDF")
        return jsonify({"success": False, "message": "Invoice PDF could not be generated."}), 500
    return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                     download_name=f"{invoice.invoice_number}.pdf")


@mobile_api_bp.delete("/admin/gift-cards/<int:card_id>")
@mobile_login_required
def admin_delete_gift_card(card_id):
    denied = _require_role("admin")
    if denied:
        return denied
    card = GiftCard.query.get(card_id)
    if not card:
        return jsonify({"success": False, "message": "Gift card not found."}), 404
    if VoucherOrder.query.filter_by(gift_card_id=card.id).first():
        return jsonify({"success": False, "message": "This card is referenced by a voucher order and cannot be deleted."}), 409
    db.session.delete(card)
    db.session.commit()
    return jsonify({"success": True, "message": "Gift card deleted."})


@mobile_api_bp.post("/admin/commerce/ads")
@mobile_login_required
def admin_create_ad():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name, link = data.get("name"), data.get("url")
    if not isinstance(name, str) or not name.strip() or not isinstance(link, str) or not link.startswith(("https://", "http://")):
        return jsonify({"success": False, "message": "Enter an ad name and a valid http(s) affiliate URL."}), 400
    if AffiliateAd.query.filter_by(ad_name=name.strip()).first():
        return jsonify({"success": False, "message": "An ad already uses that name."}), 409
    ad = AffiliateAd(ad_name=name.strip()[:100], affiliate_link=link.strip()[:2000])
    db.session.add(ad)
    db.session.commit()
    return jsonify({"success": True, "message": "Affiliate ad created.", "id": ad.id}), 201


@mobile_api_bp.delete("/admin/commerce/ads/<int:ad_id>")
@mobile_login_required
def admin_delete_ad(ad_id):
    denied = _require_role("admin")
    if denied:
        return denied
    ad = AffiliateAd.query.get(ad_id)
    if not ad:
        return jsonify({"success": False, "message": "Ad not found."}), 404
    db.session.delete(ad)
    db.session.commit()
    return jsonify({"success": True, "message": "Affiliate ad deleted."})


@mobile_api_bp.patch("/admin/commerce/seller-stock/<int:allocation_id>")
@mobile_login_required
def admin_update_seller_stock(allocation_id):
    denied = _require_role("admin")
    if denied:
        return denied
    allocation = SellerInventory.query.get(allocation_id)
    if not allocation:
        return jsonify({"success": False, "message": "Seller stock record not found."}), 404
    try:
        stock = int((request.get_json(silent=True) or {}).get("stock"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Stock must be a non-negative whole number."}), 400
    if stock < 0:
        return jsonify({"success": False, "message": "Stock cannot be negative."}), 400
    allocation.stock = stock
    db.session.commit()
    return jsonify({"success": True, "message": "Seller stock updated."})


@mobile_api_bp.delete("/admin/commerce/seller-stock/<int:allocation_id>")
@mobile_login_required
def admin_delete_seller_stock(allocation_id):
    denied = _require_role("admin")
    if denied:
        return denied
    allocation = SellerInventory.query.get(allocation_id)
    if not allocation:
        return jsonify({"success": False, "message": "Seller stock record not found."}), 404
    db.session.delete(allocation)
    db.session.commit()
    return jsonify({"success": True, "message": "Seller stock allocation deleted."})


@mobile_api_bp.post("/admin/commerce/invoices")
@mobile_login_required
def admin_create_commerce_invoice():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name, email = data.get("recipient_name"), data.get("recipient_email")
    invoice_type = str(data.get("invoice_type", "ecommerce")).strip().lower()
    if invoice_type not in {"ecommerce", "bus", "hotel", "flight"}:
        return jsonify({"success": False, "message": "Choose a valid invoice type."}), 400
    raw_items = data.get("items")
    if raw_items is None:
        raw_items = [{"description": data.get("description"), "quantity": 1, "price": data.get("amount")}]
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > 50:
        return jsonify({"success": False, "message": "Add at least one invoice line item."}), 400
    invoice_items = []
    subtotal = 0.0
    try:
        for row in raw_items:
            description = row.get("description")
            quantity = int(row.get("quantity", 1))
            price = float(row.get("price"))
            if not isinstance(description, str) or not description.strip() or len(description.strip()) > 200 or quantity < 1 or price < 0:
                raise ValueError
            invoice_items.append((description.strip(), quantity, price))
            subtotal += quantity * price
        tax = float(data.get("tax", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        return jsonify({"success": False, "message": "Enter valid invoice descriptions, quantities, prices, and tax."}), 400
    if not isinstance(name, str) or not name.strip() or not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()) or tax < 0:
        return jsonify({"success": False, "message": "Enter a recipient and valid email, with non-negative tax."}), 400
    try:
        due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date() if data.get("due_date") else None
    except ValueError:
        return jsonify({"success": False, "message": "Enter a due date in YYYY-MM-DD format."}), 400
    invoice = Invoice(invoice_number=f"SP-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}", recipient_name=name.strip()[:100],
                      recipient_email=email.strip()[:120], recipient_user_id=invoice_recipient_id(email), invoice_type=invoice_type,
                      subtotal=subtotal, tax=tax, total_amount=subtotal + tax,
                      amount_paid=0, status=InvoiceStatus.UNPAID.value, admin_id=current_user.id,
                      due_date=due_date, notes=str(data.get("notes", "")).strip() or None,
                      payment_details=str(data.get("payment_details", "")).strip() or None,
                      bill_to_address=str(data.get("bill_to_address", "")).strip() or None,
                      ship_to_address=str(data.get("ship_to_address", "")).strip() or None,
                      order_id=str(data.get("order_id", data.get("booking_reference", ""))).strip() or None,
                      booking_details=data.get("booking_details") if isinstance(data.get("booking_details"), dict) else {})
    invoice.items.extend(InvoiceItem(description=description, quantity=quantity, price=price)
                         for description, quantity, price in invoice_items)
    db.session.add(invoice)
    db.session.commit()
    email_task_id = None
    try:
        from worker import send_admin_commerce_invoice_email_task
        email_task_id = enqueue_email_job(
            send_admin_commerce_invoice_email_task, invoice.id, [invoice.recipient_email], "resend",
        )
    except Exception:
        current_app.logger.exception("Invoice saved but PDF email delivery failed")
    if not email_task_id:
        message = "Invoice created, but its email could not be queued. Check the email worker and retry."
        return jsonify({"success": True, "message": message, "email_sent": False, "id": invoice.id}), 201
    return jsonify({"success": True, "message": "Invoice created. Email queued.", "email_status": "queued", "email_task_id": email_task_id, "id": invoice.id}), 201


@mobile_api_bp.patch("/admin/commerce/invoices/<int:invoice_id>")
@mobile_login_required
def admin_update_commerce_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    was_paid = invoice.status == InvoiceStatus.PAID.value
    data = request.get_json(silent=True) or {}
    for field, max_length in (("recipient_name", 100), ("recipient_email", 120), ("notes", 10000),
                              ("payment_details", 10000), ("bill_to_address", 5000), ("ship_to_address", 5000),
                              ("order_id", 100)):
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, str):
                return jsonify({"success": False, "message": f"Invalid {field.replace('_', ' ')}."}), 400
            setattr(invoice, field, value.strip()[:max_length] or None if isinstance(value, str) else None)
    if "recipient_email" in data and invoice.recipient_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", invoice.recipient_email):
        return jsonify({"success": False, "message": "Enter a valid recipient email."}), 400
    if not invoice.recipient_name or not invoice.recipient_name.strip() or not invoice.recipient_email or not invoice.recipient_email.strip():
        return jsonify({"success": False, "message": "Recipient name and email are required."}), 400
    if "recipient_email" in data:
        invoice.recipient_user_id = invoice_recipient_id(invoice.recipient_email)
    if "due_date" in data:
        try:
            invoice.due_date = datetime.strptime(str(data["due_date"]), "%Y-%m-%d").date() if data["due_date"] else None
        except ValueError:
            return jsonify({"success": False, "message": "Enter a valid due date."}), 400
    if "booking_details" in data:
        if not isinstance(data["booking_details"], dict):
            return jsonify({"success": False, "message": "Booking details must be an object."}), 400
        invoice.booking_details = data["booking_details"]
    if "items" in data:
        rows = data["items"]
        if not isinstance(rows, list) or not rows or len(rows) > 50:
            return jsonify({"success": False, "message": "Add at least one invoice item."}), 400
        normalized, subtotal = [], 0.0
        try:
            for row in rows:
                description, quantity, price = row.get("description"), int(row.get("quantity", 1)), float(row.get("price"))
                if not isinstance(description, str) or not description.strip() or quantity < 1 or price < 0:
                    raise ValueError
                normalized.append((description.strip()[:200], quantity, price))
                subtotal += quantity * price
            tax = float(data.get("tax", invoice.tax or 0))
            if tax < 0:
                raise ValueError
        except (TypeError, ValueError, AttributeError):
            return jsonify({"success": False, "message": "Enter valid descriptions, quantities, prices, and tax."}), 400
        new_total = subtotal + tax
        if new_total < float(invoice.amount_paid or 0) - 0.01:
            return jsonify({"success": False, "message": "Invoice total cannot be below the amount already paid."}), 409
        invoice.subtotal, invoice.tax, invoice.total_amount = subtotal, tax, new_total
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        for description, quantity, price in normalized:
            db.session.add(InvoiceItem(invoice_id=invoice.id, description=description, quantity=quantity, price=price))
    if "status" in data:
        if data["status"] not in {item.value for item in InvoiceStatus}:
            return jsonify({"success": False, "message": "Choose a valid invoice status."}), 400
        invoice.status = data["status"]
        if invoice.status == InvoiceStatus.PAID.value:
            invoice.amount_paid = invoice.total_amount
    if "amount_paid" in data:
        try:
            paid = float(data["amount_paid"])
            if paid < 0 or paid > float(invoice.total_amount):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Payment amount must be between zero and invoice total."}), 400
        invoice.amount_paid = paid
        invoice.status = InvoiceStatus.PAID.value if paid >= float(invoice.total_amount) else InvoiceStatus.UNPAID.value
    became_paid = not was_paid and invoice.status == InvoiceStatus.PAID.value
    db.session.commit()
    log_user_action("Update Invoice", f"Updated invoice {invoice.invoice_number} from native admin")
    should_email = became_paid or bool(data.get("send_email"))
    email_task_id = None
    if should_email:
        try:
            if became_paid:
                email_task_id = send_email(
                    to=invoice.recipient_email,
                    subject=f"Payment Receipt: Invoice #{invoice.invoice_number}",
                    template="mail/payment_received.html", recipient_name=invoice.recipient_name,
                    invoice=invoice, total_amount=invoice.total_amount,
                    return_task_id=True, require_worker=True,
                )
            else:
                from worker import send_admin_commerce_invoice_email_task
                email_task_id = enqueue_email_job(
                    send_admin_commerce_invoice_email_task, invoice.id, [invoice.recipient_email], "updated",
                )
        except Exception:
            current_app.logger.exception("Invoice updated but notification email failed")
            email_task_id = None
    if should_email and not email_task_id:
        message = "Invoice was saved, but its email could not be queued. Check the email worker and retry."
    elif became_paid:
        message = "Invoice marked paid. Receipt email queued."
    elif email_task_id:
        message = "Invoice updated. Email queued."
    else:
        message = "Invoice updated."
    result = {"success": True, "message": message}
    if email_task_id:
        result.update({"email_status": "queued", "email_task_id": email_task_id})
    elif should_email:
        result["email_sent"] = False
    return jsonify(result)


@mobile_api_bp.post("/admin/commerce/invoices/<int:invoice_id>/payments")
@mobile_login_required
def admin_record_invoice_payment(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid payment amount."}), 400
    pending = float(invoice.total_amount or 0) - float(invoice.amount_paid or 0)
    if amount <= 0 or amount > pending + 0.01 or invoice.status in {InvoiceStatus.CANCELLED.value, InvoiceStatus.REFUNDED.value}:
        return jsonify({"success": False, "message": "Payment must be positive and no more than the current balance."}), 400
    invoice.amount_paid = min(float(invoice.total_amount), float(invoice.amount_paid or 0) + amount)
    payment = InvoicePayment(invoice_id=invoice.id, amount=amount,
                             note=str(data.get("note", "")).strip()[:5000] or None,
                             recorded_by_id=current_user.id)
    db.session.add(payment)
    if invoice.amount_paid >= float(invoice.total_amount) - 0.01:
        invoice.amount_paid = invoice.total_amount
        invoice.status = InvoiceStatus.PAID.value
        if invoice.order_id:
            order = Order.query.filter_by(order_number=invoice.order_id).first()
            if order and CommerceService.normalize_order_status(order.status) != OrderStatus.DELIVERED.value and not CommerceService.is_restock_status(order.status):
                order.status = OrderStatus.PAYMENT_RECEIVED.value
    else:
        invoice.status = InvoiceStatus.UNPAID.value
    db.session.commit()
    log_user_action("Record Payment", f"Recorded payment of {amount:.2f} for invoice {invoice.invoice_number}")
    email_task_id = None
    try:
        email_task_id = send_email(to=invoice.recipient_email, subject=f"Payment Recorded: Invoice #{invoice.invoice_number}",
                   template="mail/partial_payment_received.html", recipient_name=invoice.recipient_name,
                   invoice_number=invoice.invoice_number, payment_amount=amount, amount_paid=float(invoice.amount_paid),
                   total_amount=float(invoice.total_amount), pending_amount=max(0, float(invoice.total_amount) - float(invoice.amount_paid)),
                   admin_note=payment.note or "", return_task_id=True, require_worker=True)
    except Exception:
        current_app.logger.exception("Invoice payment saved but recipient email failed")
    message = "Payment recorded. Receipt email queued." if email_task_id else "Payment recorded, but its email could not be queued. Check the email worker and retry."
    response = {"success": True, "message": message,
                "amount_paid": float(invoice.amount_paid), "pending_amount": float(invoice.pending_amount), "status": invoice.status}
    if email_task_id:
        response.update({"email_status": "queued", "email_task_id": email_task_id})
    else:
        response["email_sent"] = False
    return jsonify(response)


@mobile_api_bp.post("/admin/commerce/invoices/<int:invoice_id>/refunds")
@mobile_login_required
def admin_refund_commerce_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid refund amount."}), 400
    if amount <= 0 or amount > invoice.refundable_amount + 0.01:
        return jsonify({"success": False, "message": "Refund amount must not exceed the refundable amount."}), 400
    refund_type = str(data.get("refund_type", "rupees")).strip().lower()
    if refund_type not in {"rupees", "supercoins"}:
        return jsonify({"success": False, "message": "Choose rupees or SupersCoins."}), 400
    reason = str(data.get("reason", "")).strip()[:5000]
    if refund_type == "supercoins":
        recipient = User.query.filter(func.lower(User.email) == invoice.recipient_email.lower()).first()
        if not recipient:
            return jsonify({"success": False, "message": "No SourcePoint account matches this invoice recipient."}), 400
        try:
            from services.superscoins_service import SupersCoinsService
            success, message, wallet, transaction = SupersCoinsService.adjust_wallet(
                seller_id=recipient.id, transaction_type="credit", amount_value=amount,
                admin_id=current_user.id, note=f"Refund for Invoice #{invoice.invoice_number}" + (f" — {reason}" if reason else ""),
                reference_type="invoice_refund", reference_id=invoice.id)
            if not success:
                db.session.rollback()
                return jsonify({"success": False, "message": message}), 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("SupersCoins invoice refund could not be applied")
            return jsonify({"success": False, "message": "SupersCoins wallet is unavailable for this recipient."}), 503
    if invoice.status == InvoiceStatus.PAID.value and float(invoice.amount_paid or 0) == 0:
        invoice.amount_paid = invoice.net_collected_amount
    refund = InvoiceRefund(invoice_id=invoice.id, amount=amount, refund_type=refund_type,
                           reason=reason or None, recorded_by_id=current_user.id)
    db.session.add(refund)
    invoice.amount_paid = max(0, float(invoice.amount_paid or 0) - amount)
    invoice.amount_refunded = float(invoice.amount_refunded or 0) + amount
    if invoice.amount_paid <= 0.01:
        invoice.status = InvoiceStatus.REFUNDED.value
    elif invoice.status == InvoiceStatus.PAID.value and invoice.amount_paid < float(invoice.total_amount) - 0.01:
        invoice.status = InvoiceStatus.UNPAID.value
    db.session.commit()
    log_user_action("Process Refund", f"Refunded {amount:.2f} ({refund_type}) for invoice {invoice.invoice_number}")
    try:
        email_task_id = send_email(to=invoice.recipient_email, subject=f"Refund Processed: Invoice #{invoice.invoice_number}",
                   template="mail/refund_processed.html", recipient_name=invoice.recipient_name,
                   invoice_number=invoice.invoice_number, refund_amount=amount, refund_type=refund_type,
                   supercoin_credited=refund_type == "supercoins", total_refunded=float(invoice.amount_refunded),
                   amount_paid=float(invoice.amount_paid), total_amount=float(invoice.total_amount),
                   pending_amount=max(0, float(invoice.total_amount) - float(invoice.amount_paid)), reason=reason,
                   return_task_id=True, require_worker=True)
    except Exception:
        current_app.logger.exception("Invoice refund saved but recipient email failed")
    message = "Invoice refund recorded. Email queued." if email_task_id else "Invoice refund recorded, but its email could not be queued. Check the email worker and retry."
    response = {"success": True, "message": message, "status": invoice.status}
    if email_task_id:
        response.update({"email_status": "queued", "email_task_id": email_task_id})
    else:
        response["email_sent"] = False
    return jsonify(response)


@mobile_api_bp.post("/admin/commerce/invoices/<int:invoice_id>/send")
@mobile_login_required
def admin_send_commerce_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    data = request.get_json(silent=True) or {}
    recipients = data.get("recipients") or [invoice.recipient_email]
    if isinstance(recipients, str):
        recipients = [value.strip() for value in recipients.split(",") if value.strip()]
    if not isinstance(recipients, list) or not recipients or any(not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()) for email in recipients):
        return jsonify({"success": False, "message": "Enter one or more valid recipient email addresses."}), 400
    try:
        from worker import send_admin_commerce_invoice_email_task
        email_task_id = enqueue_email_job(
            send_admin_commerce_invoice_email_task,
            invoice.id, list(dict.fromkeys(email.strip() for email in recipients)), "resend",
        )
    except Exception:
        current_app.logger.exception("Native admin could not resend invoice")
        return jsonify({"success": False, "message": "Invoice could not be emailed."}), 502
    return jsonify({"success": True, "message": "Invoice email queued.", "email_status": "queued", "email_task_id": email_task_id}), 202


@mobile_api_bp.post("/admin/commerce/invoices/<int:invoice_id>/remind")
@mobile_login_required
def admin_remind_commerce_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    if invoice.status in {InvoiceStatus.PAID.value, InvoiceStatus.REFUNDED.value, InvoiceStatus.CANCELLED.value}:
        return jsonify({"success": False, "message": "This invoice does not have a payable balance."}), 409
    try:
        from worker import send_admin_commerce_invoice_email_task
        email_task_id = enqueue_email_job(
            send_admin_commerce_invoice_email_task, invoice.id, [invoice.recipient_email], "reminder",
        )
    except Exception:
        current_app.logger.exception("Native admin could not send invoice reminder")
        return jsonify({"success": False, "message": "Reminder could not be emailed."}), 502
    return jsonify({"success": True, "message": "Payment reminder queued.", "email_status": "queued", "email_task_id": email_task_id}), 202


@mobile_api_bp.delete("/admin/commerce/invoices/<int:invoice_id>")
@mobile_login_required
def admin_delete_commerce_invoice(invoice_id):
    denied = _require_role("admin")
    if denied:
        return denied
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    number = invoice.invoice_number
    db.session.delete(invoice)
    db.session.commit()
    log_user_action("Delete Invoice", f"Deleted invoice {number} from native admin")
    return jsonify({"success": True, "message": f"Invoice {number} deleted."})


@mobile_api_bp.post("/admin/commerce/rollback/<int:request_id>/decision")
@mobile_login_required
def admin_decide_inventory_rollback(request_id):
    denied = _require_role("admin")
    if denied:
        return denied
    rollback = InventoryRollbackRequest.query.get(request_id)
    if not rollback or rollback.status != RollbackRequestStatus.PENDING.value:
        return jsonify({"success": False, "message": "Pending rollback request not found."}), 404
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in {"approve", "reject"}:
        return jsonify({"success": False, "message": "Choose approve or reject."}), 400
    if decision == "approve":
        inventory = rollback.seller_inventory
        if not inventory or inventory.stock < rollback.quantity:
            return jsonify({"success": False, "message": "Seller stock is lower than the requested return quantity."}), 409
        inventory.stock -= rollback.quantity
        rollback.product.stock += rollback.quantity
        rollback.status = RollbackRequestStatus.APPROVED.value
    else:
        rollback.status = RollbackRequestStatus.REJECTED.value
    rollback.admin_id = current_user.id
    rollback.admin_note = str(data.get("admin_note", "")).strip()[:2000] or None
    rollback.response_date = datetime.utcnow()
    db.session.commit()
    try:
        send_email(to=rollback.seller.email, subject=f"Rollback Request {rollback.status}: {rollback.product.name}",
                   template="mail/rollback_status_update.html", rollback_req=rollback, product=rollback.product,
                   status=rollback.status, now=datetime.utcnow())
    except Exception:
        current_app.logger.exception("Rollback decision saved but seller notification failed")
    log_user_action(f"{rollback.status} Rollback", f"Processed rollback request {rollback.request_number} from native admin")
    return jsonify({"success": True, "message": f"Rollback request {rollback.status.lower()}."})


# Native admin equivalents for the website's remaining administration pages.
@mobile_api_bp.get("/admin/activity")
@mobile_login_required
def admin_activity_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    query = ActivityLog.query.options(joinedload(ActivityLog.user))
    action = request.args.get("action", "").strip()
    search = request.args.get("q", "").strip()
    user_id = request.args.get("user_id", "").strip()
    after_id = request.args.get("after_id", type=int)
    start_value, end_value = request.args.get("start_date", "").strip(), request.args.get("end_date", "").strip()
    try:
        if start_value:
            query = query.filter(ActivityLog.timestamp >= datetime.strptime(start_value, "%Y-%m-%d"))
        if end_value:
            query = query.filter(ActivityLog.timestamp < datetime.strptime(end_value, "%Y-%m-%d") + timedelta(days=1))
        if user_id:
            query = query.filter(ActivityLog.user_id == int(user_id))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Use valid YYYY-MM-DD dates and user IDs."}), 400
    if action:
        query = query.filter(ActivityLog.action.ilike(f"%{action[:100]}%"))
    if search:
        query = query.filter(or_(ActivityLog.action.ilike(f"%{search[:150]}%"), ActivityLog.details.ilike(f"%{search[:150]}%")))
    if after_id:
        query = query.filter(ActivityLog.id > after_id)
    logs = query.order_by(ActivityLog.id.desc()).limit(50 if after_id else 100).all()
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    return jsonify({
        "success": True,
        "stats": {
            "total": ActivityLog.query.count(),
            "today": ActivityLog.query.filter(ActivityLog.timestamp >= today_start).count(),
            "active_users_today": db.session.query(func.count(func.distinct(ActivityLog.user_id))).filter(ActivityLog.timestamp >= today_start).scalar() or 0,
            "recent_logins": ActivityLog.query.filter(ActivityLog.action.ilike("%login%"), ActivityLog.timestamp >= today_start).count(),
        },
        "users": [{"id": user.id, "username": user.username, "role": user.role} for user in User.query.order_by(User.username).limit(500).all()],
        "logs": [{"id": row.id, "user_id": row.user_id, "username": row.user.username if row.user else "Unknown",
                  "role": row.user.role if row.user else "", "action": row.action or "", "details": row.details or "",
                  "ip_address": row.ip_address or "", "timestamp": row.timestamp.isoformat() if row.timestamp else ""} for row in logs],
    })


@mobile_api_bp.get("/admin/newsletter")
@mobile_login_required
def admin_newsletter_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    status = request.args.get("status", "unsent").strip().lower()
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "newest").strip().lower()
    page_number = max(1, request.args.get("page", 1, type=int))
    query = NewsArticle.query
    if status == "unsent":
        query = query.filter_by(is_sent=False)
    elif status == "sent":
        query = query.filter_by(is_sent=True)
    if search:
        query = query.filter(or_(NewsArticle.title.ilike(f"%{search[:150]}%"), NewsArticle.source_name.ilike(f"%{search[:150]}%")))
    total = query.count()
    if sort == "oldest":
        query = query.order_by(NewsArticle.published_at.asc().nullslast(), NewsArticle.fetched_at.asc())
    elif sort == "source":
        query = query.order_by(NewsArticle.source_name.asc().nullslast(), NewsArticle.published_at.desc().nullslast())
    elif sort == "title":
        query = query.order_by(NewsArticle.title.asc())
    else:
        sort = "newest"
        query = query.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())
    articles = query.offset((page_number - 1) * 50).limit(50).all()
    return jsonify({"success": True, "total": total, "page": page_number, "sort": sort,
        "stats": {"total_articles": NewsArticle.query.count(), "unsent": NewsArticle.query.filter_by(is_sent=False).count(),
                  "sent": NewsArticle.query.filter_by(is_sent=True).count(),
                  "subscribers": User.query.filter(User.email.isnot(None), User.email != "", User.newsletter_subscribed.is_(True)).count()},
        "articles": [{**_public_article_payload(article), "is_sent": bool(article.is_sent)} for article in articles]})


@mobile_api_bp.post("/admin/newsletter/send")
@mobile_login_required
def admin_send_newsletter():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    raw_ids = data.get("article_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return jsonify({"success": False, "message": "Select at least one article."}), 400
    try:
        article_ids = list(dict.fromkeys(int(value) for value in raw_ids))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "One or more selected article IDs are invalid."}), 400
    if len(article_ids) > 50:
        return jsonify({"success": False, "message": "Send at most 50 newsletter articles at a time."}), 400
    count = NewsArticle.query.filter(NewsArticle.id.in_(article_ids)).count()
    if count != len(article_ids):
        return jsonify({"success": False, "message": "One or more selected articles no longer exist."}), 404
    try:
        from worker import send_manual_newsletter_task
        send_manual_newsletter_task.delay(article_ids)
    except Exception:
        current_app.logger.exception("Native admin could not dispatch newsletter task")
        return jsonify({"success": False, "message": "Newsletter queue is unavailable; no newsletter was sent."}), 503
    log_user_action("Send Manual Newsletter", f"Triggered native admin send for {len(article_ids)} articles")
    return jsonify({"success": True, "message": f"Newsletter queued for {len(article_ids)} article(s)."})


@mobile_api_bp.get("/admin/commerce/rollback/terms")
@mobile_login_required
def admin_rollback_terms_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    active = RollbackTermsService.ensure_active_terms(created_by_id=current_user.id)
    sellers = User.query.filter_by(role=UserRole.SELLER.value).order_by(User.username).all()
    decisions = InventoryRollbackTermsDecision.query.filter_by(terms_id=active.id).all()
    by_seller = {decision.seller_id: decision for decision in decisions}
    history = InventoryRollbackTermsDecision.query.options(joinedload(InventoryRollbackTermsDecision.seller),
        joinedload(InventoryRollbackTermsDecision.terms)).order_by(InventoryRollbackTermsDecision.decided_at.desc()).limit(100).all()
    versions = InventoryRollbackTerms.query.order_by(InventoryRollbackTerms.version.desc()).limit(50).all()
    return jsonify({"success": True,
        "active": {"id": active.id, "version": active.version, "title": active.title, "content": active.content,
                   "created_at": active.created_at.isoformat() if active.created_at else ""},
        "sellers": [{"id": seller.id, "username": seller.username, "email": seller.email or "",
                     "decision": by_seller[seller.id].decision if seller.id in by_seller else "Pending",
                     "decided_at": by_seller[seller.id].decided_at.isoformat() if seller.id in by_seller and by_seller[seller.id].decided_at else ""} for seller in sellers],
        "versions": [{"id": row.id, "version": row.version, "title": row.title, "active": row.is_active,
                      "created_at": row.created_at.isoformat() if row.created_at else ""} for row in versions],
        "history": [{"seller": row.seller.username if row.seller else "Unknown", "email": row.seller.email if row.seller else "",
                     "decision": row.decision, "version": row.terms.version if row.terms else 0,
                     "decided_at": row.decided_at.isoformat() if row.decided_at else "", "ip_address": row.ip_address or ""} for row in history]})


@mobile_api_bp.post("/admin/commerce/rollback/terms")
@mobile_login_required
def admin_publish_rollback_terms():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    title, content = data.get("title", ""), data.get("content", "")
    if not isinstance(title, str) or not isinstance(content, str) or not content.strip():
        return jsonify({"success": False, "message": "Enter a title and terms content."}), 400
    if len(title) > 150 or len(content) > 100_000:
        return jsonify({"success": False, "message": "Title or terms content is too long."}), 413
    try:
        terms = RollbackTermsService.publish_new_terms(title, content, current_user.id)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native admin could not publish rollback terms")
        return jsonify({"success": False, "message": "Rollback terms could not be published."}), 500
    log_user_action("Update Rollback Terms", f"Published native admin rollback terms v{terms.version}")
    return jsonify({"success": True, "message": f"Rollback terms v{terms.version} published; sellers must accept this version.",
                    "version": terms.version, "id": terms.id})


@mobile_api_bp.get("/admin/learning/content")
@mobile_login_required
def admin_learning_content_workspace():
    denied = _require_role("admin")
    if denied:
        return denied
    rows = LearningContent.query.filter(LearningContent.id.in_(LEARNING_LANGUAGES)).order_by(LearningContent.id).all()
    return jsonify({"success": True, "content": [{"language": row.id, "html": row.content or "",
        "last_updated": row.last_updated.isoformat() if row.last_updated else ""} for row in rows]})


@mobile_api_bp.put("/admin/learning/content/<string:language>")
@mobile_login_required
def admin_update_learning_content(language):
    denied = _require_role("admin")
    if denied:
        return denied
    language = language.strip().lower()
    if language not in LEARNING_LANGUAGES:
        return jsonify({"success": False, "message": "Choose a supported learning page."}), 400
    data = request.get_json(silent=True) or {}
    content = data.get("content")
    if not isinstance(content, str) or not content.strip() or len(content) > 500_000:
        return jsonify({"success": False, "message": "Learning page content is required and must be under 500 KB."}), 400
    row = LearningContent.query.get(language)
    if not row:
        return jsonify({"success": False, "message": "Learning page was not found."}), 404
    row.content = content
    db.session.commit()
    log_user_action("Update Learning Content", f"Updated {language.upper()} learning page from native admin")
    return jsonify({"success": True, "message": f"{language.upper()} learning page saved."})


@mobile_api_bp.post("/admin/communications/maintenance")
@mobile_login_required
def admin_send_maintenance_notice():
    denied = _require_role("admin")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()
    start_time = str(data.get("start_time", "")).strip()[:100]
    end_time = str(data.get("end_time", "")).strip()[:100]
    if not reason:
        return jsonify({"success": False, "message": "Provide a maintenance reason or description."}), 400
    recipients = User.query.filter(User.email.isnot(None), User.email != "").order_by(User.id).all()
    sent, failed = 0, 0
    for user in recipients:
        try:
            send_email(to=user.email, subject="⚠️ SourcePoint — Scheduled Maintenance Notice",
                       template="mail/maintenance_email.html", user=user, start_time=start_time or None,
                       end_time=end_time or None, reason=reason, now=datetime.utcnow())
            sent += 1
        except Exception:
            failed += 1
            current_app.logger.exception("Native admin maintenance notice failed for user %s", user.id)
    log_user_action("Maintenance Notification", f"Sent maintenance notice to {sent} users; {failed} failed")
    return jsonify({"success": failed == 0, "message": f"Maintenance notice sent to {sent} users; {failed} failed.",
                    "sent": sent, "failed": failed})


@mobile_api_bp.post("/admin/health/report")
@mobile_login_required
def admin_queue_health_report():
    denied = _require_role("admin")
    if denied:
        return denied
    try:
        from worker import server_health_check_task
        server_health_check_task.delay()
    except Exception:
        current_app.logger.exception("Native admin could not queue server health report")
        return jsonify({"success": False, "message": "Health-report queue is unavailable."}), 503
    log_user_action("Run Health Check", "Queued a server health report from native admin")
    return jsonify({"success": True, "message": "Health check report will be emailed shortly."})


@mobile_api_bp.post("/admin/emi/import")
@mobile_login_required
def admin_import_emi_schedule():
    denied = _require_role("admin")
    if denied:
        return denied
    upload = request.files.get("schedule_file")
    title = request.form.get("title", "").strip()
    try:
        borrower_id = int(request.form.get("borrower_id", ""))
        lender_id = int(request.form.get("lender_id", ""))
        reminder_days = int(request.form.get("reminder_days", "3"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Choose a borrower, lender, and reminder interval."}), 400
    if not title or len(title) > 150 or borrower_id == lender_id or not upload or not upload.filename:
        return jsonify({"success": False, "message": "Enter a title, choose different borrower and lender accounts, and select a schedule file."}), 400
    if not 0 <= reminder_days <= 90:
        return jsonify({"success": False, "message": "Reminder days must be from 0 to 90."}), 400
    borrower = User.query.filter(User.id == borrower_id, User.role != UserRole.ADMIN.value).first()
    lender = User.query.filter(User.id == lender_id, User.role != UserRole.ADMIN.value).first()
    if not borrower or not lender:
        return jsonify({"success": False, "message": "Borrower or lender account was not found."}), 404
    filename = secure_filename(upload.filename).lower()
    if not filename.endswith((".csv", ".pdf")):
        return jsonify({"success": False, "message": "Choose a CSV or PDF EMI schedule."}), 400
    content = upload.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        return jsonify({"success": False, "message": "EMI schedule must be 10 MB or smaller."}), 413
    payments, processing_fee = [], 0.0
    try:
        if filename.endswith(".csv"):
            reader = csv.DictReader(content.decode("utf-8-sig").splitlines())
            headers = {str(key or "").strip().lower(): key for key in (reader.fieldnames or [])}
            if not {"date", "amount"}.issubset(headers):
                return jsonify({"success": False, "message": "CSV header must include Date and Amount; Description is optional."}), 400
            for row_number, row in enumerate(reader, 2):
                if row_number > 1002:
                    return jsonify({"success": False, "message": "EMI import is limited to 1,000 rows."}), 400
                try:
                    amount = float(str(row.get(headers["amount"]) or "0").replace(",", "").strip())
                    description = str(row.get(headers.get("description")) or f"Installment for {title}").strip()
                    if "processing fee" in description.lower():
                        processing_fee += amount
                        continue
                    date_text = str(row.get(headers["date"]) or "").strip()
                    try:
                        due_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                    except ValueError:
                        due_date = datetime.strptime(date_text, "%d/%m/%Y").date()
                    if amount > 0 and description:
                        payments.append({"due_date": due_date, "amount": amount, "description": description[:200]})
                except (TypeError, ValueError):
                    continue
        else:
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(BytesIO(content))
                extracted = "\n".join((page.extract_text() or "") for page in pdf_reader.pages)
            except Exception:
                current_app.logger.exception("Could not parse native admin EMI PDF")
                return jsonify({"success": False, "message": "Could not read the EMI schedule PDF."}), 400
            date_number = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
            date_text = re.compile(r"\b(\d{1,2})[\s/-]*([A-Za-z]{3})[\s/-]*(\d{4})\b")
            fee_pattern = re.compile(r"Processing\s*Fee\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.?\d*)", re.IGNORECASE)
            for line in extracted.splitlines():
                line = line.strip()
                if not line or "txn date" in line.lower() or "transaction date" in line.lower():
                    continue
                fee = fee_pattern.search(line)
                if fee:
                    try:
                        processing_fee += float(fee.group(1).replace(",", ""))
                    except ValueError:
                        pass
                    continue
                due_date, end_index = None, 0
                text_match = date_text.search(line)
                if text_match:
                    try:
                        day, month, year = text_match.groups()
                        due_date = datetime.strptime(f"{day}-{month}-{year}", "%d-%b-%Y").date()
                        end_index = text_match.end()
                    except ValueError:
                        pass
                if due_date is None:
                    numeric = date_number.search(line)
                    if numeric:
                        try:
                            day, month, year = numeric.groups()
                            year = "20" + year if len(year) == 2 else year
                            due_date = datetime(int(year), int(month), int(day)).date()
                            end_index = numeric.end()
                        except ValueError:
                            pass
                if due_date:
                    amounts = re.findall(r"(\d{1,3}(?:,\d{3})*\.\d{2})", line[end_index:])
                    if amounts:
                        try:
                            amount = float(amounts[0].replace(",", ""))
                            if amount > 0:
                                payments.append({"due_date": due_date, "amount": amount, "description": f"Installment for {title}"})
                        except ValueError:
                            pass
        if not payments:
            return jsonify({"success": False, "message": "No valid EMI payment records were found."}), 400
        payments.sort(key=lambda item: item["due_date"])
        if processing_fee > 0:
            payments[0]["amount"] += processing_fee
            payments[0]["description"] = (payments[0]["description"] + f" + Processing fee ({processing_fee:g})")[:200]
        total = sum(item["amount"] for item in payments)
        plan = EMIPlan(title=title, borrower_id=borrower.id, lender_id=lender.id, total_principal=total)
        db.session.add(plan)
        db.session.flush()
        for index, item in enumerate(payments, 1):
            db.session.add(EMIPayment(plan_id=plan.id, installment_number=index, due_date=item["due_date"],
                amount=item["amount"], description=item["description"], reminder_days_before=reminder_days))
        db.session.commit()
    except (UnicodeDecodeError, csv.Error):
        db.session.rollback()
        return jsonify({"success": False, "message": "EMI schedule file is not valid UTF-8 CSV."}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Native admin EMI schedule import failed")
        return jsonify({"success": False, "message": "EMI schedule could not be imported."}), 500
    log_user_action("Create EMI Plan", f"Imported schedule '{plan.title}' for Borrower {borrower.id} from native admin")
    return jsonify({"success": True, "message": f"Imported {len(payments)} EMI installment(s).", "id": plan.id,
                    "installments": len(payments), "total_principal": float(plan.total_principal)}), 201
