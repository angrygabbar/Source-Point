from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.hiring import JobApplication, JobOpening, CodeSnippet, Feedback, CodeTestSubmission, ModeratorAssignmentHistory
from models.interview import Interview, InterviewFeedback
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
from enums import UserRole, ApplicationStatus

admin_hiring_bp = Blueprint('admin_hiring', __name__, url_prefix='/admin/hiring')

@admin_hiring_bp.route('/dashboard')
@login_required
@role_required(UserRole.ADMIN.value)
def admin_hiring_dashboard():
    pending_apps_count = JobApplication.query.filter_by(status=ApplicationStatus.PENDING.value).count()
    
    hiring_roles = [UserRole.CANDIDATE.value, UserRole.DEVELOPER.value, UserRole.MODERATOR.value, UserRole.RECRUITER.value]
    pending_hiring_users = User.query.filter(User.is_approved == False, User.role.in_(hiring_roles)).all()
    
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).limit(20).all()
    
    scheduled_candidates = User.query.filter(User.role == UserRole.CANDIDATE.value, User.problem_statement_id != None, User.moderator_id == None).all()
    assigned_candidates = User.query.filter(User.role == UserRole.CANDIDATE.value, User.moderator_id.isnot(None)).order_by(User.test_start_time.asc()).limit(20).all()
    
    mod_ids = list(set([c.moderator_id for c in assigned_candidates if c.moderator_id]))
    moderators_map = {m.id: m for m in User.query.filter(User.id.in_(mod_ids)).all()}
    all_moderators = User.query.filter_by(role=UserRole.MODERATOR.value).all()
    received_snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id).order_by(CodeSnippet.timestamp.desc()).limit(5).all()
    
    # Get all feedback - code test and interview
    code_feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(20).all()
    interview_feedbacks = InterviewFeedback.query.order_by(InterviewFeedback.created_at.desc()).limit(20).all()

    return render_template('admin_hiring_dashboard.html',
                           pending_apps_count=pending_apps_count,
                           pending_hiring_users=pending_hiring_users,
                           applications=applications,
                           scheduled_candidates=scheduled_candidates,
                           assigned_candidates=assigned_candidates,
                           moderators_map=moderators_map,
                           all_moderators=all_moderators,
                           received_snippets=received_snippets,
                           code_feedbacks=code_feedbacks,
                           interview_feedbacks=interview_feedbacks)

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
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/application/accept/<int:app_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def accept_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = ApplicationStatus.ACCEPTED.value
    db.session.commit()

    send_email(to=application.candidate.email, subject=f"Update on your application for {application.job.title}", template="mail/application_status_update.html", candidate=application.candidate, job=application.job, status="Accepted", now=datetime.utcnow())
    log_user_action("Accept Application", f"Accepted application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been accepted.", 'success')
    return redirect(url_for('admin_hiring.admin_hiring_dashboard'))

