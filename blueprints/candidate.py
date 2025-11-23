from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, JobOpening, JobApplication, CodeTestSubmission, CodeSnippet
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta

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
    if not current_user.assigned_problem:
        message = "No test has been assigned to you yet."
        return render_template('test_locked.html', message=message)
    if current_user.test_start_time and now < current_user.test_start_time:
        ist_start_time = current_user.test_start_time + timedelta(hours=5, minutes=30)
        message = f"Your test has been assigned but is not yet active. It will be available starting {ist_start_time.strftime('%b %d, %Y at %I:%M %p')} IST."
        return render_template('test_locked.html', message=message)
    if current_user.test_end_time and now > current_user.test_end_time:
        ist_end_time = current_user.test_end_time + timedelta(hours=5, minutes=30)
        message = f"The deadline for your assigned test has passed. The test was available until {ist_end_time.strftime('%b %d, %Y at %I:%M %p')} IST."
        return render_template('test_locked.html', message=message)
    messageable_users = User.query.filter(User.role.in_(['admin', 'developer'])).all()
    return render_template('code_test.html', messageable_users=messageable_users)

@candidate_bp.route('/apply_job/<int:job_id>')
@login_required
@role_required('candidate')
def apply_job(job_id):
    job = JobOpening.query.get_or_404(job_id)
    existing_application = JobApplication.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    if existing_application:
        flash('You have already applied for this job.', 'warning')
    else:
        new_application = JobApplication(user_id=current_user.id, job_id=job.id)
        db.session.add(new_application)
        db.session.commit()

        admins = User.query.filter_by(role='admin').all()
        admin_emails = [admin.email for admin in admins]
        candidate = User.query.get(current_user.id)

        send_email(to=admin_emails, subject=f"New Job Application: {job.title}", template="mail/application_submitted_admin.html", candidate=candidate, job=job, now=datetime.utcnow())
        send_email(to=candidate.email, subject=f"Application Received: {job.title}", template="mail/application_submitted_candidate.html", candidate=candidate, job=job, now=datetime.utcnow())
        
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