from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from enums import UserRole, AssetType, AssetStatus, AssetCondition
from models.asset import Asset
from models.auth import User
from services.asset_email_service import (
    ASSET_ACTION_ASSIGNED,
    ASSET_ACTION_SOLD,
    send_asset_assignment_email,
    send_asset_cancellation_email,
    send_asset_delivery_receipt_email,
    send_asset_sale_terms_email,
)
from utils import role_required, log_user_action


admin_assets_bp = Blueprint(
    'admin_assets',
    __name__,
    url_prefix='/admin/assets'
)

# ── Default Terms & Conditions Template ──
DEFAULT_TERMS_AND_CONDITIONS = """1. NO RETURN POLICY — This asset has been inspected, tested, and verified before allocation. By accepting this asset, the assignee acknowledges that the asset is in proper working condition and agrees to a strict no-return policy.

2. ASSET CONDITION ACCEPTANCE — The assignee confirms that the asset was demonstrated and agreed upon in its current condition at the time of handover. Any pre-existing defects or cosmetic issues have been communicated and accepted.

3. POST-PURCHASE LIABILITY — Any damage, malfunction, hardware failure, or issue arising after the date of purchase/allocation shall be the sole responsibility of the assignee. SourcePoint shall bear no liability or accountability for such issues.

4. MAINTENANCE & REPAIRS — The assignee is fully responsible for all maintenance, servicing, and repair costs incurred after the allocation date. SourcePoint does not provide any post-allocation support or repair services.

5. WARRANTY DISCLAIMER — Unless explicitly stated otherwise, SourcePoint does not extend any warranty on the allocated asset beyond the manufacturer's warranty (if applicable). Any warranty claims must be handled directly with the manufacturer.

6. PROPER USE — The assignee agrees to use the asset responsibly and in accordance with its intended purpose. Any misuse, negligence, or unauthorized modifications will void any remaining support obligations.

7. ASSET ACCOUNTABILITY — The assignee is accountable for the safekeeping of the asset. In the event of loss, theft, or irreparable damage, the assignee may be liable for the replacement cost as determined by SourcePoint.

8. NON-TRANSFERABLE — This asset allocation is non-transferable. The assignee may not lend, sell, or reassign the asset to any other individual without prior written approval from SourcePoint administration."""


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


def _parse_hardware_specs(form):
    """Extract hardware specification fields from form data."""
    return {
        'processor': form.get('processor', '').strip() or None,
        'ram': form.get('ram', '').strip() or None,
        'storage_spec': form.get('storage_spec', '').strip() or None,
        'display': form.get('display', '').strip() or None,
        'graphics': form.get('graphics', '').strip() or None,
        'operating_system': form.get('operating_system', '').strip() or None,
        'battery': form.get('battery', '').strip() or None,
        'color': form.get('color', '').strip() or None,
    }


def _parse_decimal(value):
    """Parse optional currency/decimal values from form data."""
    if not value:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _asset_acceptance_snapshot(asset):
    """Fields that require a fresh sale terms acceptance when changed."""
    return (
        asset.name,
        asset.asset_type,
        asset.serial_number,
        asset.brand,
        asset.model_number,
        asset.condition,
        asset.processor,
        asset.ram,
        asset.storage_spec,
        asset.display,
        asset.graphics,
        asset.operating_system,
        asset.battery,
        asset.color,
        asset.sold_to_name,
        asset.sold_to_email,
        asset.sold_date.isoformat() if asset.sold_date else None,
        f"{float(asset.sale_price):.2f}" if asset.sale_price is not None else None,
        asset.terms_and_conditions,
    )


