from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from extensions import db, bcrypt
from utils import send_email, log_user_action
from datetime import datetime
from enums import UserRole
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
            UserRole.RECRUITER.value: 'recruiter.recruiter_dashboard'
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
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', UserRole.CANDIDATE.value)
    
    mobile_number = request.form.get('mobile_number')
    secret_question = request.form.get('secret_question')
    secret_answer = request.form.get('secret_answer')
    
    primary_skill = request.form.get('primary_skill')
    primary_skill_experience = request.form.get('primary_skill_experience')

    if password != confirm_password:
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
                    admin_email = current_app.config.get('ADMIN_EMAIL')
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
                except Exception as e:
                    print(f"WARNING: Failed to send Email: {e}")

            if user.is_approved:
                flash(message, 'success')
            else:
                flash(message, 'info')

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating profile details: {e}", 'danger')
            return redirect(url_for('auth.login_register'))

    else:
        flash(message, 'danger')

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

@auth_bp.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')