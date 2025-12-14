from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, ProblemStatement, CodeTestSubmission
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
import requests
import os

events_bp = Blueprint('events', __name__)

JDOODLE_CLIENT_ID = os.environ.get('JDOODLE_CLIENT_ID')
JDOODLE_CLIENT_SECRET = os.environ.get('JDOODLE_CLIENT_SECRET')

@events_bp.route('/events')
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def events():
    candidates = User.query.filter_by(role='candidate').all()
    problems = ProblemStatement.query.all()
    scheduled_events = User.query.filter(User.problem_statement_id != None, User.test_completed == False).all()
    completed_events = User.query.filter(User.problem_statement_id != None, User.test_completed == True).all()

    ist_offset = timedelta(hours=5, minutes=30)
    for event in scheduled_events + completed_events:
        if event.test_start_time:
            event.start_time_ist = (event.test_start_time + ist_offset).strftime('%b %d, %Y at %I:%M %p')
        if event.test_end_time:
            event.end_time_ist = (event.test_end_time + ist_offset).strftime('%b %d, %Y at %I:%M %p')

    received_tests = CodeTestSubmission.query.filter_by(recipient_id=current_user.id).order_by(CodeTestSubmission.submitted_at.desc()).all()

    return render_template('events.html', candidates=candidates, problems=problems, scheduled_events=scheduled_events, completed_events=completed_events, received_tests=received_tests)

@events_bp.route('/create_problem', methods=['POST'])
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def create_problem():
    title = request.form.get('problem_title')
    description = request.form.get('problem_description')
    if not title or not description:
        flash('Title and description are required.', 'danger')
    else:
        new_problem = ProblemStatement(title=title, description=description, created_by_id=current_user.id)
        db.session.add(new_problem)
        db.session.commit()
        log_user_action("Create Problem", f"Created problem statement: {title}")
        flash('New problem statement created.', 'success')
    return redirect(url_for('events.events'))

@events_bp.route('/assign_problem', methods=['POST'])
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def assign_problem():
    candidate_id = request.form.get('candidate_id')
    problem_id = request.form.get('problem_id')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    meeting_link = request.form.get('meeting_link')
    candidate = User.query.get(candidate_id)
    problem = ProblemStatement.query.get(problem_id)
    
    if not candidate or not problem_id or not start_time_str or not end_time_str:
        flash('Please select a candidate, a problem, and set both start and end times.', 'danger')
        return redirect(url_for('events.events'))
    
    try:
        start_time_ist = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_time_ist = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(url_for('events.events'))
    
    ist_offset = timedelta(hours=5, minutes=30)
    start_time_utc = start_time_ist - ist_offset
    end_time_utc = end_time_ist - ist_offset
    
    candidate.problem_statement_id = problem_id
    candidate.test_start_time = start_time_utc
    candidate.test_end_time = end_time_utc
    candidate.meeting_link = meeting_link
    candidate.reminder_sent = False
    candidate.moderator_id = None
    candidate.test_completed = False
    db.session.commit()

    send_email(
        to=candidate.email, subject="You've Been Scheduled for a Coding Test", template="mail/test_scheduled.html",
        candidate=candidate, problem=problem, start_time_ist=start_time_ist, end_time_ist=end_time_ist, meeting_link=meeting_link
    )
    log_user_action("Assign Problem", f"Assigned problem to {candidate.username}")
    flash(f'Problem assigned to {candidate.username}.', 'success')
    return redirect(url_for('events.events'))

