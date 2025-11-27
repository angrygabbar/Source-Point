from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt, limiter
from models import User
from utils import log_user_action, send_email
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login-register', methods=['GET', 'POST'])
@limiter.limit("10 per minute") # Limit login attempts to 10 per minute per IP
def login_register():
    if current_user.is_authenticated: return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        if 'register' in request.form:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            mobile_number = request.form.get('mobile_number')
            if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
                flash('Username or email already exists.', 'danger')
                return redirect(url_for('auth.login_register'))
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            avatar_url = f'https://api.dicebear.com/8.x/initials/svg?seed={username}'
            new_user = User(username=username, email=email, password_hash=hashed_password, role=role, avatar_url=avatar_url, mobile_number=mobile_number)
            if User.query.count() == 0:
                new_user.role = 'admin'
                new_user.is_approved = True
            db.session.add(new_user)
            db.session.commit()

            # --- EMAIL NOTIFICATION FOR ADMINS ---
            admins = User.query.filter_by(role='admin').all()
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                send_email(
                    to=admin_emails,
                    subject="New User Registration - Action Required",
                    template="mail/new_user_admin_notification.html",
                    new_user=new_user,
                    now=datetime.utcnow()
                )

            flash('Account created successfully! Please wait for admin approval.', 'success')
            return redirect(url_for('auth.login_register'))
        if 'login' in request.form:
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            if not user or not bcrypt.check_password_hash(user.password_hash, password):
                flash('Login failed. Please check your email and password.', 'danger')
                return redirect(url_for('auth.login_register'))
            if not user.is_approved:
                flash('Your account has not been approved by an administrator yet.', 'warning')
                return redirect(url_for('auth.login_register'))
            if not user.is_active:
                flash('Your account is blocked by admin. Kindly contact admin by raising a support ticket or connect via WhatsApp messaging.', 'danger')
                return redirect(url_for('auth.login_register'))
            login_user(user, remember=True)
            log_user_action("Login", "User logged in successfully")
            return redirect(url_for('main.dashboard'))
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
@limiter.limit("5 per minute") # Limit password reset attempts
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