from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from extensions import db, bcrypt
from utils import send_email
from datetime import datetime
from enums import UserRole
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_register', methods=['GET'])
def login_register():
    """Renders the combined Login/Register page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login_register.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handles the Login form submission using AuthService."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember-me') else False

    # --- REFACTOR: Logic moved to AuthService ---
    # This handles checking password, is_active, and is_approved
    user, message = AuthService.authenticate_user(email, password)

    if user:
        login_user(user, remember=remember)
        
        # Role-based Redirection Map using Enums
        role_map = {
            UserRole.ADMIN.value: 'admin_core.admin_dashboard',
            UserRole.DEVELOPER.value: 'developer.developer_dashboard',
            UserRole.MODERATOR.value: 'moderator.moderator_dashboard',
            UserRole.CANDIDATE.value: 'candidate.candidate_dashboard',
            UserRole.BUYER.value: 'buyer.buyer_dashboard',
            UserRole.SELLER.value: 'seller.seller_dashboard',
            UserRole.RECRUITER.value: 'recruiter.recruiter_dashboard'
        }
        
        # Handle 'next' URL safely to prevent open redirects
        next_page = request.args.get('next')
        if next_page and not next_page.startswith('/'):
            next_page = None 
            
        target = role_map.get(user.role, 'main.dashboard')
        return redirect(next_page) if next_page else redirect(url_for(target))
    else:
        # Message contains specific error (e.g., "Account blocked", "Pending approval")
        flash(message, 'danger')
        return redirect(url_for('auth.login_register'))

@auth_bp.route('/register', methods=['POST'])
def register():
    """Handles the Registration form submission."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # 1. Fetch Form Data
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', UserRole.CANDIDATE.value)
    
    # Extended Profile Fields
    mobile_number = request.form.get('mobile_number')
    secret_question = request.form.get('secret_question')
    secret_answer = request.form.get('secret_answer')
    
    # Skill Fields
    primary_skill = request.form.get('primary_skill')
    primary_skill_experience = request.form.get('primary_skill_experience')

    # 2. Basic Validation
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth.login_register'))

    # 3. Call Service to create the base user
    user, message = AuthService.register_user(
        username=username, 
        email=email, 
        password=password, 
        role=role,
        mobile_number=mobile_number
    )

    if user:
        # 4. Update Extended Fields (Not handled by Service basic registration)
        try:
            # Handle Security Question Hashing
            if secret_answer:
                user.secret_question = secret_question
                user.secret_answer_hash = bcrypt.generate_password_hash(secret_answer).decode('utf-8')
            
            # Handle Skills
            user.primary_skill = primary_skill
            user.primary_skill_experience = primary_skill_experience
            db.session.commit()

            # 5. RESTORED: Email Notification Logic
            # Only notify admins if the user is NOT auto-approved
            if not user.is_approved: 
                try:
                    # Find an Admin to notify
                    from models.auth import User # Local import to avoid circular dependency
                    admin_email = current_app.config.get('ADMIN_EMAIL')
                    
                    if not admin_email:
                        admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()
                        if admin_user:
                            admin_email = admin_user.email
                    
                    if admin_email:
                        send_email(
                            to=[admin_email],
                            subject=f"New User Registration Request: {username}",
                            template='mail/new_user_admin_notification.html',
                            new_user=user, 
                            now=datetime.utcnow()
                        )
                except Exception as e:
                    print(f"WARNING: Failed to send Admin Notification Email: {e}")
                    traceback.print_exc()

            if user.is_approved:
                flash(message, 'success') # "Account created... you are Admin"
            else:
                flash(message, 'info') # "Wait for approval"

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating profile details: {e}", 'danger')
            return redirect(url_for('auth.login_register'))

    else:
        # Registration failed (Duplicate user, etc.)
        flash(message, 'danger')

    return redirect(url_for('auth.login_register'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_register'))

@auth_bp.route('/reset_password_request')
def reset_password_request():
    return render_template('forgot_password.html')

@auth_bp.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')