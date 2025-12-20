from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, JobOpening, JobApplication, CodeTestSubmission, CodeSnippet
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
import cloudinary.uploader

candidate_bp = Blueprint('candidate', __name__)

@candidate_bp.route('/candidate')
@login_required
@role_required('candidate')
def candidate_dashboard():
    messageable_users = User.query.filter(User.role.in_(['admin', 'developer'])).all()
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
@role_required('candidate')
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
        # If the test is expired but database still says "not completed", update it now.
        if not current_user.test_completed:
            current_user.test_completed = True
            db.session.commit()
            
        ist_end_time = current_user.test_end_time + timedelta(hours=5, minutes=30)
        message = f"The deadline for your assigned test has passed. The test was available until {ist_end_time.strftime('%b %d, %Y at %I:%M %p')} IST."
        return render_template('test_locked.html', message=message)

    messageable_users = User.query.filter(User.role.in_(['admin', 'developer'])).all()
    return render_template('code_test.html', messageable_users=messageable_users)

@candidate_bp.route('/apply_job/<int:job_id>', methods=['POST'])
@login_required
@role_required('candidate')
def apply_job(job_id):
    job = JobOpening.query.get_or_404(job_id)
    existing_application = JobApplication.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    
    if existing_application:
        flash('You have already applied for this job.', 'warning')
        return redirect(url_for('candidate.candidate_dashboard'))

    # Resume Upload Logic
    resume_url = None
    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            if file and file.filename.endswith('.pdf'):
                try:
                    upload_result = cloudinary.uploader.upload(
                        file, 
                        resource_type="raw", 
                        folder="application_resumes",
                        public_id=f"app_resume_{current_user.id}_{job.id}"
                    )
                    resume_url = upload_result['secure_url']
                except Exception as e:
                    flash(f'Resume upload failed: {str(e)}', 'danger')
                    return redirect(url_for('candidate.candidate_dashboard'))
            else:
                flash('Only PDF files are allowed.', 'danger')
                return redirect(url_for('candidate.candidate_dashboard'))
    
    # Fallback to profile resume if none uploaded
    if not resume_url and current_user.resume_filename:
        resume_url = current_user.resume_filename

    if not resume_url:
        flash('Please upload a resume to apply.', 'danger')
        return redirect(url_for('candidate.candidate_dashboard'))

    new_application = JobApplication(user_id=current_user.id, job_id=job.id, resume_url=resume_url)
    db.session.add(new_application)
    db.session.commit()

    # Notifications
    admins = User.query.filter_by(role='admin').all()
    recruiters = User.query.filter_by(role='recruiter').all()
    
    # Notify admins and recruiters
    recipient_emails = [u.email for u in admins + recruiters]
    
    if recipient_emails:
        admin_user = User.query.filter_by(role='admin').first()
        send_email(to=recipient_emails, subject=f"New Job Application: {job.title}", template="mail/application_submitted_admin.html", admin=admin_user, candidate=current_user, job=job, now=datetime.utcnow())
    
    send_email(to=current_user.email, subject=f"Application Received: {job.title}", template="mail/application_submitted_candidate.html", candidate=current_user, job=job, now=datetime.utcnow())
    
    log_user_action("Apply Job", f"Applied for job: {job.title}")
    flash('You have successfully applied for the job!', 'success')
    return redirect(url_for('candidate.candidate_dashboard'))

@candidate_bp.route('/submit_code_test', methods=['POST'])
@login_required
@role_required('candidate')
def submit_code_test():
    recipient_id = request.form.get('recipient_id')
    code = request.form.get('code')
    output = request.form.get('output')
    language = "java"
    if not recipient_id or not code.strip():
        flash('Please select a recipient and provide code.', 'danger')
    else:
        submission = CodeTestSubmission(candidate_id=current_user.id, recipient_id=recipient_id, code=code, output=output, language=language)
        db.session.add(submission)
        db.session.commit()

        recipient = User.query.get(recipient_id)
        candidate = User.query.get(current_user.id)
        problem_title = candidate.assigned_problem.title if candidate.assigned_problem else None

        send_email(
            to=recipient.email, cc=[candidate.email], subject=f"New Code Submission from {candidate.username}",
            template="mail/submit_code_test.html", candidate=candidate, recipient=recipient,
            problem_title=problem_title, language=language, code=code, output=output, now=datetime.utcnow()
        )
        log_user_action("Submit Code Test", f"Submitted code test to {recipient.username}")
        flash('Your code test has been submitted successfully and sent via email!', 'success')
    return redirect(url_for('candidate.code_test'))

@candidate_bp.route('/share_code', methods=['POST'])
@login_required
@role_required('candidate')
def share_code():
    recipient_id = request.form.get('recipient_id')
    code = request.form.get('java_code')
    language = "java"
    if not recipient_id or not code or not code.strip():
        flash('Please select a recipient and provide code.', 'danger')
    else:
        new_snippet = CodeSnippet(sender_id=current_user.id, recipient_id=recipient_id, code=code, language=language)
        db.session.add(new_snippet)
        db.session.commit()
        log_user_action("Share Code", f"Shared code snippet with user ID {recipient_id}")
        flash('Code snippet shared successfully!', 'success')
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