@admin_hiring_bp.route('/application/reject/<int:app_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def reject_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = ApplicationStatus.REJECTED.value
    db.session.commit()

    send_email(to=application.candidate.email, subject=f"Update on your application for {application.job.title}", template="mail/application_status_update.html", candidate=application.candidate, job=application.job, status="Rejected", now=datetime.utcnow())
    log_user_action("Reject Application", f"Rejected application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been rejected.", 'warning')
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

    history_record = ModeratorAssignmentHistory(candidate_id=candidate.id, moderator_id=moderator.id, problem_statement_id=candidate.problem_statement_id)
    db.session.add(history_record)
    db.session.commit()
    
    log_user_action("Assign Moderator", f"Assigned moderator {moderator.username} to candidate {candidate.username}")

    ist_offset = timedelta(hours=5, minutes=30)
    email_context = {"moderator": moderator, "candidate": candidate, "problem_title": candidate.assigned_problem.title, "start_time_ist": candidate.test_start_time + ist_offset, "end_time_ist": candidate.test_end_time + ist_offset, "meeting_link": candidate.meeting_link, "now": datetime.utcnow()}

    send_email(to=moderator.email, cc=[candidate.email], subject=f"Moderator Assignment for {candidate.username}'s Test", template="mail/moderator_assigned.html", **email_context)
    flash(f'Moderator assigned. Notification sent.', 'success')
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

# --- DELETE ROUTES ---
@admin_hiring_bp.route('/job/delete/<int:job_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_job_opening(job_id):
    job = JobOpening.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    log_user_action("Delete Job", f"Deleted job {job.title}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Job deleted.', 'remove_row_id': f'job-{job_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/feedback/delete/<int:feedback_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    log_user_action("Delete Feedback", f"Deleted feedback {feedback_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Feedback deleted.', 'remove_row_id': f'feed-{feedback_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/submission/delete/<int:submission_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_submission_record(submission_id):
    submission = CodeTestSubmission.query.get_or_404(submission_id)
    db.session.delete(submission)
    db.session.commit()
    log_user_action("Delete Submission", f"Deleted submission {submission_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Submission deleted.', 'remove_row_id': f'sub-{submission_id}'})
    return redirect(url_for('admin_hiring.manage_records'))

@admin_hiring_bp.route('/history/delete/<int:history_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_assignment_history(history_id):
    history_record = ModeratorAssignmentHistory.query.get_or_404(history_id)
    db.session.delete(history_record)
    db.session.commit()
    log_user_action("Delete History", f"Deleted history {history_id}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'History deleted.', 'remove_row_id': f'hist-{history_id}'})
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
    log_user_action("Clear Event", f"Cleared event history for {candidate.username}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Event cleared.', 'remove_row_id': f'evt-{user_id}'})
    return redirect(url_for('admin_hiring.manage_records'))


# ==================== INTERVIEW SCHEDULING ROUTES ====================

@admin_hiring_bp.route('/interviews/schedule', methods=['GET'])
@login_required
@role_required(UserRole.ADMIN.value)
def schedule_interview():
    """Display the interview scheduling form"""
    from models.interview import Interview
    
    # Get all moderators and candidates
    moderators = User.query.filter_by(role=UserRole.MODERATOR.value, is_approved=True).all()
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value, is_approved=True).all()
    
    return render_template('admin_schedule_interview.html', 
                         moderators=moderators, 
                         candidates=candidates,
                         now=datetime.utcnow())


@admin_hiring_bp.route('/interviews/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_interview():
    """Create a new interview with Google Meet link"""
    from models.interview import Interview, InterviewParticipant
    from services.google_calendar_service import GoogleCalendarService
    
    try:
        # Extract form data
        title = request.form.get('title')
        description = request.form.get('description', '')
        candidate_id = request.form.get('candidate_id')
        moderator_ids = request.form.getlist('moderator_ids')  # Multiple moderators
        scheduled_date = request.form.get('scheduled_date')
        scheduled_time = request.form.get('scheduled_time')
        duration_minutes = int(request.form.get('duration_minutes', 60))
        
        # Validation
        if not all([title, candidate_id, scheduled_date, scheduled_time]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin_hiring.schedule_interview'))
        
        if not moderator_ids:
            flash('Please select at least one moderator.', 'danger')
            return redirect(url_for('admin_hiring.schedule_interview'))
        
        # Parse datetime - user enters time in IST
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        scheduled_datetime_ist = datetime.strptime(scheduled_datetime_str, '%Y-%m-%d %H:%M')
        
        # Convert to UTC for storage (IST is UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        scheduled_datetime = scheduled_datetime_ist - ist_offset  # UTC time for DB
        
        # Get candidate and moderators
        candidate = User.query.get_or_404(candidate_id)
        moderators = User.query.filter(User.id.in_(moderator_ids)).all()
        
        if len(moderators) != len(moderator_ids):
            flash('Invalid moderator selection.', 'danger')
            return redirect(url_for('admin_hiring.schedule_interview'))
        
        # Prepare attendee emails
        attendee_emails = [candidate.email] + [mod.email for mod in moderators]
        
        # Create Jitsi Meet link for the interview
        from services.jitsi_meet_service import JitsiMeetService
        jitsi_service = JitsiMeetService()
        meeting_data = jitsi_service.create_meeting(
            title=title,
            scheduled_time=scheduled_datetime
        )
        meet_link = meeting_data['meet_link']
        current_app.logger.info(f"Created Jitsi Meet link: {meet_link}")
        
        # Create interview record
        interview = Interview(
            title=title,
            description=description,
            scheduled_time=scheduled_datetime,
            duration_minutes=duration_minutes,
            candidate_id=candidate_id,
            google_event_id=None,  # Not using Google Calendar
            google_meet_link=meet_link,  # Jitsi Meet link stored here
            status='scheduled',
            created_by=current_user.id
        )
        current_app.logger.info(f"DEBUG: Creating interview record for candidate_id={candidate_id}")
        db.session.add(interview)
        db.session.flush()  # Get interview ID
        current_app.logger.info(f"DEBUG: Interview created with ID={interview.id}")
        
        # Add moderators as participants
        for moderator in moderators:
            participant = InterviewParticipant(
                interview_id=interview.id,
                user_id=moderator.id,
                role='moderator',
                notified_at=datetime.utcnow()
            )
            db.session.add(participant)
        
        current_app.logger.info(f"DEBUG: Committing interview and participants to database")
        db.session.commit()
        current_app.logger.info(f"DEBUG: Database commit successful")
        
        # Send email notifications
        # Send email notifications - use the original IST time entered by user
        scheduled_time_ist = scheduled_datetime_ist  # Already in IST
        
        # Email to moderators
        for moderator in moderators:
            other_moderators = [m for m in moderators if m.id != moderator.id]
            try:
                send_email(
                    to=moderator.email,
                    subject=f"Interview Scheduled: {title}",
                    template="mail/interview_scheduled_moderator.html",
                    moderator=moderator,
                    candidate=candidate,
                    interview=interview,
                    other_moderators=other_moderators,
                    scheduled_time_ist=scheduled_time_ist,
                    meet_link=meet_link,
                    now=datetime.utcnow()
                )
            except Exception as email_error:
                current_app.logger.warning(f"Failed to send email to {moderator.email}: {email_error}")
        
        # Email to candidate
        try:
            send_email(
                to=candidate.email,
                subject=f"Interview Scheduled: {title}",
                template="mail/interview_scheduled_candidate.html",
                candidate=candidate,
                interview=interview,
                moderators=moderators,
                scheduled_time_ist=scheduled_time_ist,
                meet_link=meet_link,
                now=datetime.utcnow()
            )
        except Exception as email_error:
            current_app.logger.warning(f"Failed to send email to {candidate.email}: {email_error}")
        
        log_user_action("Schedule Interview", f"Scheduled interview '{title}' with {candidate.username}")
        
        # Show success message
        flash(f'Interview scheduled successfully! Meeting link: {meet_link}', 'success')
        
        return redirect(url_for('admin_hiring.view_interviews'))
        
    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f"Error scheduling interview: {e}")
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error scheduling interview: {str(e)}', 'danger')
        return redirect(url_for('admin_hiring.schedule_interview'))


@admin_hiring_bp.route('/interviews')
@login_required
@role_required(UserRole.ADMIN.value)
def view_interviews():
    """View all scheduled interviews"""
    from models.interview import Interview
    
    # Get filter parameter
    status_filter = request.args.get('status', 'all')
    
    query = Interview.query
    
    if status_filter == 'upcoming':
        query = query.filter(
            Interview.status == 'scheduled',
            Interview.scheduled_time >= datetime.utcnow()
        )
    elif status_filter == 'past':
        query = query.filter(
            Interview.scheduled_time < datetime.utcnow()
        )
    elif status_filter == 'cancelled':
        query = query.filter(Interview.status == 'cancelled')
    
    interviews = query.order_by(Interview.scheduled_time.desc()).all()
    
    return render_template('admin_interviews_list.html', 
                         interviews=interviews,
                         status_filter=status_filter,
                         now=datetime.utcnow(),
                         timedelta=timedelta)


@admin_hiring_bp.route('/interviews/<int:interview_id>/cancel', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def cancel_interview(interview_id):
    """Cancel an interview and notify participants"""
    from models.interview import Interview
    from services.google_calendar_service import GoogleCalendarService
    
    try:
        interview = Interview.query.get_or_404(interview_id)
        
        if interview.status == 'cancelled':
            flash('Interview is already cancelled.', 'warning')
            return redirect(url_for('admin_hiring.view_interviews'))
        
        # Cancel Google Calendar event
        if interview.google_event_id:
            try:
                calendar_service = GoogleCalendarService()
                calendar_service.cancel_interview_event(interview.google_event_id)
            except Exception as e:
                flash(f'Warning: Could not cancel Google Calendar event: {str(e)}', 'warning')
        
        # Update status
        interview.status = 'cancelled'
        interview.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Send cancellation emails
        ist_offset = timedelta(hours=5, minutes=30)
        scheduled_time_ist = interview.scheduled_time + ist_offset
        
        # Email to moderators
        for participant in interview.participants:
            send_email(
                to=participant.user.email,
                subject=f"Interview Cancelled: {interview.title}",
                template="mail/interview_cancelled.html",
                user=participant.user,
                interview=interview,
                candidate=interview.candidate,
                scheduled_time_ist=scheduled_time_ist,
                now=datetime.utcnow()
            )
        
        # Email to candidate
        send_email(
            to=interview.candidate.email,
            subject=f"Interview Cancelled: {interview.title}",
            template="mail/interview_cancelled.html",
            user=interview.candidate,
            interview=interview,
            candidate=interview.candidate,
            scheduled_time_ist=scheduled_time_ist,
            now=datetime.utcnow()
        )
        
        log_user_action("Cancel Interview", f"Cancelled interview '{interview.title}'")
        flash('Interview cancelled and participants notified.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling interview: {str(e)}', 'danger')
    
    return redirect(url_for('admin_hiring.view_interviews'))


@admin_hiring_bp.route('/interviews/<int:interview_id>/reschedule', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def reschedule_interview(interview_id):
    """Reschedule an interview to a new date/time"""
    from models.interview import Interview
    from services.jitsi_meet_service import JitsiMeetService
    
    interview = Interview.query.get_or_404(interview_id)
    
    if interview.status == 'cancelled':
        flash('Cannot reschedule a cancelled interview.', 'warning')
        return redirect(url_for('admin_hiring.view_interviews'))
    
    if request.method == 'GET':
        # Show reschedule form
        ist_offset = timedelta(hours=5, minutes=30)
        current_time_ist = interview.scheduled_time + ist_offset
        return render_template('admin_reschedule_interview.html',
                             interview=interview,
                             current_time_ist=current_time_ist,
                             now=datetime.now())
    
    # POST - Process reschedule
    try:
        new_date = request.form.get('scheduled_date')
        new_time = request.form.get('scheduled_time')
        new_duration = request.form.get('duration_minutes', 60)
        reason = request.form.get('reason', '')
        
        if not new_date or not new_time:
            flash('Please provide both date and time.', 'danger')
            return redirect(url_for('admin_hiring.reschedule_interview', interview_id=interview_id))
        
        # Parse new datetime (IST to UTC)
        ist_offset = timedelta(hours=5, minutes=30)
        scheduled_datetime_ist = datetime.strptime(f"{new_date} {new_time}", '%Y-%m-%d %H:%M')
        scheduled_datetime_utc = scheduled_datetime_ist - ist_offset
        
        # Store old time for notification
        old_time_ist = interview.scheduled_time + ist_offset
        
        # Update interview
        interview.scheduled_time = scheduled_datetime_utc
        interview.duration_minutes = int(new_duration)
        interview.updated_at = datetime.utcnow()
        
        # Generate new Jitsi Meet link
        jitsi_service = JitsiMeetService()
        meeting_data = jitsi_service.create_meeting(
            title=interview.title,
            interview_id=interview.id,
            scheduled_time=scheduled_datetime_utc
        )
        interview.google_meet_link = meeting_data['meet_link']
        
        db.session.commit()
        
        # Send reschedule notifications
        moderators = [p.user for p in interview.participants]
        new_time_ist = scheduled_datetime_ist
        
        # Send to candidate
        send_email(
            to=interview.candidate.email,
            subject=f"Interview Rescheduled - {interview.title}",
            template="mail/interview_rescheduled.html",
            interview=interview,
            recipient=interview.candidate,
            recipient_type='candidate',
            old_time_ist=old_time_ist,
            new_time_ist=new_time_ist,
            reason=reason,
            moderators=moderators,
            meet_link=interview.google_meet_link,
            now=datetime.utcnow()
        )
        
        # Send to moderators
        for moderator in moderators:
            send_email(
                to=moderator.email,
                subject=f"Interview Rescheduled - {interview.title}",
                template="mail/interview_rescheduled.html",
                interview=interview,
                recipient=moderator,
                recipient_type='moderator',
                old_time_ist=old_time_ist,
                new_time_ist=new_time_ist,
                reason=reason,
                candidate=interview.candidate,
                meet_link=interview.google_meet_link,
                now=datetime.utcnow()
            )
        
        log_user_action("Reschedule Interview", f"Rescheduled interview '{interview.title}' to {new_time_ist.strftime('%Y-%m-%d %H:%M')}")
        flash(f'Interview rescheduled successfully! All participants have been notified.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rescheduling interview: {e}")
        flash(f'Error rescheduling interview: {str(e)}', 'danger')
    
    return redirect(url_for('admin_hiring.view_interviews'))


@admin_hiring_bp.route('/interviews/<int:interview_id>/resend-invites', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def resend_interview_invites(interview_id):
    """Resend interview invitations to all participants"""
    from models.interview import Interview
    
    try:
        interview = Interview.query.get_or_404(interview_id)
        
        if interview.status == 'cancelled':
            flash('Cannot resend invites for cancelled interview.', 'warning')
            return redirect(url_for('admin_hiring.view_interviews'))
        
        ist_offset = timedelta(hours=5, minutes=30)
        scheduled_time_ist = interview.scheduled_time + ist_offset
        
        # Resend to moderators
        moderators = [p.user for p in interview.participants]
        for moderator in moderators:
            other_moderators = [m for m in moderators if m.id != moderator.id]
            send_email(
                to=moderator.email,
                subject=f"Reminder: Interview Scheduled - {interview.title}",
                template="mail/interview_scheduled_moderator.html",
                moderator=moderator,
                candidate=interview.candidate,
                interview=interview,
                other_moderators=other_moderators,
                scheduled_time_ist=scheduled_time_ist,
                meet_link=interview.google_meet_link,
                now=datetime.utcnow()
            )
        
        # Resend to candidate
        send_email(
            to=interview.candidate.email,
            subject=f"Reminder: Interview Scheduled - {interview.title}",
            template="mail/interview_scheduled_candidate.html",
            candidate=interview.candidate,
            interview=interview,
            moderators=moderators,
            scheduled_time_ist=scheduled_time_ist,
            meet_link=interview.google_meet_link,
            now=datetime.utcnow()
        )
        
        log_user_action("Resend Interview Invites", f"Resent invites for interview '{interview.title}'")
        flash('Interview invitations resent to all participants.', 'success')
        
    except Exception as e:
        flash(f'Error resending invites: {str(e)}', 'danger')
    
    return redirect(url_for('admin_hiring.view_interviews'))