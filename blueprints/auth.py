from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from extensions import db, bcrypt
from utils import send_email, log_user_action
from datetime import datetime
from enums import UserRole
import os
import sys
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_register', methods=['GET'])
def login_register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login_register.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    print("DEBUG: /login route hit. Processing form data...", file=sys.stderr)
    
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember-me') else False

    # Authenticate via Service
    user, message = AuthService.authenticate_user(email, password)

    if user:
        print(f"DEBUG: Logging in user {user.id}...", file=sys.stderr)
        try:
            login_user(user, remember=remember)
            # Log the login activity
            log_user_action('User Login', f'User {user.username} logged in successfully')
        except Exception as e:
            print(f"CRITICAL ERROR: login_user() failed: {e}", file=sys.stderr)
            traceback.print_exc()
            flash('Internal system error during login session creation.', 'danger')
            return redirect(url_for('auth.login_register'))
        
        # Role-based Redirection Map
        role_map = {
            UserRole.ADMIN.value: 'admin_core.admin_dashboard',
            UserRole.DEVELOPER.value: 'developer.developer_dashboard',
            UserRole.MODERATOR.value: 'moderator.moderator_dashboard',
            UserRole.CANDIDATE.value: 'candidate.candidate_dashboard',
            UserRole.BUYER.value: 'buyer.buyer_dashboard',
            UserRole.SELLER.value: 'seller.seller_dashboard',
            UserRole.RECRUITER.value: 'recruiter.recruiter_dashboard',
            UserRole.TEACHER.value: 'teaching.home',
            UserRole.STUDENT.value: 'teaching.home'
        }
        
        target = role_map.get(user.role, 'main.dashboard')
        print(f"DEBUG: Redirecting user to {target}...", file=sys.stderr)
        
        next_page = request.args.get('next')
        if next_page and not next_page.startswith('/'):
            next_page = None 
            
        return redirect(next_page) if next_page else redirect(url_for(target))
    else:
        print(f"DEBUG: Auth failed. Message: {message}", file=sys.stderr)
        flash(message, 'danger')
        return redirect(url_for('auth.login_register'))

