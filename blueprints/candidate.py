from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.hiring import JobOpening, JobApplication, CodeSnippet
from services.hiring_service import HiringService
from utils import role_required, log_user_action
from datetime import datetime, timedelta
from enums import UserRole # --- IMPORT ENUMS ---

candidate_bp = Blueprint('candidate', __name__)

@candidate_bp.route('/candidate')
@login_required
@role_required(UserRole.CANDIDATE.value) # --- USE ENUM ---
def candidate_dashboard():
    # Fetch Admin and Developers for messaging
    target_roles = [UserRole.ADMIN.value, UserRole.DEVELOPER.value]
    messageable_users = User.query.filter(User.role.in_(target_roles)).all()
    
    open_jobs = JobOpening.query.filter_by(is_open=True).order_by(JobOpening.created_at.desc()).all()
    my_applications = JobApplication.query.filter_by(user_id=current_user.id).all()
    applied_job_ids = [app.job_id for app in my_applications]
    
    return render_template('candidate_dashboard.html',
                           messageable_users=messageable_users,
                           open_jobs=open_jobs,
                           my_applications=my_applications,
                           applied_job_ids=applied_job_ids)

@candidate_bp.route('/code_test')
@login_required
@role_required(UserRole.CANDIDATE.value)
def code_test():
    now = datetime.utcnow()
    
    # 1. Check if test is assigned
    if not current_user.assigned_problem:
        message = "No test has been assigned to you yet."
        return render_template('test_locked.html', message=message)
    
    # 2. Check if test hasn't started yet
    if current_user.test_start_time and now < current_user.test_start_time:
        ist_start_time = current_user.test_start_time + timedelta(hours=5, minutes=30)
        message = f"Your test has been assigned but is not yet active. It will be available starting {ist_start_time.strftime('%b %d, %Y at %I:%M %p')} IST."
        return render_template('test_locked.html', message=message)

    # 3. Check if test has ended (Lazy Update Logic)
    if current_user.test_end_time and now > current_user.test_end_time:
        if not current_user.test_completed:
            current_user.test_completed = True
            db.session.commit()
            
        ist_end_time = current_user.test_end_time + timedelta(hours=5, minutes=30)
        message = f"The deadline for your assigned test has passed. The test was available until {ist_end_time.strftime('%b %d, %Y at %I:%M %p')} IST."
        return render_template('test_locked.html', message=message)

    target_roles = [UserRole.ADMIN.value, UserRole.DEVELOPER.value]
    messageable_users = User.query.filter(User.role.in_(target_roles)).all()
    return render_template('code_test.html', messageable_users=messageable_users)

@candidate_bp.route('/apply_job/<int:job_id>', methods=['POST'])
@login_required
@role_required(UserRole.CANDIDATE.value)
def apply_job(job_id):
    resume_file = request.files.get('resume')
    
    # Use Service with Global Error Handling in app.py
    try:
        success, msg = HiringService.apply_for_job(current_user, job_id, resume_file)
        if success:
            log_user_action("Apply Job", f"Applied for job ID: {job_id}")
            flash(msg, 'success')
    except Exception as e:
        # Service might raise BusinessValidationError, handled by app.py, 
        # but for simple boolean returns we catch here or let it bubble up.
        # Since HiringService currently returns (bool, str), we check success.
        flash(str(e), 'danger')
        
    return redirect(url_for('candidate.candidate_dashboard'))

@candidate_bp.route('/submit_code_test', methods=['POST'])
@login_required
@role_required(UserRole.CANDIDATE.value)
def submit_code_test():
    try:
        success, msg = HiringService.submit_code_test(
            candidate=current_user,
            recipient_id=request.form.get('recipient_id'),
            code=request.form.get('code'),
            output=request.form.get('output')
        )
        if success:
            log_user_action("Submit Code Test", f"Submitted code test")
            flash(msg, 'success')
    except Exception as e:
        flash(str(e), 'danger')
        
    return redirect(url_for('candidate.code_test'))

@candidate_bp.route('/share_code', methods=['POST'])
@login_required
@role_required(UserRole.CANDIDATE.value)
def share_code():
    try:
        success, msg = HiringService.share_code_snippet(
            sender_id=current_user.id,
            recipient_id=request.form.get('recipient_id'),
            code=request.form.get('java_code')
        )
        if success:
            log_user_action("Share Code", f"Shared code snippet")
            flash(msg, 'success')
    except Exception as e:
        flash(str(e), 'danger')
        
    return redirect(url_for('candidate.candidate_dashboard'))

@candidate_bp.route('/delete_snippet/<int:snippet_id>')
@login_required
def delete_snippet(snippet_id):
    snippet = CodeSnippet.query.get_or_404(snippet_id)
    if snippet.recipient_id == current_user.id:
        db.session.delete(snippet)
        db.session.commit()
        flash('Code snippet deleted successfully.', 'success')
    else:
        flash('You do not have permission to delete this snippet.', 'danger')
    return redirect(url_for('main.dashboard'))