@events_bp.route('/reschedule_event/<int:user_id>', methods=['POST'])
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def reschedule_event(user_id):
    candidate = User.query.get_or_404(user_id)
    problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "your assigned problem"
    start_time_str = request.form.get('new_start_time')
    end_time_str = request.form.get('new_end_time')

    if not start_time_str or not end_time_str:
        flash('Please provide both a new start and end time.', 'danger')
        return redirect(request.referrer)

    try:
        start_time_ist = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_time_ist = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(request.referrer)

    ist_offset = timedelta(hours=5, minutes=30)
    candidate.test_start_time = start_time_ist - ist_offset
    candidate.test_end_time = end_time_ist - ist_offset
    candidate.reminder_sent = False
    candidate.moderator_id = None
    candidate.test_completed = False
    db.session.commit()

    send_email(
        to=candidate.email, subject="Your Coding Test Has Been Rescheduled", template="mail/test_rescheduled.html",
        candidate=candidate, problem_title=problem_title, start_time_ist=start_time_ist, end_time_ist=end_time_ist
    )
    log_user_action("Reschedule Event", f"Rescheduled test for {candidate.username}")
    flash(f'Event for {candidate.username} has been rescheduled.', 'success')

    if current_user.role == 'moderator': return redirect(url_for('moderator.moderator_dashboard'))
    elif current_user.role == 'recruiter': return redirect(url_for('recruiter.recruiter_dashboard'))
    else: return redirect(url_for('events.events'))

@events_bp.route('/cancel_event/<int:user_id>')
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def cancel_event(user_id):
    candidate = User.query.get_or_404(user_id)
    problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "your assigned problem"

    candidate.problem_statement_id = None
    candidate.test_start_time = None
    candidate.test_end_time = None
    candidate.reminder_sent = False
    candidate.moderator_id = None
    db.session.commit()

    send_email(to=candidate.email, subject="Your Coding Test Has Been Cancelled", template="mail/test_cancelled.html", candidate=candidate, problem_title=problem_title)
    log_user_action("Cancel Event", f"Cancelled test for {candidate.username}")
    flash(f'Event for {candidate.username} has been canceled.', 'success')

    if current_user.role == 'moderator': return redirect(url_for('moderator.moderator_dashboard'))
    elif current_user.role == 'recruiter': return redirect(url_for('recruiter.recruiter_dashboard'))
    else: return redirect(url_for('events.events'))

@events_bp.route('/mark_event_completed/<int:user_id>')
@login_required
@role_required(['admin', 'developer', 'moderator', 'recruiter'])
def mark_event_completed(user_id):
    candidate = User.query.get_or_404(user_id)
    if candidate.role != 'candidate':
        flash('Cannot mark event completed for non-candidate users.', 'danger')
        return redirect(url_for('events.events'))
    
    candidate.test_completed = True
    db.session.commit()
    flash(f'Event for {candidate.username} has been manually marked as completed.', 'success')

    problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "your assigned problem"
    send_email(to=candidate.email, subject="Your Coding Test is Complete", template="mail/test_completed_candidate.html", candidate=candidate, problem_title=problem_title)

    recipient_emails = []
    if candidate.moderator_id:
        moderator = User.query.get(candidate.moderator_id)
        if moderator: recipient_emails.append(moderator.email)
    else:
        admins = User.query.filter_by(role='admin').all()
        recipient_emails = [admin.email for admin in admins]

    if recipient_emails:
        admin_user = User.query.filter_by(role='admin').first()
        send_email(to=recipient_emails, subject=f"Coding Test Completed: {candidate.username}", template="mail/test_completed_admin.html", admin=admin_user, candidate=candidate, problem_title=problem_title)

    if current_user.role == 'moderator': return redirect(url_for('moderator.moderator_dashboard'))
    elif current_user.role == 'recruiter': return redirect(url_for('recruiter.recruiter_dashboard'))
    else: return redirect(url_for('events.events'))

@events_bp.route('/run_code', methods=['POST'])
@login_required
def run_code():
    data = request.get_json()
    code = data.get('code')
    stdin = data.get('stdin', '')

    if not code:
        return jsonify({'error': 'No code provided'}), 400

    url = "https://api.jdoodle.com/v1/execute"
    payload = {
        "clientId": JDOODLE_CLIENT_ID,
        "clientSecret": JDOODLE_CLIENT_SECRET,
        "script": code,
        "stdin": stdin,
        "language": "java",
        "versionIndex": "0"
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@events_bp.route('/delete_code_test_submission/<int:submission_id>')
@login_required
def delete_code_test_submission(submission_id):
    submission = CodeTestSubmission.query.get_or_404(submission_id)
    if submission.recipient_id == current_user.id:
        db.session.delete(submission)
        db.session.commit()
        flash('Code test submission deleted successfully.', 'success')
    else:
        flash('You do not have permission to delete this submission.', 'danger')
    return redirect(url_for('events.events'))