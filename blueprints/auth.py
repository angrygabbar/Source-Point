from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt, limiter
from models.auth import User
from services.auth_service import AuthService  # <-- Import Service
from utils import log_user_action, send_email
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login-register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login_register():
    # --- Redirect Authenticated Users ---
    if current_user.is_authenticated:
        role_map = {
            'seller': 'seller.seller_dashboard',
            'admin': 'admin.admin_dashboard',
            'buyer': 'buyer.buyer_dashboard',
            'recruiter': 'recruiter.recruiter_dashboard',
            'candidate': 'candidate.candidate_dashboard',
            'developer': 'developer.developer_dashboard',
            'moderator': 'moderator.moderator_dashboard'
        }
        return redirect(url_for(role_map.get(current_user.role, 'main.dashboard')))

    if request.method == 'POST':
        # --- REGISTRATION ---
        if 'register' in request.form:
            user, msg = AuthService.register_user(
                username=request.form.get('username'),
                email=request.form.get('email'),
                password=request.form.get('password'),
                role=request.form.get('role'),
                mobile_number=request.form.get('mobile_number')
            )
            
            if user:
                # Send Admin Notification (Logic remains in controller or moves to event listener)
                try:
                    admins = User.query.filter_by(role='admin').all()
                    admin_emails = [a.email for a in admins]
                    if admin_emails:
                        send_email(
                            to=admin_emails,
                            subject="New User Registration - Action Required",
                            template="mail/new_user_admin_notification.html",
                            new_user=user,
                            now=datetime.utcnow()
                        )
                except Exception as e:
                    print(f"Notification Error: {e}")

                flash(msg, 'success')
            else:
                flash(msg, 'danger')
            
            return redirect(url_for('auth.login_register'))

        # --- LOGIN ---
        if 'login' in request.form:
            user, msg = AuthService.authenticate_user(
                email=request.form.get('email'),
                password=request.form.get('password')
            )
            
            if user:
                login_user(user, remember=True)
                log_user_action("Login", "User logged in successfully")
                
                role_map = {
                    'seller': 'seller.seller_dashboard',
                    'admin': 'admin.admin_dashboard',
                    'buyer': 'buyer.buyer_dashboard',
                    'recruiter': 'recruiter.recruiter_dashboard',
                    'candidate': 'candidate.candidate_dashboard',
                    'developer': 'developer.developer_dashboard',
                    'moderator': 'moderator.moderator_dashboard'
                }
                return redirect(url_for(role_map.get(user.role, 'main.dashboard')))
            else:
                flash(msg, 'danger')
                return redirect(url_for('auth.login_register'))

    return render_template('login_register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_user_action("Logout", "User logged out")
    logout_user()
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user and user.secret_question:
            return redirect(url_for('auth.reset_with_question', user_id=user.id))
        else:
            flash('No account found with that email or no secret question is set.', 'warning')
            return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset_with_question/<int:user_id>', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_with_question(user_id):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        answer = request.form.get('secret_answer')
        new_password = request.form.get('new_password')
        if user.secret_answer_hash and bcrypt.check_password_hash(user.secret_answer_hash, answer):
            user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login_register'))
        else:
            flash('Your secret answer was incorrect. Please try again.', 'danger')
            return redirect(url_for('auth.reset_with_question', user_id=user.id))
    return render_template('reset_with_question.html', user=user)