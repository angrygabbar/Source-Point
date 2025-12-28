from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.auth import User
from extensions import db, bcrypt
from utils import send_email
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_register', methods=['GET'])
def login_register():
    """Renders the combined Login/Register page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login_register.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handles the Login form submission."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember-me') else False

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        # CHECK 1: Is user active? (Blocked users)
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return redirect(url_for('auth.login_register'))
        
        # CHECK 2: Is user approved? (Pending users)
        if not user.is_approved:
            flash('Your account is pending approval by an admin.', 'warning')
            return redirect(url_for('auth.login_register'))

        login_user(user, remember=remember)
        
        # Role-based Redirection Map
        role_map = {
            'admin': 'admin_core.admin_dashboard',
            'developer': 'developer.developer_dashboard',
            'moderator': 'moderator.moderator_dashboard',
            'candidate': 'candidate.candidate_dashboard',
            'buyer': 'buyer.buyer_dashboard',
            'seller': 'seller.seller_dashboard',
            'recruiter': 'recruiter.recruiter_dashboard'
        }
        
        # Handle 'next' URL safely
        next_page = request.args.get('next')
        if next_page and not next_page.startswith('/'):
            next_page = None # Prevent open redirects
            
        target = role_map.get(user.role, 'main.dashboard')
        return redirect(next_page) if next_page else redirect(url_for(target))
    else:
        flash('Login failed. Check your email and password.', 'danger')
        return redirect(url_for('auth.login_register'))

@auth_bp.route('/register', methods=['POST'])
def register():
    """Handles the Registration form submission with extended fields."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # 1. Fetch Form Data
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', 'candidate')
    
    # Extended Profile Fields
    mobile_number = request.form.get('mobile_number')
    secret_question = request.form.get('secret_question')
    secret_answer = request.form.get('secret_answer')
    
    # Skill Fields (Optional, mostly for Candidates/Devs)
    primary_skill = request.form.get('primary_skill')
    primary_skill_experience = request.form.get('primary_skill_experience')

    # 2. Validation
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth.login_register'))

    if User.query.filter_by(email=email).first():
        flash('Email already registered.', 'danger')
        return redirect(url_for('auth.login_register'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already taken.', 'danger')
        return redirect(url_for('auth.login_register'))

    # 3. Secure Data
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    secret_hash = bcrypt.generate_password_hash(secret_answer).decode('utf-8') if secret_answer else None
    
    # Generate default avatar
    avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={username}"

    # --- APPROVAL LOGIC ---
    # Default: User is NOT approved (must wait for admin)
    is_approved = False
    
    # EXCEPTION: If this is the FIRST user in the system, make them Admin & Approved
    if User.query.count() == 0:
        is_approved = True
        role = 'admin'

    # 4. Create User
    new_user = User(
        username=username, 
        email=email, 
        password_hash=hashed_password, 
        role=role, 
        mobile_number=mobile_number,
        is_approved=is_approved,
        avatar_url=avatar_url,
        secret_question=secret_question,
        secret_answer_hash=secret_hash,
        primary_skill=primary_skill,
        primary_skill_experience=primary_skill_experience
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()

        # --- EMAIL NOTIFICATION BLOCK (FIXED) ---
        try:
            # Only notify if they need approval
            if not is_approved: 
                # STEP 1: Try to get admin email from Config
                admin_email = current_app.config.get('ADMIN_EMAIL')
                
                # STEP 2: If not in config, find the first Admin user in the Database
                if not admin_email:
                    admin_user = User.query.filter_by(role='admin').first()
                    if admin_user:
                        admin_email = admin_user.email
                
                # STEP 3: Fallback (Just in case no admin exists yet, though unlikely)
                if not admin_email:
                    admin_email = 'admin@sourcepoint.com'

                send_email(
                    to=[admin_email],
                    subject=f"New User Registration Request: {username}",
                    template='mail/new_user_admin_notification.html',
                    new_user=new_user, 
                    now=datetime.utcnow()
                )
        except Exception as e:
            # Log error but don't stop the user creation
            print(f"Error sending admin notification email: {e}")

        if is_approved:
            flash('Account created! Since you are the first user, you are now Admin.', 'success')
        else:
            flash('Account created successfully! Please wait for admin approval.', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating account: {str(e)}', 'danger')

    return redirect(url_for('auth.login_register'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_register'))

@auth_bp.route('/reset_password_request')
def reset_password_request():
    """Route linked from the Login page 'Forgot Password?' link."""
    return render_template('forgot_password.html')

@auth_bp.route('/forgot_password')
def forgot_password():
    """Legacy route for backward compatibility."""
    return render_template('forgot_password.html')