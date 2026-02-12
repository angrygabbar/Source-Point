from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.mcq import MCQQuestion, Test, TestAssignment, TestResult
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
from enums import UserRole
import json

candidate_mcq_bp = Blueprint('candidate_mcq', __name__, url_prefix='/candidate/mcq')

# ==================== TEST TAKING ====================

@candidate_mcq_bp.route('/tests')
@login_required
@role_required(UserRole.CANDIDATE.value)
def list_tests():
    """List all assigned tests for the candidate"""
    assignments = TestAssignment.query.filter_by(candidate_id=current_user.id).order_by(
        TestAssignment.scheduled_start_time.desc()
    ).all()
    
    return render_template('candidate_mcq_tests.html', 
                         assignments=assignments,
                         now=datetime.utcnow(),
                         timedelta=timedelta)

@candidate_mcq_bp.route('/tests/<int:assignment_id>/start')
@login_required
@role_required(UserRole.CANDIDATE.value)
def start_test(assignment_id):
    """Start a test (validates scheduled time and access)"""
    try:
        assignment = TestAssignment.query.get_or_404(assignment_id)
        
        # Verify this assignment belongs to the current user
        if assignment.candidate_id != current_user.id:
            flash('You do not have access to this test.', 'danger')
            return redirect(url_for('candidate.candidate_dashboard'))
        
        # Check if test is already completed
        if assignment.status == 'completed':
            flash('This test has already been completed.', 'info')
            return redirect(url_for('candidate_mcq.view_result', assignment_id=assignment_id))
        
        # Check if test is expired/cancelled
        if assignment.status == 'expired':
            flash('This test has been cancelled or expired.', 'warning')
            return redirect(url_for('candidate.candidate_dashboard'))
        
        # Check if current time is before scheduled start time
        current_time = datetime.utcnow()
        if current_time < assignment.scheduled_start_time:
            flash('This test is not yet available. Please wait until the scheduled start time.', 'warning')
            return redirect(url_for('candidate.candidate_dashboard'))
        
        # Update status to in_progress if this is the first access
        if assignment.status == 'pending':
            assignment.status = 'in_progress'
            assignment.started_at = current_time
            db.session.commit()
        
        # Calculate remaining time
        if assignment.started_at:
            elapsed_minutes = (current_time - assignment.started_at).total_seconds() / 60
            remaining_minutes = assignment.test.duration_minutes - elapsed_minutes
            
            # Check if time has expired
            if remaining_minutes <= 0:
                flash('The time limit for this test has expired.', 'danger')
                return redirect(url_for('candidate.candidate_dashboard'))
        else:
            remaining_minutes = assignment.test.duration_minutes
        
        # Get test questions
        test = assignment.test
        questions = test.questions
        
        return render_template('candidate_mcq_take_test.html',
                             assignment=assignment,
                             test=test,
                             questions=questions,
                             remaining_minutes=int(remaining_minutes),
                             now=current_time)
        
    except Exception as e:
        flash(f'Error loading test: {str(e)}', 'danger')
        return redirect(url_for('candidate.candidate_dashboard'))