def _reset_sale_acceptance(asset):
    asset.sale_terms_email_sent_at = None
    asset.sale_terms_accepted_at = None
    asset.sale_terms_accepted_ip = None
    asset.sale_terms_acceptance_user_agent = None
    asset.delivery_receipt_sent_at = None


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
    sold_count = Asset.query.filter_by(asset_action=ASSET_ACTION_SOLD).count()
    retired_count = Asset.query.filter_by(status=AssetStatus.RETIRED.value).count()
    assigned_count = Asset.query.filter(Asset.assigned_to_id.isnot(None), Asset.status == AssetStatus.ACTIVE.value).count()
    cancelled_count = Asset.query.filter_by(status=AssetStatus.CANCELLED.value).count()

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
        sold_count=sold_count,
        retired_count=retired_count,
        assigned_count=assigned_count,
        cancelled_count=cancelled_count,
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
        return render_template(
            'admin_assets_add.html',
            default_terms=DEFAULT_TERMS_AND_CONDITIONS,
            **dropdowns,
        )

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
    asset_action = request.form.get('asset_action', '').strip()
    assigned_to_id = request.form.get('assigned_to_id', '')
    allocation_date_str = request.form.get('allocation_date', '')
    sold_to_name = request.form.get('sold_to_name', '').strip()
    sold_to_email = request.form.get('sold_to_email', '').strip()
    sold_date_str = request.form.get('sold_date', '')
    sale_price = request.form.get('sale_price', '')
    location = request.form.get('location', '').strip()
    notes = request.form.get('notes', '').strip()
    terms_and_conditions = request.form.get('terms_and_conditions', '').strip()

    if not asset_action and assigned_to_id:
        asset_action = ASSET_ACTION_ASSIGNED
    elif not asset_action and sold_to_email:
        asset_action = ASSET_ACTION_SOLD

    if not name or not asset_type:
        flash('Asset name and type are required.', 'danger')
        return render_template(
            'admin_assets_add.html',
            default_terms=DEFAULT_TERMS_AND_CONDITIONS,
            **dropdowns,
        )

    # Parse hardware specs
    hw_specs = _parse_hardware_specs(request.form)

    new_asset = Asset(
        asset_code=_generate_asset_code(),
        name=name,
        asset_type=asset_type,
        serial_number=serial_number or None,
        brand=brand or None,
        model_number=model_number or None,
        asset_action=asset_action or None,
        status=status,
        condition=condition,
        location=location or None,
        notes=notes or None,
        terms_and_conditions=terms_and_conditions or DEFAULT_TERMS_AND_CONDITIONS,
        authorized_by_id=current_user.id,
        **hw_specs,
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
    assigned_user = None
    sold_email = None
    if asset_action == ASSET_ACTION_ASSIGNED:
        if not assigned_to_id:
            flash('Please select the registered user this asset is assigned to.', 'danger')
            return render_template(
                'admin_assets_add.html',
                default_terms=DEFAULT_TERMS_AND_CONDITIONS,
                **dropdowns,
            )

        try:
            assigned_user = User.query.get(int(assigned_to_id))
        except (TypeError, ValueError):
            assigned_user = None

        if not assigned_user:
            flash('Selected assignee was not found.', 'danger')
            return render_template(
                'admin_assets_add.html',
                default_terms=DEFAULT_TERMS_AND_CONDITIONS,
                **dropdowns,
            )

        new_asset.assigned_to_id = assigned_user.id
        if not new_asset.allocation_date:
            new_asset.allocation_date = datetime.utcnow().date()
        new_asset.generate_share_token()
    elif asset_action == ASSET_ACTION_SOLD:
        if not sold_to_email:
            flash('Sold-to email is required when selling an asset.', 'danger')
            return render_template(
                'admin_assets_add.html',
                default_terms=DEFAULT_TERMS_AND_CONDITIONS,
                **dropdowns,
            )

        new_asset.status = AssetStatus.SOLD.value
        new_asset.sold_to_name = sold_to_name or None
        new_asset.sold_to_email = sold_to_email
        sold_email = sold_to_email
        if sold_date_str:
            try:
                new_asset.sold_date = datetime.strptime(sold_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if not new_asset.sold_date:
            new_asset.sold_date = datetime.utcnow().date()
        new_asset.sale_price = _parse_decimal(sale_price)
        new_asset.assigned_to_id = None
        new_asset.allocation_date = None
        _reset_sale_acceptance(new_asset)
        new_asset.generate_share_token()

    db.session.add(new_asset)
    db.session.commit()

    log_user_action("Add Asset", f"Added asset {new_asset.asset_code}: {new_asset.name}")

    # Send assignment email if asset is assigned to someone
    if assigned_user:
        email_sent = send_asset_assignment_email(new_asset, assigned_user)
        if email_sent:
            flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added and assignment email sent to {assigned_user.username}.', 'success')
        elif not assigned_user.email:
            flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added, but {assigned_user.username} has no email address for the assignment email.', 'warning')
        else:
            flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added, but the assignment email could not be sent.', 'warning')
    elif sold_email:
        email_sent = send_asset_sale_terms_email(new_asset)
        if email_sent:
            flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added as sold. Terms acceptance email sent to {sold_email}; delivery receipt will send after acceptance.', 'success')
        else:
            flash(f'Asset "{new_asset.name}" ({new_asset.asset_code}) added as sold, but the terms acceptance email could not be sent.', 'warning')
    else:
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
    old_acceptance_snapshot = _asset_acceptance_snapshot(asset)

    asset.name = request.form.get('name', asset.name).strip()
    asset.asset_type = request.form.get('asset_type', asset.asset_type)
    asset.serial_number = request.form.get('serial_number', '').strip() or None
    asset.brand = request.form.get('brand', '').strip() or None
    asset.model_number = request.form.get('model_number', '').strip() or None
    asset.status = request.form.get('status', asset.status)
    asset.condition = request.form.get('condition', asset.condition)
    asset.location = request.form.get('location', '').strip() or None
    asset.notes = request.form.get('notes', '').strip() or None

    # Hardware specs
    hw_specs = _parse_hardware_specs(request.form)
    for key, val in hw_specs.items():
        setattr(asset, key, val)

    # Terms & Conditions
    terms = request.form.get('terms_and_conditions', '').strip()
    asset.terms_and_conditions = terms or DEFAULT_TERMS_AND_CONDITIONS

    # Parse dates
    purchase_date_str = request.form.get('purchase_date', '')
    warranty_expiry_str = request.form.get('warranty_expiry', '')
    allocation_date_str = request.form.get('allocation_date', '')
    purchase_price = request.form.get('purchase_price', '')
    asset_action = request.form.get('asset_action', '').strip()
    sold_to_name = request.form.get('sold_to_name', '').strip()
    sold_to_email = request.form.get('sold_to_email', '').strip()
    sold_date_str = request.form.get('sold_date', '')
    sale_price = request.form.get('sale_price', '')

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
    if not asset_action and new_assigned_to:
        asset_action = ASSET_ACTION_ASSIGNED
    elif not asset_action and sold_to_email:
        asset_action = ASSET_ACTION_SOLD

    old_action = asset.asset_action
    old_assigned_to = asset.assigned_to_id
    old_sold_to_email = asset.sold_to_email

    assigned_user = None
    sold_email = None
    send_assignment_email = False
    send_terms_email = False

    if asset_action == ASSET_ACTION_ASSIGNED:
        if not new_assigned_to:
            flash('Please select the registered user this asset is assigned to.', 'danger')
            return redirect(url_for('admin_assets.dashboard'))

        try:
            assigned_user = User.query.get(int(new_assigned_to))
        except (TypeError, ValueError):
            assigned_user = None

        if not assigned_user:
            flash('Selected assignee was not found.', 'danger')
            return redirect(url_for('admin_assets.dashboard'))

        asset.asset_action = ASSET_ACTION_ASSIGNED
        asset.assigned_to_id = assigned_user.id
        asset.sold_to_name = None
        asset.sold_to_email = None
        asset.sold_date = None
        asset.sale_price = None
        _reset_sale_acceptance(asset)
        # Set allocation date if newly assigned
        if old_action != ASSET_ACTION_ASSIGNED or not old_assigned_to or old_assigned_to != assigned_user.id:
            if not asset.allocation_date:
                asset.allocation_date = datetime.utcnow().date()
            # Rotate the token so previous assignees cannot keep using old links.
            asset.generate_share_token()
            send_assignment_email = True
        elif not asset.share_token:
            asset.generate_share_token()
    elif asset_action == ASSET_ACTION_SOLD:
        if not sold_to_email:
            flash('Sold-to email is required when selling an asset.', 'danger')
            return redirect(url_for('admin_assets.dashboard'))

        asset.asset_action = ASSET_ACTION_SOLD
        asset.assigned_to_id = None
        asset.allocation_date = None
        asset.sold_to_name = sold_to_name or None
        asset.sold_to_email = sold_to_email
        sold_email = sold_to_email
        if sold_date_str:
            try:
                asset.sold_date = datetime.strptime(sold_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            asset.sold_date = None
        if not asset.sold_date:
            asset.sold_date = datetime.utcnow().date()
        asset.sale_price = _parse_decimal(sale_price)
        asset.status = AssetStatus.SOLD.value

        new_acceptance_snapshot = _asset_acceptance_snapshot(asset)
        sale_details_changed = old_acceptance_snapshot != new_acceptance_snapshot

        if old_action != ASSET_ACTION_SOLD or old_sold_to_email != sold_to_email or sale_details_changed:
            _reset_sale_acceptance(asset)
            asset.generate_share_token()
            send_terms_email = True
        elif not asset.share_token:
            asset.generate_share_token()
            send_terms_email = True
        elif not asset.sale_terms_email_sent_at and not asset.sale_terms_accepted_at:
            send_terms_email = True
    else:
        asset.asset_action = None
        asset.assigned_to_id = None
        asset.allocation_date = None
        asset.sold_to_name = None
        asset.sold_to_email = None
        asset.sold_date = None
        asset.sale_price = None
        asset.share_token = None
        _reset_sale_acceptance(asset)

    asset.updated_at = datetime.utcnow()
    db.session.commit()

    log_user_action("Edit Asset", f"Updated asset {asset.asset_code}: {asset.name}")

    # Send email if assignment changed to a new user
    if assigned_user:
        if send_assignment_email:
            email_sent = send_asset_assignment_email(asset, assigned_user)
            if email_sent:
                flash(f'Asset "{asset.name}" updated and assignment email sent to {assigned_user.username}.', 'success')
            elif not assigned_user.email:
                flash(f'Asset "{asset.name}" updated, but {assigned_user.username} has no email address for the assignment email.', 'warning')
            else:
                flash(f'Asset "{asset.name}" updated, but the assignment email could not be sent.', 'warning')
        else:
            flash(f'Asset "{asset.name}" updated successfully.', 'success')
    elif sold_email:
        if send_terms_email:
            email_sent = send_asset_sale_terms_email(asset)
            if email_sent:
                flash(f'Asset "{asset.name}" updated as sold. Terms acceptance email sent to {sold_email}; delivery receipt will send after acceptance.', 'success')
            else:
                flash(f'Asset "{asset.name}" updated as sold, but the terms acceptance email could not be sent.', 'warning')
        else:
            flash(f'Asset "{asset.name}" updated successfully.', 'success')
    else:
        flash(f'Asset "{asset.name}" updated successfully.', 'success')

    return redirect(url_for('admin_assets.dashboard'))


@admin_assets_bp.route('/resend-email/<int:asset_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def resend_assignment_email(asset_id):
    """Resend the assignment email for an asset."""
    asset = Asset.query.get_or_404(asset_id)
    if asset.asset_action == ASSET_ACTION_SOLD and asset.sold_to_email:
        if asset.sale_terms_accepted_at:
            email_sent = send_asset_delivery_receipt_email(asset)
            log_user_action("Resend Asset Receipt", f"Resent delivery receipt for {asset.asset_code} to {asset.sold_to_email}")
            if email_sent:
                flash(f'Delivery receipt resent to {asset.sold_to_email}.', 'success')
            else:
                flash('Delivery receipt could not be sent. Please check the mail service.', 'warning')
        else:
            email_sent = send_asset_sale_terms_email(asset)
            log_user_action("Resend Asset Terms", f"Resent sale terms acceptance email for {asset.asset_code} to {asset.sold_to_email}")
            if email_sent:
                flash(f'Terms acceptance email resent to {asset.sold_to_email}.', 'success')
            else:
                flash('Terms acceptance email could not be sent. Please check the mail service.', 'warning')
        return redirect(url_for('admin_assets.view_asset', asset_id=asset.id))

    if not asset.assigned_to:
        flash('This asset is not assigned or sold to anyone.', 'danger')
        return redirect(url_for('admin_assets.view_asset', asset_id=asset.id))

    email_sent = send_asset_assignment_email(asset, asset.assigned_to)
    log_user_action("Resend Asset Email", f"Resent assignment email for {asset.asset_code} to {asset.assigned_to.username}")
    if email_sent:
        flash(f'Assignment email resent to {asset.assigned_to.username}.', 'success')
    elif not asset.assigned_to.email:
        flash(f'{asset.assigned_to.username} has no email address for the assignment email.', 'warning')
    else:
        flash('Assignment email could not be sent. Please check the mail service.', 'warning')
    return redirect(url_for('admin_assets.view_asset', asset_id=asset.id))


@admin_assets_bp.route('/cancel/<int:asset_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def cancel_asset(asset_id):
    """Cancel an asset sale/assignment and notify the buyer."""
    asset = Asset.query.get_or_404(asset_id)
    cancellation_reason = request.form.get('cancellation_reason', '').strip()

    if asset.status == AssetStatus.CANCELLED.value:
        flash(f'Asset "{asset.name}" is already cancelled.', 'warning')
        return redirect(url_for('admin_assets.view_asset', asset_id=asset.id))

    # Capture recipient before clearing fields
    recipient_email = None
    recipient_name = None
    if asset.asset_action == ASSET_ACTION_SOLD and asset.sold_to_email:
        recipient_email = asset.sold_to_email
        recipient_name = asset.sold_to_name or asset.sold_to_email
    elif asset.assigned_to:
        recipient_email = asset.assigned_to.email if asset.assigned_to.email else None
        recipient_name = asset.assigned_to.username

    # Update asset status
    asset.status = AssetStatus.CANCELLED.value
    asset.cancelled_at = datetime.utcnow()
    asset.cancellation_reason = cancellation_reason or None
    # Invalidate the share token so old public links stop working
    asset.share_token = None
    # Reset sale acceptance tracking
    _reset_sale_acceptance(asset)
    asset.updated_at = datetime.utcnow()
    db.session.commit()

    log_user_action("Cancel Asset", f"Cancelled asset {asset.asset_code}: {asset.name}")

    # Send cancellation email to buyer/assignee
    if recipient_email:
        email_sent = send_asset_cancellation_email(asset, recipient_email, recipient_name)
        if email_sent:
            flash(f'Asset "{asset.name}" has been cancelled. Cancellation notification sent to {recipient_name}.', 'success')
        else:
            flash(f'Asset "{asset.name}" has been cancelled, but the notification email could not be sent.', 'warning')
    else:
        flash(f'Asset "{asset.name}" has been cancelled.', 'success')

    return redirect(url_for('admin_assets.view_asset', asset_id=asset.id))


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
        'asset_action': asset.asset_action or '',
        'assigned_to_id': asset.assigned_to_id or '',
        'assigned_to_name': asset.assigned_to.username if asset.assigned_to else '',
        'sold_to_name': asset.sold_to_name or '',
        'sold_to_email': asset.sold_to_email or '',
        'sold_date': asset.sold_date.isoformat() if asset.sold_date else '',
        'sale_price': str(asset.sale_price) if asset.sale_price else '',
        'authorized_by_name': asset.authorized_by.username if asset.authorized_by else '',
        'allocation_date': asset.allocation_date.isoformat() if asset.allocation_date else '',
        'location': asset.location or '',
        'notes': asset.notes or '',
        'processor': asset.processor or '',
        'ram': asset.ram or '',
        'storage_spec': asset.storage_spec or '',
        'display': asset.display or '',
        'graphics': asset.graphics or '',
        'operating_system': asset.operating_system or '',
        'battery': asset.battery or '',
        'color': asset.color or '',
        'terms_and_conditions': asset.terms_and_conditions or DEFAULT_TERMS_AND_CONDITIONS,
        'sale_terms_email_sent_at': asset.sale_terms_email_sent_at.isoformat() if asset.sale_terms_email_sent_at else '',
        'sale_terms_accepted_at': asset.sale_terms_accepted_at.isoformat() if asset.sale_terms_accepted_at else '',
        'delivery_receipt_sent_at': asset.delivery_receipt_sent_at.isoformat() if asset.delivery_receipt_sent_at else '',
        'created_at': asset.created_at.strftime('%d %b %Y, %I:%M %p') if asset.created_at else '',
        'updated_at': asset.updated_at.strftime('%d %b %Y, %I:%M %p') if asset.updated_at else '',
    })
