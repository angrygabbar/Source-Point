from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from extensions import db, bcrypt, cache
from models import User, Message, AffiliateAd, LearningContent, JobOpening, JobApplication
from utils import role_required, log_user_action, send_email
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import cloudinary.uploader

main_bp = Blueprint('main', __name__)

SECRET_QUESTIONS = [
    "What was your first pet's name?",
    "What is your mother's maiden name?",
    "What was the name of your elementary school?",
    "In what city were you born?",
    "What is your favorite book?"
]

@main_bp.route('/')
# @cache.cached(timeout=600) # <-- FIXED: Caching removed so the page updates immediately on logout
def home(): 
    return render_template('home.html')

@main_bp.route('/offers')
@cache.cached(timeout=300) # Cache offers for 5 minutes
def offers():
    ads = AffiliateAd.query.all()
    return render_template('offers.html', ads=ads)

@main_bp.route('/contact')
def contact(): return render_template('contact.html')

@main_bp.route('/contact_submit', methods=['POST'])
def submit_contact():
    name = request.form.get('Name')
    email = request.form.get('Email')
    query = request.form.get('Query')
    
    if not name or not email or not query:
        flash('All fields are required.', 'danger')
        return redirect(url_for('main.contact'))

    subject = f"New Support Request from {name}"
    body = f"""
    <h3>Support Request</h3>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Issue Description:</strong></p>
    <p>{query}</p>
    """
    
    admin_email = "admin@sourcepoint.in"
    admin_user = User.query.filter_by(role='admin').first()
    
    if not admin_user:
        class DummyUser:
            username = "Admin"
            email = admin_email
        admin_user = DummyUser()

    send_email(to=admin_email, subject=subject, template="mail/broadcast.html", user=admin_user, body=body)
    
    flash('Your support request has been sent successfully!', 'success')
    return redirect(url_for('main.contact'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin': return redirect(url_for('admin.admin_dashboard'))
    elif current_user.role == 'developer': return redirect(url_for('developer.developer_dashboard'))
    elif current_user.role == 'moderator': return redirect(url_for('moderator.moderator_dashboard'))
    elif current_user.role == 'buyer': return redirect(url_for('buyer.buyer_dashboard'))
    else: return redirect(url_for('candidate.candidate_dashboard'))

@main_bp.route('/messages')
@login_required
def messages():
    messageable_users_dict = {}
    now = datetime.utcnow()

    if current_user.role == 'candidate':
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            messageable_users_dict[admin.id] = admin
        if current_user.test_start_time and current_user.test_end_time and \
           current_user.test_start_time <= now <= current_user.test_end_time and \
           current_user.moderator_id:
            moderator = User.query.get(current_user.moderator_id)
            if moderator:
                messageable_users_dict[moderator.id] = moderator

    elif current_user.role == 'moderator':
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            messageable_users_dict[admin.id] = admin

        assigned_candidates = User.query.filter(
            User.moderator_id == current_user.id,
            User.test_start_time <= now,
            User.test_end_time >= now
        ).all()
        for candidate in assigned_candidates:
            messageable_users_dict[candidate.id] = candidate

    elif current_user.role in ['admin', 'developer']:
        users = User.query.filter(User.id != current_user.id).all()
        for user in users:
            messageable_users_dict[user.id] = user

    messageable_users = list(messageable_users_dict.values())
    return render_template('messages.html', messageable_users=messageable_users)

@main_bp.route('/get_conversation/<int:other_user_id>')
@login_required
def get_conversation(other_user_id):
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == other_user_id),
            (Message.sender_id == other_user_id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    conversation = [
        {
            'sender_id': msg.sender_id,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%b %d, %I:%M %p')
        } for msg in messages
    ]
    return jsonify(conversation)

@main_bp.route('/send_message', methods=['POST'])
@login_required
def send_message():
    recipient_id = request.form.get('recipient_id')
    body = request.form.get('body')
    if not recipient_id or not body:
        flash('Message cannot be empty.', 'danger')
    else:
        msg = Message(sender_id=current_user.id, recipient_id=recipient_id, body=body)
        db.session.add(msg)
        db.session.commit()
        flash('Message sent!', 'success')
    return redirect(url_for('main.messages'))

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', secret_questions=SECRET_QUESTIONS)

@main_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.mobile_number = request.form.get('mobile_number')
    current_user.primary_skill = request.form.get('primary_skill')
    current_user.primary_skill_experience = request.form.get('primary_skill_experience')
    current_user.secondary_skill = request.form.get('secondary_skill')
    current_user.secondary_skill_experience = request.form.get('secondary_skill_experience')
    
    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            if file and file.filename.endswith('.pdf'):
                try:
                    upload_result = cloudinary.uploader.upload(
                        file, 
                        resource_type="raw",  
                        folder="resumes",      
                        public_id=f"resume_{current_user.id}" 
                    )
                    current_user.resume_filename = upload_result['secure_url']
                except Exception as e:
                    flash(f'Upload failed: {str(e)}', 'danger')
                    return redirect(url_for('main.profile'))
            else:
                flash('Only PDF files are allowed for resumes.', 'danger')
                return redirect(url_for('main.profile'))
                
    db.session.commit()
    log_user_action("Update Profile", "User updated their profile details")
    flash('Your profile has been updated successfully!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/update_security_question', methods=['POST'])
@login_required
def update_security_question():
    secret_question = request.form.get('secret_question')
    secret_answer = request.form.get('secret_answer')
    if secret_question and secret_answer:
        current_user.secret_question = secret_question
        current_user.secret_answer_hash = bcrypt.generate_password_hash(secret_answer).decode('utf-8')
        db.session.commit()
        log_user_action("Update Security Question", "Updated security question")
        flash('Your security question has been updated.', 'success')
    else:
        flash('Please select a question and provide an answer.', 'danger')
    return redirect(url_for('main.profile'))

@main_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not bcrypt.check_password_hash(current_user.password_hash, old_password):
        flash('Old password is not correct.', 'danger')
        return redirect(url_for('main.profile'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('main.profile'))

    current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    log_user_action("Change Password", "User changed their password")
    flash('Your password has been updated successfully!', 'success')
    return redirect(url_for('main.profile'))

# --- LEARNING ROUTES ---
@main_bp.route('/learning')
@login_required
@role_required(['candidate', 'admin', 'developer'])
@cache.cached(timeout=600) # Cache learning hub for 10 minutes
def learning():
    return render_template('learning.html')

@main_bp.route('/learn/<language>')
@login_required
@role_required(['candidate', 'admin', 'developer'])
@cache.cached(timeout=300) # Cache individual tutorials
def learn_language(language):
    supported_languages = ['java', 'cpp', 'c', 'sql', 'dbms', 'plsql', 'mysql']
    if language in supported_languages:
        learning_content = LearningContent.query.get(language)
        if not learning_content:
            learning_content = LearningContent(id=language, content=f'<h1>{language.upper()} Tutorial</h1><p>Content coming soon...</p>')
            db.session.add(learning_content)
            db.session.commit()
        
        log_user_action("View Learning Content", f"Viewed {language} tutorial")
        return render_template('learn_page.html', language=language, page_content=learning_content.content)
    else:
        flash('The requested learning page does not exist.', 'danger')
        return redirect(url_for('main.learning'))