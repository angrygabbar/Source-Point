from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from enums import UserRole, AssetType, AssetStatus, AssetCondition
from models.asset import Asset
from models.auth import User
from utils import role_required, log_user_action


admin_assets_bp = Blueprint(
    'admin_assets',
    __name__,
    url_prefix='/admin/assets'
)


def _generate_asset_code():
    """Generate the next asset code like SP-AST-0001."""
    last_asset = Asset.query.order_by(Asset.id.desc()).first()
    next_id = (last_asset.id + 1) if last_asset else 1
    return f"SP-AST-{next_id:04d}"


def _get_dropdowns():
    """Return common dropdown data used across templates."""
    return {
        'all_users': User.query.order_by(User.username).all(),
        'asset_types': [(t.value, t.value) for t in AssetType],
        'asset_statuses': [(s.value, s.value) for s in AssetStatus],
        'asset_conditions': [(c.value, c.value) for c in AssetCondition],
    }


@admin_assets_bp.route('/')
@login_required
@role_required(UserRole.ADMIN.value)
def dashboard():
    # --- Filters ---
    filter_type = request.args.get('type', '')
    filter_status = request.args.get('status', '')
    filter_assigned = request.args.get('assigned_to', '')
    filter_location = request.args.get('location', '')
    search_query = request.args.get('q', '')

    query = Asset.query

    if filter_type:
        query = query.filter(Asset.asset_type == filter_type)
    if filter_status:
        query = query.filter(Asset.status == filter_status)
    if filter_assigned:
        query = query.filter(Asset.assigned_to_id == int(filter_assigned))
    if filter_location:
        query = query.filter(Asset.location.ilike(f'%{filter_location}%'))
    if search_query:
        query = query.filter(
            or_(
                Asset.name.ilike(f'%{search_query}%'),
                Asset.asset_code.ilike(f'%{search_query}%'),
                Asset.serial_number.ilike(f'%{search_query}%'),
                Asset.brand.ilike(f'%{search_query}%'),
            )
        )

    assets = query.order_by(Asset.created_at.desc()).all()

    # --- Stats ---
    total_assets = Asset.query.count()
    active_count = Asset.query.filter_by(status=AssetStatus.ACTIVE.value).count()
    storage_count = Asset.query.filter_by(status=AssetStatus.IN_STORAGE.value).count()
    repair_count = Asset.query.filter_by(status=AssetStatus.UNDER_REPAIR.value).count()
    retired_count = Asset.query.filter_by(status=AssetStatus.RETIRED.value).count()
    assigned_count = Asset.query.filter(Asset.assigned_to_id.isnot(None), Asset.status == AssetStatus.ACTIVE.value).count()

    # Get unique locations for filter dropdown
    locations = db.session.query(Asset.location).filter(Asset.location.isnot(None)).distinct().all()
    locations = sorted([loc[0] for loc in locations if loc[0]])

    dropdowns = _get_dropdowns()

    return render_template(
        'admin_assets.html',
        assets=assets,
        total_assets=total_assets,
        active_count=active_count,
        storage_count=storage_count,
        repair_count=repair_count,
        retired_count=retired_count,
        assigned_count=assigned_count,
        locations=locations,
        filter_type=filter_type,
        filter_status=filter_status,
        filter_assigned=filter_assigned,
        filter_location=filter_location,
        search_query=search_query,
        **dropdowns,
    )


