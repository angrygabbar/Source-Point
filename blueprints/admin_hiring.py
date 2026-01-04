from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.hiring import JobApplication, JobOpening, CodeSnippet, Feedback, CodeTestSubmission, ModeratorAssignmentHistory
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
from enums import UserRole, ApplicationStatus # --- IMPORT ENUMS ---

admin_hiring_bp = Blueprint('admin_hiring', __name__, url_prefix='/admin/hiring')

@admin_hiring_bp.route('/dashboard')
@login_required
@role_required(UserRole.ADMIN.value) # --- USE ENUM ---
def admin_hiring_dashboard():
    pending_apps_count = JobApplication.query.filter_by(status=ApplicationStatus.PENDING.value).count()
    
    hiring_roles = [
        UserRole.CANDIDATE.value, 
        UserRole.DEVELOPER.value, 
        UserRole.MODERATOR.value, 
        UserRole.RECRUITER.value
    ]
    pending_hiring_users = User.query.filter(
        User.is_approved == False,
        User.role.in_(hiring_roles)
    ).all()
    
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).limit(20).all()
    
    scheduled_candidates = User.query.filter(
        User.role == UserRole.CANDIDATE.value,
        User.problem_statement_id != None,
        User.moderator_id == None
    ).all()

    assigned_candidates = User.query.filter(
        User.role == UserRole.CANDIDATE.value,
        User.moderator_id.isnot(None)
    ).order_by(User.test_start_time.asc()).limit(20).all()
    
    mod_ids = list(set([c.moderator_id for c in assigned_candidates if c.moderator_id]))
    moderators_map = {m.id: m for m in User.query.filter(User.id.in_(mod_ids)).all()}
    all_moderators = User.query.filter_by(role=UserRole.MODERATOR.value).all()

    received_snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id)\
        .order_by(CodeSnippet.timestamp.desc()).limit(5).all()

    return render_template('admin_hiring_dashboard.html',
                           pending_apps_count=pending_apps_count,
                           pending_hiring_users=pending_hiring_users,
                           applications=applications,
                           scheduled_candidates=scheduled_candidates,
                           assigned_candidates=assigned_candidates,
                           moderators_map=moderators_map,
                           all_moderators=all_moderators,
                           received_snippets=received_snippets)

