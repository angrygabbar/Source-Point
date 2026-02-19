from flask import Blueprint, render_template, request, abort
from extensions import db
from models.auth import User
from models.commerce import Product, SellerInventory, ShareableLink
from models.gift_card import GiftCard
from sqlalchemy import or_
from enums import UserRole, GiftCardStatus

public_bp = Blueprint('public', __name__)


@public_bp.route('/shop/<token>')
def shared_catalog(token):
    """Public catalog page — no login required."""
    link = ShareableLink.query.filter_by(token=token).first()

    if not link or not link.is_active:
        return render_template('shared_link_expired.html'), 404

    seller = User.query.get(link.seller_id)
    if not seller:
        abort(404)

    # Filters
    category_filter = request.args.get('category')
    search_query = request.args.get('q', '').strip()

    # Build product list based on role
    if seller.role == UserRole.ADMIN.value:
        # Admin shares the master catalog
        query = Product.query.filter(Product.stock > 0)
    else:
        # Seller shares their assigned inventory
        query = db.session.query(Product).join(
            SellerInventory, SellerInventory.product_id == Product.id
        ).filter(
            SellerInventory.seller_id == seller.id,
            SellerInventory.stock > 0
        )

    if search_query:
        query = query.filter(or_(
            Product.name.ilike(f'%{search_query}%'),
            Product.description.ilike(f'%{search_query}%'),
            Product.category.ilike(f'%{search_query}%')
        ))

    if category_filter:
        query = query.filter(Product.category == category_filter)

    products = query.order_by(Product.id.desc()).all()

    # Categories
    if seller.role == UserRole.ADMIN.value:
        categories_query = db.session.query(Product.category).filter(
            Product.stock > 0
        ).distinct().all()
    else:
        categories_query = db.session.query(Product.category).join(
            SellerInventory, SellerInventory.product_id == Product.id
        ).filter(
            SellerInventory.seller_id == seller.id,
            SellerInventory.stock > 0
        ).distinct().all()

    categories = [c[0] for c in categories_query if c[0]]

    # Vouchers — only available ones, no sensitive data exposed
    vouchers = GiftCard.query.filter_by(
        status=GiftCardStatus.AVAILABLE.value
    ).order_by(GiftCard.denomination.asc()).all()

    return render_template('shared_catalog.html',
                           products=products,
                           categories=categories,
                           current_category=category_filter,
                           search_query=search_query,
                           seller=seller,
                           token=token,
                           vouchers=vouchers)


@public_bp.route('/shop/<token>/product/<int:product_id>')
def shared_product_detail(token, product_id):
    """Public product detail page — no login required."""
    link = ShareableLink.query.filter_by(token=token).first()

    if not link or not link.is_active:
        return render_template('shared_link_expired.html'), 404

    seller = User.query.get(link.seller_id)
    if not seller:
        abort(404)

    product = Product.query.get_or_404(product_id)

    # Verify this product belongs to the seller's inventory
    if seller.role != UserRole.ADMIN.value:
        inv = SellerInventory.query.filter_by(
            seller_id=seller.id, product_id=product.id
        ).first()
        if not inv or inv.stock <= 0:
            abort(404)

    return render_template('shared_product_detail.html',
                           product=product,
                           seller=seller,
                           token=token)
