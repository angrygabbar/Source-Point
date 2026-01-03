from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.hiring import (CodeTestSubmission, Feedback, ModeratorAssignmentHistory, 
                           JobApplication)
from models.learning import ProblemStatement
from utils import role_required, log_user_action, send_email
from enums import UserRole # --- IMPORT ENUM ---

moderator_bp = Blueprint('moderator', __name__)

@moderator_bp.route('/moderator')
@login_required
@role_required(UserRole.MODERATOR.value) # --- USE ENUM ---
def moderator_dashboard():
    moderated_candidates = User.query.filter_by(moderator_id=current_user.id).all()
    return render_template('moderator_dashboard.html', moderated_candidates=moderated_candidates)

@moderator_bp.route('/submit_feedback', methods=['POST'])
@login_required
@role_required(UserRole.MODERATOR.value) # --- USE ENUM ---
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