@admin_hiring_bp.route('/job/post', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def post_job():
    title = request.form.get('job_title')
    description = request.form.get('job_description')
    if title and description:
        new_job = JobOpening(title=title, description=description)
        db.session.add(new_job)
        db.session.commit()
        log_user_action("Post Job", f"Posted new job opening: {title}")
        flash('New job opening has been posted.', 'success')
    else:
        flash('Job title and description are required.', 'danger')
    
    # IMPROVEMENT: Redirect back to Hiring Dashboard
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/application/accept/<int:app_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def accept_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = ApplicationStatus.ACCEPTED.value # --- USE ENUM ---
    db.session.commit()

    send_email(
        to=application.candidate.email,
        subject=f"Update on your application for {application.job.title}",
        template="mail/application_status_update.html",
        candidate=application.candidate, job=application.job, status="Accepted", now=datetime.utcnow()
    )
    
    log_user_action("Accept Application", f"Accepted application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been accepted.", 'success')
    
    # IMPROVEMENT: Redirect back to Hiring Dashboard
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/application/reject/<int:app_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def reject_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = ApplicationStatus.REJECTED.value # --- USE ENUM ---
    db.session.commit()

    send_email(
        to=application.candidate.email,
        subject=f"Update on your application for {application.job.title}",
        template="mail/application_status_update.html",
        candidate=application.candidate, job=application.job, status="Rejected", now=datetime.utcnow()
    )
    
    log_user_action("Reject Application", f"Rejected application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been rejected.", 'warning')
    
    # IMPROVEMENT: Redirect back to Hiring Dashboard
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/candidate/add_contact', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def add_contact_for_candidate():
    candidate_id = request.form.get('candidate_id')
    developer_id = request.form.get('developer_id')
    candidate = User.query.get(candidate_id)
    developer = User.query.get(developer_id)
    
    if candidate and developer and developer.role == UserRole.DEVELOPER.value:
        candidate.allowed_contacts.append(developer)
        db.session.commit()
        log_user_action("Link Contacts", f"Linked developer {developer.username} to {candidate.username}")
        flash(f'Developer {developer.username} added to {candidate.username}\'s contacts.', 'success')
    else:
        flash('Invalid selection. Please try again.', 'danger')
        
    # IMPROVEMENT: Redirect back to Hiring Dashboard
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/moderator/assign', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def assign_moderator():
    candidate_id = request.form.get('candidate_id')
    moderator_id = request.form.get('moderator_id')

    candidate = User.query.get(candidate_id)
    moderator = User.query.get(moderator_id)

    if not candidate or not moderator or moderator.role != UserRole.MODERATOR.value:
        flash("Invalid user selection.", 'danger')
        return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

    if not all([candidate.assigned_problem, candidate.test_start_time, candidate.test_end_time]):
        flash(f"Error: Candidate {candidate.username} does not have a complete test schedule.", 'danger')
        return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

    candidate.moderator_id = moderator_id
    db.session.commit()

    history_record = ModeratorAssignmentHistory(
        candidate_id=candidate.id, moderator_id=moderator.id, problem_statement_id=candidate.problem_statement_id
    )
    db.session.add(history_record)
    db.session.commit()
    
    log_user_action("Assign Moderator", f"Assigned moderator {moderator.username} to candidate {candidate.username}")

    ist_offset = timedelta(hours=5, minutes=30)
    email_context = {
        "moderator": moderator, "candidate": candidate, "problem_title": candidate.assigned_problem.title,
        "start_time_ist": candidate.test_start_time + ist_offset, "end_time_ist": candidate.test_end_time + ist_offset,
        "meeting_link": candidate.meeting_link, "now": datetime.utcnow()
    }

    send_email(
        to=moderator.email, cc=[candidate.email], subject=f"Moderator Assignment for {candidate.username}'s Test",
        template="mail/moderator_assigned.html", **email_context
    )

    flash(f'Moderator assigned. Notification sent.', 'success')
    
    # IMPROVEMENT: Redirect back to Hiring Dashboard
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/records')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_records():
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    feedback = Feedback.query.order_by(Feedback.created_at.desc()).all()
    submissions = CodeTestSubmission.query.order_by(CodeTestSubmission.submitted_at.desc()).all()
    history = ModeratorAssignmentHistory.query.order_by(ModeratorAssignmentHistory.assigned_at.desc()).all()
    events = User.query.filter(User.test_completed == True).order_by(User.test_end_time.desc()).all()

    moderator_ids = [e.moderator_id for e in events if e.moderator_id]
    moderators = User.query.filter(User.id.in_(moderator_ids)).all()
    moderators_map = {m.id: m for m in moderators}

    return render_template('manage_records.html', jobs=jobs, feedback=feedback, submissions=submissions, history=history, events=events, moderators_map=moderators_map)

# --- Delete Routes for Records ---
@admin_hiring_bp.route('/job/delete/<int:job_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_job_opening(job_id):
    job = JobOpening.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Job deleted.', 'remove_row_id': f'job-{job_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/feedback/delete/<int:feedback_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Feedback deleted.', 'remove_row_id': f'feed-{feedback_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/submission/delete/<int:submission_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_submission_record(submission_id):
    submission = CodeTestSubmission.query.get_or_404(submission_id)
    db.session.delete(submission)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Submission deleted.', 'remove_row_id': f'sub-{submission_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/history/delete/<int:history_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_assignment_history(history_id):
    history_record = ModeratorAssignmentHistory.query.get_or_404(history_id)
    db.session.delete(history_record)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'History deleted.', 'remove_row_id': f'hist-{history_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/event/delete/<int:user_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_coding_event(user_id):
    candidate = User.query.get_or_404(user_id)
    candidate.problem_statement_id = None
    candidate.test_start_time = None
    candidate.test_end_time = None
    candidate.test_completed = False
    candidate.moderator_id = None
    CodeTestSubmission.query.filter_by(candidate_id=user_id).delete()
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Event cleared.', 'remove_row_id': f'evt-{user_id}'})
    return redirect(url_for('admin_hiring.manage_records'))