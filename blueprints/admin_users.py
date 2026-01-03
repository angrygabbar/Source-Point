from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db, bcrypt
from models.auth import User
from utils import role_required, log_user_action, send_email
from datetime import datetime
from sqlalchemy import or_
import cloudinary.uploader
from enums import UserRole  # --- IMPORT ENUM ---

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')

@admin_users_bp.route('/manage')
@login_required
@role_required(UserRole.ADMIN.value) # --- USE ENUM ---
def manage_users():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')

    query = User.query

    if search_query:
        query = query.filter(or_(
            User.username.ilike(f"%{search_query}%"),
            User.email.ilike(f"%{search_query}%")
        ))

    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if status_filter != 'all':
        is_active = True if status_filter == 'active' else False
        query = query.filter_by(is_active=is_active)

    users_pagination = query.order_by(User.id).paginate(page=page, per_page=12, error_out=False)

    return render_template('manage_users.html', 
                           users=users_pagination, 
                           current_search=search_query,
                           current_role=role_filter,
                           current_status=status_filter)

@admin_users_bp.route('/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([username, email, password, role]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin_users.manage_users'))

    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        flash('Username or email already exists.', 'danger')
        return redirect(url_for('admin_users.manage_users'))

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    avatar_url = f'https://api.dicebear.com/8.x/initials/svg?seed={username}'

    new_user = User(
        username=username, email=email, password_hash=hashed_password,
        role=role, avatar_url=avatar_url, is_approved=True
    )
    db.session.add(new_user)
    db.session.commit()
    log_user_action("Create User", f"Created user {username} with role {role}")
    flash(f'User {username} has been created successfully.', 'success')
    return redirect(url_for('admin_users.manage_users'))

@admin_users_bp.route('/toggle_status/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def toggle_user_status(user_id):
    user_to_toggle = User.query.get_or_404(user_id)
    if user_to_toggle.id == current_user.id:
        flash('You cannot change your own status.', 'danger')
        return redirect(url_for('admin_users.manage_users'))

    user_to_toggle.is_active = not user_to_toggle.is_active
    db.session.commit()
    status = "activated" if user_to_toggle.is_active else "deactivated"
    
    log_user_action("Toggle User Status", f"{status.title()} user {user_to_toggle.username}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'User {user_to_toggle.username} has been {status}.',
            'is_active': user_to_toggle.is_active
        })

    flash(f'User {user_to_toggle.username} has been {status}.', 'success')
    return redirect(url_for('admin_users.manage_users'))

@admin_users_bp.route('/approve/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()

    send_email(
        to=user.email,
        subject="Your DevConnect Hub Account is Approved!",
        template="mail/account_approved.html",
        user=user,
        now=datetime.utcnow()
    )
    log_user_action("Approve User", f"Approved user {user.username}")
    flash(f'User {user.username} has been approved.', 'success')

    return redirect(url_for('admin_core.admin_dashboard'))

@admin_users_bp.route('/reject/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def reject_user(user_id):
    user_to_reject = User.query.filter_by(id=user_id, is_approved=False).first_or_404() 
    username = user_to_reject.username
    db.session.delete(user_to_reject)
    db.session.commit()
    log_user_action("Reject User", f"Rejected user registration for {username}")
    flash(f'User registration for {username} has been rejected and deleted.', 'warning')
    return redirect(url_for('admin_core.admin_dashboard'))

@admin_users_bp.route('/profile/view/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user_profile.html', user=user)

@admin_users_bp.route('/profile/edit/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def edit_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('edit_user_profile.html', user=user)

@admin_users_bp.route('/profile/update/<int:user_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_user_profile(user_id):
    user_to_update = User.query.get_or_404(user_id)

    user_to_update.mobile_number = request.form.get('mobile_number')
    user_to_update.primary_skill = request.form.get('primary_skill')
    user_to_update.primary_skill_experience = request.form.get('primary_skill_experience')
    user_to_update.secondary_skill = request.form.get('secondary_skill')
    user_to_update.secondary_skill_experience = request.form.get('secondary_skill_experience')

    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            if file and file.filename.endswith('.pdf'):
                try:
                    upload_result = cloudinary.uploader.upload(
                        file, resource_type="raw", folder="resumes",
                        public_id=f"resume_{user_to_update.id}"
                    )
                    user_to_update.resume_filename = upload_result['secure_url']
                except Exception as e:
                    flash(f'Upload failed: {str(e)}', 'danger')
                    return redirect(url_for('admin_users.edit_user_profile', user_id=user_id))
            else:
                flash('Only PDF files are allowed for resumes.', 'danger')
                return redirect(url_for('admin_users.edit_user_profile', user_id=user_id))

    db.session.commit()
    log_user_action("Update User Profile", f"Admin updated profile for {user_to_update.username}")
    flash(f'{user_to_update.username}\'s profile has been updated.', 'success')
    return redirect(url_for('admin_users.manage_users'))

@admin_users_bp.route('/password/change/<int:user_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def admin_change_user_password(user_id):
    user_to_update = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('admin_users.edit_user_profile', user_id=user_id))

    user_to_update.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    log_user_action("Admin Change Password", f"Admin changed password for {user_to_update.username}")
    flash(f'Password for {user_to_update.username} has been updated.', 'success')
    return redirect(url_for('admin_users.manage_users'))