@auth_bp.route('/register', methods=['POST'])
@auth_bp.route('/api/v1/auth/register', methods=['POST'])
def register():
    is_mobile_request = request.is_json
    form_data = (request.get_json(silent=True) or {}) if is_mobile_request else request.form
    if current_user.is_authenticated:
        if is_mobile_request:
            return jsonify({'success': False, 'message': 'You are already signed in.'}), 409
        return redirect(url_for('main.dashboard'))

    username = str(form_data.get('username', '')).strip()
    email = str(form_data.get('email', '')).strip()
    password = form_data.get('password')
    confirm_password = form_data.get('confirm_password')
    role = form_data.get('role', UserRole.CANDIDATE.value)
    if is_mobile_request and not isinstance(role, str):
        return jsonify({'success': False, 'message': 'Please choose a valid account type.'}), 400
    allowed_roles = {
        UserRole.BUYER.value, UserRole.SELLER.value, UserRole.CANDIDATE.value,
        UserRole.DEVELOPER.value, UserRole.RECRUITER.value, UserRole.MODERATOR.value,
        UserRole.TEACHER.value, UserRole.STUDENT.value
    }
    if role not in allowed_roles:
        if is_mobile_request:
            return jsonify({'success': False, 'message': 'Please choose a valid account type.'}), 400
        flash('Please choose a valid account type.', 'danger')
        return redirect(url_for('auth.login_register'))
    
    mobile_number = form_data.get('mobile_number')
    secret_question = form_data.get('secret_question')
    secret_answer = form_data.get('secret_answer')
    
    primary_skill = form_data.get('primary_skill')
    primary_skill_experience = form_data.get('primary_skill_experience')

    if is_mobile_request:
        required_values = (username, email, password, confirm_password, secret_question, secret_answer)
        if not all(isinstance(value, str) and value.strip() for value in required_values):
            return jsonify({'success': False, 'message': 'Complete all required registration fields.'}), 400

    if password != confirm_password:
        if is_mobile_request:
            return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth.login_register'))

    user, message = AuthService.register_user(
        username=username, 
        email=email, 
        password=password, 
        role=role,
        mobile_number=mobile_number
    )

    if user:
        try:
            if secret_answer:
                user.secret_question = secret_question
                user.secret_answer_hash = bcrypt.generate_password_hash(secret_answer).decode('utf-8')
            
            user.primary_skill = primary_skill
            user.primary_skill_experience = primary_skill_experience
            db.session.commit()

            # Email Notification Logic
            if not user.is_approved: 
                try:
                    from models.auth import User 
                    admin_email = os.environ.get('ADMIN_EMAIL')
                    if not admin_email:
                        admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()
                        if admin_user:
                            admin_email = admin_user.email
                    
                    if admin_email:
                        send_email(
                            to=[admin_email],
                            subject=f"New User Registration: {username}",
                            template='mail/new_user_admin_notification.html',
                            new_user=user, 
                            now=datetime.utcnow()
                        )
                    else:
                        current_app.logger.error("No ADMIN_EMAIL configured and no admin user found in DB. Registration email skipped.")
                except Exception as e:
                    current_app.logger.error(f"Failed to send registration notification email: {e}")

            if user.is_approved:
                if is_mobile_request:
                    return jsonify({'success': True, 'message': message, 'approved': True}), 201
                flash(message, 'success')
            else:
                if is_mobile_request:
                    return jsonify({'success': True, 'message': message, 'approved': False}), 201
                flash(message, 'info')

        except Exception as e:
            db.session.rollback()
            if is_mobile_request:
                current_app.logger.exception('Mobile account registration profile update failed')
                return jsonify({'success': False, 'message': 'Account details could not be saved.'}), 500
            flash(f"Error updating profile details: {e}", 'danger')
            return redirect(url_for('auth.login_register'))

    else:
        if is_mobile_request:
            return jsonify({'success': False, 'message': message}), 409
        flash(message, 'danger')

    if is_mobile_request:
        return jsonify({'success': True, 'message': message, 'approved': bool(user and user.is_approved)}), 201
    return redirect(url_for('auth.login_register'))

@auth_bp.route('/logout')
@login_required
def logout():
    # Log the logout activity before logging out
    try:
        username = current_user.username
        log_user_action('User Logout', f'User {username} logged out')
    except Exception as e:
        print(f"WARNING: Failed to log logout activity: {e}", file=sys.stderr)
    
    logout_user()
    flash('You have been logged out.', 'info')
    # CORRECTED: Now redirects to main.home instead of auth.login_register
    return redirect(url_for('main.home'))

@auth_bp.route('/reset_password_request')
def reset_password_request():
    return render_template('forgot_password.html')

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    # POST: send reset link via email
    email = request.form.get('email', '').strip()
    from models.auth import User
    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal whether the email exists (security best practice)
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.forgot_password'))

    # Generate a time-limited token (30 minutes)
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = s.dumps(user.email, salt='password-reset-salt')

    reset_url = request.host_url.rstrip('/') + url_for('auth.reset_password', token=token)

    try:
        send_email(
            to=[user.email],
            subject='SourcePoint — Password Reset',
            template='mail/password_reset_email.html',
            user=user,
            reset_url=reset_url
        )
    except Exception as e:
        print(f"WARNING: Failed to send password reset email: {e}")
        flash('Failed to send reset email. Please try again later.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    flash('If an account with that email exists, a password reset link has been sent.', 'info')
    return redirect(url_for('auth.forgot_password'))


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

    try:
        email = s.loads(token, salt='password-reset-salt', max_age=1800)  # 30 min
    except SignatureExpired:
        flash('The password reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash('Invalid password reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    from models.auth import User
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'GET':
        return render_template('reset_password.html', token=token)

    # POST: set new password
    new_password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('auth.reset_password', token=token))

    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth.reset_password', token=token))

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()

    flash('Password reset successful! Please log in with your new password.', 'success')
    return redirect(url_for('auth.login_register'))