@candidate_mcq_bp.route('/tests/<int:assignment_id>/submit', methods=['POST'])
@login_required
@role_required(UserRole.CANDIDATE.value)
def submit_test(assignment_id):
    """Submit test answers and calculate score"""
    try:
        assignment = TestAssignment.query.get_or_404(assignment_id)
        
        # Verify this assignment belongs to the current user
        if assignment.candidate_id != current_user.id:
            flash('You do not have access to this test.', 'danger')
            return redirect(url_for('candidate.candidate_dashboard'))
        
        # Check if test is already completed
        if assignment.status == 'completed':
            flash('This test has already been submitted.', 'info')
            return redirect(url_for('candidate_mcq.view_result', assignment_id=assignment_id))
        
        # Check if test was started
        if not assignment.started_at:
            flash('Test was not properly started.', 'danger')
            return redirect(url_for('candidate.candidate_dashboard'))
        
        # Validate submission time (must be within duration + small buffer for network delay)
        current_time = datetime.utcnow()
        elapsed_minutes = (current_time - assignment.started_at).total_seconds() / 60
        
        # Allow 1 minute grace period for network delays
        if elapsed_minutes > (assignment.test.duration_minutes + 1):
            flash('Submission time exceeded. Test has been auto-submitted with current answers.', 'warning')
        
        # Collect answers from form
        answers = {}
        for question in assignment.test.questions:
            answer = request.form.get(f'question_{question.id}')
            if answer:
                answers[str(question.id)] = answer
        
        # Calculate score
        score = 0
        total_questions = len(assignment.test.questions)
        
        for question in assignment.test.questions:
            candidate_answer = answers.get(str(question.id))
            if candidate_answer == question.correct_option:
                score += 1
        
        # Create test result
        test_result = TestResult(
            assignment_id=assignment.id,
            score=score,
            total_questions=total_questions,
            time_taken_minutes=int(elapsed_minutes),
            answers_json=json.dumps(answers)
        )
        
        # Update assignment status
        assignment.status = 'completed'
        
        db.session.add(test_result)
        db.session.commit()
        
        # Send email notifications
        _send_test_completion_emails(assignment, test_result)
        
        log_user_action("Submit MCQ Test", f"Submitted test '{assignment.test.title}' - Score: {score}/{total_questions}")
        flash(f'Test submitted successfully! Your score: {score}/{total_questions}', 'success')
        
        return redirect(url_for('candidate_mcq.view_result', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting test: {str(e)}', 'danger')
        return redirect(url_for('candidate.candidate_dashboard'))

@candidate_mcq_bp.route('/tests/<int:assignment_id>/results')
@login_required
@role_required(UserRole.CANDIDATE.value)
def view_result(assignment_id):
    """View test results"""
    assignment = TestAssignment.query.get_or_404(assignment_id)
    
    # Verify this assignment belongs to the current user
    if assignment.candidate_id != current_user.id:
        flash('You do not have access to this test.', 'danger')
        return redirect(url_for('candidate.candidate_dashboard'))
    
    # Check if test is completed
    if assignment.status != 'completed' or not assignment.result:
        flash('Test results are not yet available.', 'info')
        return redirect(url_for('candidate.candidate_dashboard'))
    
    # Format questions with answers
    questions_data = _format_test_results(assignment.result, assignment.test)
    
    return render_template('candidate_mcq_results.html',
                         assignment=assignment,
                         result=assignment.result,
                         questions_data=questions_data)

# ==================== HELPER FUNCTIONS ====================

def _send_test_completion_emails(assignment, test_result):
    """Send email notifications to candidate, reviewer, and admin"""
    try:
        candidate = assignment.candidate
        reviewer = assignment.reviewer
        test = assignment.test
        
        # Format questions data for email
        questions_data = _format_test_results(test_result, test)
        
        # 1. Email to Candidate (Thank You)
        send_email(
            to=candidate.email,
            subject=f"Test Submitted: {test.title}",
            template="mail/mcq_test_submitted_candidate.html",
            candidate=candidate,
            test=test,
            result=test_result,
            now=datetime.utcnow()
        )
        
        # 2. Email to Reviewer (Detailed Report)
        # Admin is automatically CC'd by the send_email function
        send_email(
            to=reviewer.email,
            subject=f"MCQ Test Completed: {candidate.username} - {test.title}",
            template="mail/mcq_test_submitted_reviewer.html",
            candidate=candidate,
            reviewer=reviewer,
            test=test,
            result=test_result,
            questions_data=questions_data,
            now=datetime.utcnow()
        )
        
    except Exception as e:
        # Log error but don't fail the submission
        print(f"Error sending test completion emails: {e}")

def _format_test_results(test_result, test):
    """Format test results for display"""
    answers = json.loads(test_result.answers_json)
    questions_data = []
    
    for question in test.questions:
        candidate_answer = answers.get(str(question.id), "Not answered")
        is_correct = candidate_answer == question.correct_option
        
        questions_data.append({
            'question_text': question.question_text,
            'candidate_answer': candidate_answer,
            'correct_answer': question.correct_option,
            'is_correct': is_correct,
            'options': {
                'A': question.option_a,
                'B': question.option_b,
                'C': question.option_c,
                'D': question.option_d
            }
        })
    
    return questions_data