@admin_assets_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def add_asset_page():
    dropdowns = _get_dropdowns()

    if request.method == 'GET':
        return render_template('admin_assets_add.html', **dropdowns)

    # --- POST: process the form ---
    name = request.form.get('name', '').strip()
    asset_type = request.form.get('asset_type', '')
    serial_number = request.form.get('serial_number', '').strip()
    brand = request.form.get('brand', '').strip()
    model_number = request.form.get('model_number', '').strip()
    purchase_date_str = request.form.get('purchase_date', '')
    purchase_price = request.form.get('purchase_price', '')
    warranty_expiry_str = request.form.get('warranty_expiry', '')
    status = request.form.get('status', AssetStatus.ACTIVE.value)
    condition = request.form.get('condition', AssetCondition.NEW.value)
    assigned_to_id = request.form.get('assigned_to_id', '')
    allocation_date_str = request.form.get('allocation_date', '')
    location = request.form.get('location', '').strip()
    notes = request.form.get('notes', '').strip()

    if not name or not asset_type:
        flash('Asset name and type are required.', 'danger')
        return render_template('admin_assets_add.html', **dropdowns)

    new_asset = Asset(
        asset_code=_generate_asset_code(),
        name=name,
        asset_type=asset_type,
        serial_number=serial_number or None,
        brand=brand or None,
        model_number=model_number or None,
        status=status,
        condition=condition,
        location=location or None,
        notes=notes or None,
        authorized_by_id=current_user.id,
    )

    # Parse dates
    if purchase_date_str:
        try:
            new_asset.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if warranty_expiry_str:
        try:
            new_asset.warranty_expiry = datetime.strptime(warranty_expiry_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if allocation_date_str:
        try:
            new_asset.allocation_date = datetime.strptime(allocation_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Parse price
    if purchase_price:
        try:
            new_asset.purchase_price = float(purchase_price)
        except ValueError:
            pass

    # Assignment
    if assigned_to_id:
        new_asset.assigned_to_id = int(assigned_to_id)
        if not new_asset.allocation_date:
            new_asset.allocation_date = datetime.utcnow().date()

    db.session.add(new_asset)
    db.session.commit()

    log_user_action("Add Asset", f"Added asset {new_asset.asset_code}: {new_asset.name}")
    flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added successfully.', 'success')
    return redirect(url_for('admin_assets.dashboard'))


@admin_assets_bp.route('/view/<int:asset_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def view_asset(asset_id):
    from datetime import date
    asset = Asset.query.get_or_404(asset_id)
    return render_template('admin_assets_view.html', asset=asset, today=date.today())


@admin_assets_bp.route('/edit/<int:asset_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    asset.name = request.form.get('name', asset.name).strip()
    asset.asset_type = request.form.get('asset_type', asset.asset_type)
    asset.serial_number = request.form.get('serial_number', '').strip() or None
    asset.brand = request.form.get('brand', '').strip() or None
    asset.model_number = request.form.get('model_number', '').strip() or None
    asset.status = request.form.get('status', asset.status)
    asset.condition = request.form.get('condition', asset.condition)
    asset.location = request.form.get('location', '').strip() or None
    asset.notes = request.form.get('notes', '').strip() or None

    # Parse dates
    purchase_date_str = request.form.get('purchase_date', '')
    warranty_expiry_str = request.form.get('warranty_expiry', '')
    allocation_date_str = request.form.get('allocation_date', '')
    purchase_price = request.form.get('purchase_price', '')

    if purchase_date_str:
        try:
            asset.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        asset.purchase_date = None

    if warranty_expiry_str:
        try:
            asset.warranty_expiry = datetime.strptime(warranty_expiry_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        asset.warranty_expiry = None

    if allocation_date_str:
        try:
            asset.allocation_date = datetime.strptime(allocation_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        asset.allocation_date = None

    if purchase_price:
        try:
            asset.purchase_price = float(purchase_price)
        except ValueError:
            pass
    else:
        asset.purchase_price = None

    # Handle assignment changes
    new_assigned_to = request.form.get('assigned_to_id', '')
    old_assigned_to = asset.assigned_to_id

    if new_assigned_to:
        asset.assigned_to_id = int(new_assigned_to)
        # Set allocation date if newly assigned
        if not old_assigned_to or old_assigned_to != int(new_assigned_to):
            if not asset.allocation_date:
                asset.allocation_date = datetime.utcnow().date()
    else:
        asset.assigned_to_id = None

    asset.updated_at = datetime.utcnow()
    db.session.commit()

    log_user_action("Edit Asset", f"Updated asset {asset.asset_code}: {asset.name}")
    flash(f'Asset "{asset.name}" updated successfully.', 'success')
    return redirect(url_for('admin_assets.dashboard'))


@admin_assets_bp.route('/delete/<int:asset_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    asset_name = asset.name
    asset_code = asset.asset_code

    db.session.delete(asset)
    db.session.commit()

    log_user_action("Delete Asset", f"Deleted asset {asset_code}: {asset_name}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Asset "{asset_name}" deleted.'})

    flash(f'Asset "{asset_name}" ({asset_code}) has been deleted.', 'success')
    return redirect(url_for('admin_assets.dashboard'))


@admin_assets_bp.route('/detail/<int:asset_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def asset_detail(asset_id):
    """Return asset details as JSON for the edit modal."""
    asset = Asset.query.get_or_404(asset_id)
    return jsonify({
        'id': asset.id,
        'asset_code': asset.asset_code,
        'name': asset.name,
        'asset_type': asset.asset_type,
        'serial_number': asset.serial_number or '',
        'brand': asset.brand or '',
        'model_number': asset.model_number or '',
        'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else '',
        'purchase_price': str(asset.purchase_price) if asset.purchase_price else '',
        'warranty_expiry': asset.warranty_expiry.isoformat() if asset.warranty_expiry else '',
        'status': asset.status,
        'condition': asset.condition,
        'assigned_to_id': asset.assigned_to_id or '',
        'assigned_to_name': asset.assigned_to.username if asset.assigned_to else '',
        'authorized_by_name': asset.authorized_by.username if asset.authorized_by else '',
        'allocation_date': asset.allocation_date.isoformat() if asset.allocation_date else '',
        'location': asset.location or '',
        'notes': asset.notes or '',
        'created_at': asset.created_at.strftime('%d %b %Y, %I:%M %p') if asset.created_at else '',
        'updated_at': asset.updated_at.strftime('%d %b %Y, %I:%M %p') if asset.updated_at else '',
    })
