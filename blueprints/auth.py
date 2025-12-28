from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.auth import User
from extensions import db, bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_register', methods=['GET', 'POST'])
def login_register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # --- LOGIN LOGIC ---
        if 'login' in request.form:
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()

            if user and bcrypt.check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact support.', 'danger')
                    return redirect(url_for('auth.login_register'))
                
                if not user.is_approved:
                    flash('Your account is pending approval by an admin.', 'warning')
                    return redirect(url_for('auth.login_register'))

                login_user(user, remember=True)
                
                # Role-based Redirection Map
                # UPDATED: 'admin' now points to 'admin_core.admin_dashboard'
                role_map = {
                    'admin': 'admin_core.admin_dashboard',
                    'developer': 'developer.developer_dashboard',
                    'moderator': 'moderator.moderator_dashboard',
                    'candidate': 'candidate.candidate_dashboard',
                    'buyer': 'buyer.buyer_dashboard',
                    'seller': 'seller.seller_dashboard',
                    'recruiter': 'recruiter.recruiter_dashboard'
                }
                
                next_page = request.args.get('next')
                target = role_map.get(user.role, 'main.dashboard')
                
                return redirect(next_page) if next_page else redirect(url_for(target))
            else:
                flash('Login failed. Check your email and password.', 'danger')

        # --- REGISTER LOGIC ---
        elif 'register' in request.form:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            mobile_number = request.form.get('mobile_number')

            if User.query.filter_by(email=email).first():
                flash('Email already exists.', 'danger')
            elif User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
            else:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                # Admin is auto-approved, others are pending
                is_approved = True if role == 'admin' else False
                
                # Generate Avatar
                avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={username}"

                new_user = User(
                    username=username, 
                    email=email, 
                    password_hash=hashed_password, 
                    role=role, 
                    mobile_number=mobile_number,
                    is_approved=is_approved,
                    avatar_url=avatar_url
                )
                db.session.add(new_user)
                db.session.commit()
                
                if is_approved:
                    flash('Account created! You can now login.', 'success')
                else:
                    flash('Account created! Please wait for admin approval.', 'info')
                
                return redirect(url_for('auth.login_register'))

    return render_template('login_register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')