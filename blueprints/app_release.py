import os
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_from_directory, current_app, abort)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models.app_release import AndroidAppRelease, AppFeature
from utils import role_required, log_user_action
from enums import UserRole

app_release_bp = Blueprint('app_release', __name__, url_prefix='/app')

ALLOWED_EXTENSIONS = {'apk'}

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------------
# PUBLIC: Download page + direct APK (no login required)
# ------------------------------------------------------------------

@app_release_bp.route('/download')
def download_app():
    release  = AndroidAppRelease.query.filter_by(is_active=True)\
                                      .order_by(AndroidAppRelease.uploaded_at.desc()).first()
    features = AppFeature.query.filter_by(is_active=True)\
                               .order_by(AppFeature.sort_order.asc(), AppFeature.id.asc()).all()
    return render_template('app_download.html', release=release, features=features)


@app_release_bp.route('/download/apk')
def download_apk():
    release = AndroidAppRelease.query.filter_by(is_active=True)\
                                     .order_by(AndroidAppRelease.uploaded_at.desc()).first()
    if not release:
        abort(404)
    apk_dir = os.path.join(current_app.root_path, 'static', 'apks')
    return send_from_directory(apk_dir, release.filename,
                               as_attachment=True,
                               download_name=release.original_filename)


# ------------------------------------------------------------------
# ADMIN: Releases (upload / activate / delete)
# ------------------------------------------------------------------

@app_release_bp.route('/admin/releases')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_releases():
    releases = AndroidAppRelease.query.order_by(AndroidAppRelease.uploaded_at.desc()).all()
    features = AppFeature.query.order_by(AppFeature.sort_order.asc(), AppFeature.id.asc()).all()
    return render_template('admin_app_releases.html', releases=releases, features=features)


@app_release_bp.route('/admin/releases/upload', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def upload_release():
    version_name  = request.form.get('version_name', '').strip()
    version_code  = request.form.get('version_code', '1').strip()
    release_notes = request.form.get('release_notes', '').strip()
    file = request.files.get('apk_file')

    if not version_name:
        flash('Version name is required.', 'danger')
        return redirect(url_for('app_release.manage_releases'))
    if not file or file.filename == '':
        flash('No APK file selected.', 'danger')
        return redirect(url_for('app_release.manage_releases'))
    if not _allowed_file(file.filename):
        flash('Only .apk files are allowed.', 'danger')
        return redirect(url_for('app_release.manage_releases'))

    safe_version    = secure_filename(version_name)
    stored_filename = f"SourcePoint-v{safe_version}-{version_code}.apk"
    original_filename = f"SourcePoint-v{version_name}.apk"

    apk_dir  = os.path.join(current_app.root_path, 'static', 'apks')
    os.makedirs(apk_dir, exist_ok=True)
    filepath = os.path.join(apk_dir, stored_filename)
    file.save(filepath)
    file_size = os.path.getsize(filepath)

    AndroidAppRelease.query.update({'is_active': False})
    new_release = AndroidAppRelease(
        version_name=version_name,
        version_code=int(version_code) if version_code.isdigit() else 1,
        filename=stored_filename,
        original_filename=original_filename,
        file_size=file_size,
        release_notes=release_notes,
        is_active=True,
        uploaded_by_id=current_user.id
    )
    db.session.add(new_release)
    db.session.commit()

    log_user_action("Upload APK", f"Uploaded Android app v{version_name} ({file_size} bytes)")
    flash(f'Android app v{version_name} uploaded successfully and set as active.', 'success')
    return redirect(url_for('app_release.manage_releases'))


@app_release_bp.route('/admin/releases/<int:release_id>/toggle', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def toggle_release(release_id):
    release = AndroidAppRelease.query.get_or_404(release_id)
    AndroidAppRelease.query.update({'is_active': False})
    release.is_active = True
    db.session.commit()
    log_user_action("Activate APK Release", f"Activated Android app v{release.version_name}")
    flash(f'v{release.version_name} is now the active download.', 'success')
    return redirect(url_for('app_release.manage_releases'))


@app_release_bp.route('/admin/releases/<int:release_id>/delete', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_release(release_id):
    release = AndroidAppRelease.query.get_or_404(release_id)
    apk_dir  = os.path.join(current_app.root_path, 'static', 'apks')
    filepath = os.path.join(apk_dir, release.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    was_active = release.is_active
    db.session.delete(release)
    db.session.commit()

    if was_active:
        latest = AndroidAppRelease.query.order_by(AndroidAppRelease.uploaded_at.desc()).first()
        if latest:
            latest.is_active = True
            db.session.commit()

    log_user_action("Delete APK Release", f"Deleted Android app v{release.version_name}")
    flash(f'Release v{release.version_name} deleted.', 'success')
    return redirect(url_for('app_release.manage_releases'))


# ------------------------------------------------------------------
# ADMIN: App Features (add / edit / delete / toggle)
# ------------------------------------------------------------------

@app_release_bp.route('/admin/features/add', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def add_feature():
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    icon        = request.form.get('icon', 'fa-star').strip()
    color       = request.form.get('color', 'emerald').strip()
    sort_order  = request.form.get('sort_order', '0').strip()

    if not title or not description:
        flash('Title and description are required.', 'danger')
        return redirect(url_for('app_release.manage_releases'))

    feature = AppFeature(
        title=title, description=description,
        icon=icon, color=color,
        sort_order=int(sort_order) if sort_order.isdigit() else 0
    )
    db.session.add(feature)
    db.session.commit()
    log_user_action("Add App Feature", f"Added feature: {title}")
    flash(f'Feature "{title}" added.', 'success')
    return redirect(url_for('app_release.manage_releases'))


@app_release_bp.route('/admin/features/<int:feature_id>/edit', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_feature(feature_id):
    feature = AppFeature.query.get_or_404(feature_id)
    feature.title       = request.form.get('title', feature.title).strip()
    feature.description = request.form.get('description', feature.description).strip()
    feature.icon        = request.form.get('icon', feature.icon).strip()
    feature.color       = request.form.get('color', feature.color).strip()
    sort_order = request.form.get('sort_order', str(feature.sort_order)).strip()
    feature.sort_order  = int(sort_order) if sort_order.isdigit() else feature.sort_order
    db.session.commit()
    log_user_action("Edit App Feature", f"Edited feature: {feature.title}")
    flash(f'Feature "{feature.title}" updated.', 'success')
    return redirect(url_for('app_release.manage_releases'))


@app_release_bp.route('/admin/features/<int:feature_id>/toggle', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def toggle_feature(feature_id):
    feature = AppFeature.query.get_or_404(feature_id)
    feature.is_active = not feature.is_active
    db.session.commit()
    state = 'shown' if feature.is_active else 'hidden'
    flash(f'Feature "{feature.title}" is now {state} on the download page.', 'success')
    return redirect(url_for('app_release.manage_releases'))


@app_release_bp.route('/admin/features/<int:feature_id>/delete', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_feature(feature_id):
    feature = AppFeature.query.get_or_404(feature_id)
    title = feature.title
    db.session.delete(feature)
    db.session.commit()
    log_user_action("Delete App Feature", f"Deleted feature: {title}")
    flash(f'Feature "{title}" deleted.', 'success')
    return redirect(url_for('app_release.manage_releases'))
