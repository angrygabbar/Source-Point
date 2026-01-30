from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.hiring import (CodeTestSubmission, Feedback, ModeratorAssignmentHistory, 
                           JobApplication)
from models.interview import Interview, InterviewParticipant, InterviewFeedback
from models.learning import ProblemStatement
from utils import role_required, log_user_action, send_email
from enums import UserRole
from datetime import datetime

moderator_bp = Blueprint('moderator', __name__)

@moderator_bp.route('/moderator')
@login_required
@role_required(UserRole.MODERATOR.value)
def moderator_dashboard():
    moderated_candidates = User.query.filter_by(moderator_id=current_user.id).all()
    
    # Get interviews assigned to this moderator
    assigned_interviews = Interview.query.join(InterviewParticipant).filter(
        InterviewParticipant.user_id == current_user.id,
        InterviewParticipant.role == 'moderator'
    ).order_by(Interview.scheduled_time.desc()).all()
    
    # Separate into pending feedback and completed
    interviews_pending_feedback = []
    interviews_with_feedback = []
    
    for interview in assigned_interviews:
        # Check if this moderator already submitted feedback for this interview
        existing_feedback = InterviewFeedback.query.filter_by(
            interview_id=interview.id,
            moderator_id=current_user.id
        ).first()
        
        if existing_feedback:
            interviews_with_feedback.append({
                'interview': interview,
                'feedback': existing_feedback
            })
        elif interview.status != 'cancelled':
            interviews_pending_feedback.append(interview)
    
    return render_template('moderator_dashboard.html', 
                           moderated_candidates=moderated_candidates,
                           interviews_pending_feedback=interviews_pending_feedback,
                           interviews_with_feedback=interviews_with_feedback)

@moderator_bp.route('/submit_feedback', methods=['POST'])
@login_required
@role_required(UserRole.MODERATOR.value)
def submit_feedback():
    candidate_id = request.form.get('candidate_id')
    if not candidate_id:
        flash('You must select a candidate.', 'danger')
        return redirect(url_for('moderator.moderator_dashboard'))

    ratings = {
        'code_correctness': request.form.get('code_correctness'),
        'code_efficiency': request.form.get('code_efficiency'),
        'code_readability': request.form.get('code_readability'),
        'problem_solving': request.form.get('problem_solving'),
        'time_management': request.form.get('time_management')
    }

    for criterion, value in ratings.items():
        if not value:
            flash(f'Please provide a rating for {criterion.replace("_", " ").title()}.', 'danger')
            return redirect(url_for('moderator.moderator_dashboard'))

    remarks = request.form.get('remarks')
    candidate = User.query.get(candidate_id)
    
    if not candidate or candidate.moderator_id != current_user.id:
        flash('You can only provide feedback for candidates you have moderated.', 'danger')
        return redirect(url_for('moderator.moderator_dashboard'))

    feedback = Feedback(
        moderator_id=current_user.id, candidate_id=candidate_id,
        code_correctness=int(ratings['code_correctness']), code_efficiency=int(ratings['code_efficiency']),
        code_readability=int(ratings['code_readability']), problem_solving=int(ratings['problem_solving']),
        time_management=int(ratings['time_management']), remarks=remarks
    )
    db.session.add(feedback)
    db.session.commit()

    send_email(
        to=current_user.email, cc=[], subject=f"Feedback Submitted for {candidate.username}",
        template="mail/feedback_notification.html", moderator=current_user, candidate=candidate, feedback=feedback
    )
    
    log_user_action("Submit Feedback", f"Submitted feedback for {candidate.username}")
    flash('Feedback submitted successfully and admin has been notified.', 'success')
    return redirect(url_for('moderator.moderator_dashboard'))


@moderator_bp.route('/moderator/interview/<int:interview_id>/feedback')
@login_required
@role_required(UserRole.MODERATOR.value)
def interview_feedback_form(interview_id):
    """Show the interview feedback form"""
    interview = Interview.query.get_or_404(interview_id)
    
    # Verify moderator is assigned to this interview
    participant = InterviewParticipant.query.filter_by(
        interview_id=interview_id,
        user_id=current_user.id,
        role='moderator'
    ).first()
    
    if not participant:
        flash('You are not assigned to this interview.', 'danger')
        return redirect(url_for('moderator.moderator_dashboard'))
    
    # Check if feedback already submitted
    existing_feedback = InterviewFeedback.query.filter_by(
        interview_id=interview_id,
        moderator_id=current_user.id
    ).first()
    
    if existing_feedback:
        flash('You have already submitted feedback for this interview.', 'warning')
        return redirect(url_for('moderator.moderator_dashboard'))
    
    return render_template('moderator_interview_feedback.html', 
                           interview=interview)


@moderator_bp.route('/moderator/interview/<int:interview_id>/submit-feedback', methods=['POST'])
@login_required
@role_required(UserRole.MODERATOR.value)
def submit_interview_feedback(interview_id):
    """Submit interview feedback"""
    interview = Interview.query.get_or_404(interview_id)
    
    # Verify moderator is assigned to this interview
    participant = InterviewParticipant.query.filter_by(
        interview_id=interview_id,
        user_id=current_user.id,
        role='moderator'
    ).first()
    
    if not participant:
        flash('You are not assigned to this interview.', 'danger')
        return redirect(url_for('moderator.moderator_dashboard'))
    
    # Check if feedback already submitted
    existing_feedback = InterviewFeedback.query.filter_by(
        interview_id=interview_id,
        moderator_id=current_user.id
    ).first()
    
    if existing_feedback:
        flash('You have already submitted feedback for this interview.', 'warning')
        return redirect(url_for('moderator.moderator_dashboard'))
    
    # Get ratings
    ratings = {
        'communication_skills': request.form.get('communication_skills'),
        'technical_knowledge': request.form.get('technical_knowledge'),
        'problem_solving': request.form.get('problem_solving'),
        'cultural_fit': request.form.get('cultural_fit'),
        'overall_impression': request.form.get('overall_impression')
    }
    
    for criterion, value in ratings.items():
        if not value:
            flash(f'Please provide a rating for {criterion.replace("_", " ").title()}.', 'danger')
            return redirect(url_for('moderator.interview_feedback_form', interview_id=interview_id))
    
    recommendation = request.form.get('recommendation')
    if recommendation not in ['hire', 'maybe', 'no_hire']:
        flash('Please select a valid recommendation.', 'danger')
        return redirect(url_for('moderator.interview_feedback_form', interview_id=interview_id))
    
    remarks = request.form.get('remarks')
    
    # Create feedback
    feedback = InterviewFeedback(
        interview_id=interview_id,
        moderator_id=current_user.id,
        candidate_id=interview.candidate_id,
        communication_skills=int(ratings['communication_skills']),
        technical_knowledge=int(ratings['technical_knowledge']),
        problem_solving=int(ratings['problem_solving']),
        cultural_fit=int(ratings['cultural_fit']),
        overall_impression=int(ratings['overall_impression']),
        recommendation=recommendation,
        remarks=remarks
    )
    db.session.add(feedback)
    db.session.commit()
    
    # Send email notification to admin
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        send_email(
            to=admin.email, 
            cc=[], 
            subject=f"Interview Feedback Submitted: {interview.title}",
            template="mail/interview_feedback_submitted.html", 
            moderator=current_user, 
            candidate=interview.candidate,
            interview=interview,
            feedback=feedback
        )
    
    log_user_action("Submit Interview Feedback", f"Submitted feedback for interview '{interview.title}' with {interview.candidate.username}")
    flash('Interview feedback submitted successfully!', 'success')
    return redirect(url_for('moderator.moderator_dashboard'))