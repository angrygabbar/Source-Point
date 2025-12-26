from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.auth import User, Message
from models.hiring import JobOpening, JobApplication, CodeTestSubmission
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta

recruiter_bp = Blueprint('recruiter', __name__)

@recruiter_bp.route('/recruiter')
@login_required
@role_required('recruiter')
def recruiter_dashboard():
    # 1. Fetch Job Stats
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    
    # 2. Fetch Applications
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).all()
    pending_apps = [app for app in applications if app.status == 'pending']
    
    # 3. Fetch Candidates & Event Status
    candidates = User.query.filter_by(role='candidate').all()
    
    # Filter for active testing events
    scheduled_candidates = User.query.filter(
        User.role == 'candidate',
        User.problem_statement_id != None,
        User.test_completed == False
    ).all()
    
    # 4. Fetch Moderators for Assignment
    moderators = User.query.filter_by(role='moderator').all()

    return render_template('recruiter_dashboard.html',
                           jobs=jobs,
                           applications=applications,
                           pending_apps=pending_apps,
                           candidates=candidates,
                           scheduled_candidates=scheduled_candidates,
                           moderators=moderators)

# --- THIS WAS THE MISSING ROUTE ---
@recruiter_bp.route('/view_profile/<int:user_id>')
@login_required
@role_required('recruiter')
def view_candidate_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user_profile.html', user=user)
# ----------------------------------

@recruiter_bp.route('/post_job', methods=['POST'])
@login_required
@role_required('recruiter')
def post_job():
    title = request.form.get('job_title')
    description = request.form.get('job_description')
    
    if title and description:
        new_job = JobOpening(title=title, description=description)
        db.session.add(new_job)
        db.session.commit()
        log_user_action("Post Job", f"Recruiter posted new job: {title}")
        flash('New job opening has been posted.', 'success')
    else:
        flash('Job title and description are required.', 'danger')
        
    return redirect(url_for('recruiter.recruiter_dashboard'))

@recruiter_bp.route('/delete_job/<int:job_id>')
@login_required
@role_required('recruiter')
def delete_job(job_id):
    job = JobOpening.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    log_user_action("Delete Job", f"Recruiter deleted job: {job.title}")
    flash('Job opening deleted.', 'success')
    return redirect(url_for('recruiter.recruiter_dashboard'))

@recruiter_bp.route('/application/<int:app_id>/<string:action>')
@login_required
@role_required('recruiter')
def manage_application(app_id, action):
    application = JobApplication.query.get_or_404(app_id)
    
    if action not in ['accept', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('recruiter.recruiter_dashboard'))
    
    status = 'accepted' if action == 'accept' else 'rejected'
    application.status = status
    db.session.commit()

    # Notify Candidate
    send_email(
        to=application.candidate.email,
        subject=f"Update on your application for {application.job.title}",
        template="mail/application_status_update.html",
        candidate=application.candidate,
        job=application.job,
        status=status.capitalize(),
        now=datetime.utcnow()
    )
    
    log_user_action(f"{status.capitalize()} Application", f"Recruiter processed application for {application.candidate.username}")
    flash(f"Application for {application.candidate.username} has been {status}.", 'success')
    return redirect(url_for('recruiter.recruiter_dashboard'))

@recruiter_bp.route('/assign_moderator', methods=['POST'])
@login_required
@role_required('recruiter')
def assign_moderator():
    candidate_id = request.form.get('candidate_id')
    moderator_id = request.form.get('moderator_id')

    candidate = User.query.get(candidate_id)
    moderator = User.query.get(moderator_id)

    if not candidate or not moderator:
        flash("Invalid user selection.", 'danger')
        return redirect(url_for('recruiter.recruiter_dashboard'))

    if not candidate.assigned_problem:
        flash(f"Error: Candidate {candidate.username} does not have a test scheduled yet. Please schedule a test in the Events tab first.", 'danger')
        return redirect(url_for('recruiter.recruiter_dashboard'))

    candidate.moderator_id = moderator_id
    db.session.commit()

    # Log History
    history_record = ModeratorAssignmentHistory(
        candidate_id=candidate.id,
        moderator_id=moderator.id,
        problem_statement_id=candidate.problem_statement_id
    )
    db.session.add(history_record)
    db.session.commit()
    
    log_user_action("Assign Moderator", f"Recruiter assigned {moderator.username} to {candidate.username}")

    # Notify Moderator
    ist_offset = timedelta(hours=5, minutes=30)
    email_context = {
        "moderator": moderator,
        "candidate": candidate,
        "problem_title": candidate.assigned_problem.title,
        "start_time_ist": candidate.test_start_time + ist_offset if candidate.test_start_time else None,
        "end_time_ist": candidate.test_end_time + ist_offset if candidate.test_end_time else None,
        "meeting_link": candidate.meeting_link,
        "now": datetime.utcnow()
    }

    send_email(
        to=moderator.email,
        cc=[candidate.email],
        subject=f"Moderator Assignment for {candidate.username}'s Test",
        template="mail/moderator_assigned.html",
        **email_context
    )

    flash(f'Moderator {moderator.username} has been assigned to {candidate.username}.', 'success')
    return redirect(url_for('recruiter.recruiter_dashboard'))