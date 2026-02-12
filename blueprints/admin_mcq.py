from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User
from models.mcq import MCQQuestion, Test, TestAssignment, TestResult, test_questions
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
from enums import UserRole

admin_mcq_bp = Blueprint('admin_mcq', __name__, url_prefix='/admin/mcq')

# ==================== QUESTION MANAGEMENT ====================

@admin_mcq_bp.route('/questions')
@login_required
@role_required(UserRole.ADMIN.value)
def list_questions():
    """MCQ Management Dashboard"""
    questions = MCQQuestion.query.order_by(MCQQuestion.created_at.desc()).all()
    tests = Test.query.order_by(Test.created_at.desc()).all()
    assignments = TestAssignment.query.order_by(TestAssignment.scheduled_start_time.desc()).all()
    
    # Get unique categories for filtering
    categories = db.session.query(MCQQuestion.category).distinct().filter(MCQQuestion.category.isnot(None)).order_by(MCQQuestion.category).all()
    categories = [cat[0] for cat in categories]
    
    # Get data for creating assignments
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value, is_approved=True).order_by(User.username).all()
    reviewers = User.query.filter(
        User.role.in_([UserRole.MODERATOR.value, UserRole.DEVELOPER.value]),
        User.is_approved == True
    ).order_by(User.username).all()
    
    return render_template('admin_mcq_dashboard.html', 
                         questions=questions,
                         tests=tests,
                         assignments=assignments,
                         candidates=candidates,
                         reviewers=reviewers,
                         categories=categories)

@admin_mcq_bp.route('/questions/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_question():
    """Create a new MCQ question"""
    try:
        question_text = request.form.get('question_text')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_option = request.form.get('correct_option')
        category = request.form.get('category', '').strip() or None  # Empty string becomes None
        
        # Validation
        if not all([question_text, option_a, option_b, option_c, option_d, correct_option]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        if correct_option not in ['A', 'B', 'C', 'D']:
            flash('Correct option must be A, B, C, or D.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        # Create question
        new_question = MCQQuestion(
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            category=category,
            created_by_id=current_user.id
        )
        
        db.session.add(new_question)
        db.session.commit()
        
        log_user_action("Create MCQ Question", f"Created question: {question_text[:50]}...")
        flash('Question created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating question: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

@admin_mcq_bp.route('/questions/<int:question_id>/edit', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_question(question_id):
    """Edit an existing MCQ question"""
    try:
        question = MCQQuestion.query.get_or_404(question_id)
        
        question.question_text = request.form.get('question_text')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_option = request.form.get('correct_option')
        question.category = request.form.get('category', '').strip() or None
        
        # Validation
        if not all([question.question_text, question.option_a, question.option_b, 
                   question.option_c, question.option_d, question.correct_option]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        if question.correct_option not in ['A', 'B', 'C', 'D']:
            flash('Correct option must be A, B, C, or D.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        db.session.commit()
        
        log_user_action("Edit MCQ Question", f"Edited question ID: {question_id}")
        flash('Question updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating question: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

@admin_mcq_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_question(question_id):
    """Delete an MCQ question"""
    try:
        question = MCQQuestion.query.get_or_404(question_id)
        
        # Check if question is used in any tests
        if question.tests.count() > 0:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Cannot delete question that is used in tests.'})
            flash('Cannot delete question that is used in tests.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        db.session.delete(question)
        db.session.commit()
        
        log_user_action("Delete MCQ Question", f"Deleted question ID: {question_id}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Question deleted successfully!'})
        
        flash('Question deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Error deleting question: {str(e)}'})
        flash(f'Error deleting question: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

# ==================== TEST MANAGEMENT ====================

@admin_mcq_bp.route('/tests')
@login_required
@role_required(UserRole.ADMIN.value)
def list_tests():
    """List all tests"""
    tests = Test.query.order_by(Test.created_at.desc()).all()
    all_questions = MCQQuestion.query.order_by(MCQQuestion.created_at.desc()).all()
    return render_template('admin_mcq_tests.html', tests=tests, all_questions=all_questions)

@admin_mcq_bp.route('/tests/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_test():
    """Create a new test"""
    try:
        title = request.form.get('title')
        description = request.form.get('description', '')
        duration_minutes = request.form.get('duration_minutes')
        question_ids = request.form.getlist('question_ids')
        
        # Validation
        if not title or not duration_minutes:
            flash('Title and duration are required.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        if not question_ids:
            flash('Please select at least one question.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        try:
            duration_minutes = int(duration_minutes)
            if duration_minutes <= 0:
                raise ValueError()
        except ValueError:
            flash('Duration must be a positive number.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        # Create test
        new_test = Test(
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            created_by_id=current_user.id
        )
        
        # Add questions to test
        questions = MCQQuestion.query.filter(MCQQuestion.id.in_(question_ids)).all()
        new_test.questions.extend(questions)
        
        db.session.add(new_test)
        db.session.commit()
        
        log_user_action("Create Test", f"Created test: {title} with {len(questions)} questions")
        flash(f'Test "{title}" created successfully with {len(questions)} questions!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating test: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

@admin_mcq_bp.route('/tests/<int:test_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def view_test(test_id):
    """View test details"""
    test = Test.query.get_or_404(test_id)
    return render_template('admin_mcq_test_detail.html', test=test)

@admin_mcq_bp.route('/tests/<int:test_id>/edit', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_test(test_id):
    """Edit an existing test"""
    try:
        test = Test.query.get_or_404(test_id)
        
        test.title = request.form.get('title')
        test.description = request.form.get('description', '')
        duration_minutes = request.form.get('duration_minutes')
        question_ids = request.form.getlist('question_ids')
        
        # Validation
        if not test.title or not duration_minutes:
            flash('Title and duration are required.', 'danger')
            return redirect(url_for('admin_mcq.view_test', test_id=test_id))
        
        try:
            test.duration_minutes = int(duration_minutes)
            if test.duration_minutes <= 0:
                raise ValueError()
        except ValueError:
            flash('Duration must be a positive number.', 'danger')
            return redirect(url_for('admin_mcq.view_test', test_id=test_id))
        
        # Update questions
        if question_ids:
            test.questions = []
            questions = MCQQuestion.query.filter(MCQQuestion.id.in_(question_ids)).all()
            test.questions.extend(questions)
        
        db.session.commit()
        
        log_user_action("Edit Test", f"Edited test ID: {test_id}")
        flash('Test updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating test: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.view_test', test_id=test_id))

@admin_mcq_bp.route('/tests/<int:test_id>/delete', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def delete_test(test_id):
    """Delete a test"""
    try:
        test = Test.query.get_or_404(test_id)
        
        # Check if test has assignments
        if test.assignments:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Cannot delete test that has assignments.'})
            flash('Cannot delete test that has assignments.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        db.session.delete(test)
        db.session.commit()
        
        log_user_action("Delete Test", f"Deleted test ID: {test_id}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Test deleted successfully!'})
        
        flash('Test deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Error deleting test: {str(e)}'})
        flash(f'Error deleting test: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

# ==================== ASSIGNMENT MANAGEMENT ====================

@admin_mcq_bp.route('/assignments')
@login_required
@role_required(UserRole.ADMIN.value)
def list_assignments():
    """List all test assignments"""
    assignments = TestAssignment.query.order_by(TestAssignment.scheduled_start_time.desc()).all()
    
    # Get data for creating new assignments
    tests = Test.query.order_by(Test.title).all()
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value, is_approved=True).order_by(User.username).all()
    reviewers = User.query.filter(
        User.role.in_([UserRole.MODERATOR.value, UserRole.DEVELOPER.value]),
        User.is_approved == True
    ).order_by(User.username).all()
    
    return render_template('admin_mcq_assignments.html', 
                         assignments=assignments,
                         tests=tests,
                         candidates=candidates,
                         reviewers=reviewers,
                         now=datetime.utcnow())

@admin_mcq_bp.route('/assignments/create', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_assignment():
    """Assign a test to a candidate with a reviewer"""
    try:
        test_id = request.form.get('test_id')
        candidate_id = request.form.get('candidate_id')
        reviewer_id = request.form.get('reviewer_id')
        scheduled_start_time = request.form.get('scheduled_start_time')
        
        # Validation
        if not all([test_id, candidate_id, reviewer_id, scheduled_start_time]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        # Verify entities exist
        test = Test.query.get_or_404(test_id)
        candidate = User.query.get_or_404(candidate_id)
        reviewer = User.query.get_or_404(reviewer_id)
        
        # Verify roles
        if candidate.role != UserRole.CANDIDATE.value:
            flash('Selected user is not a candidate.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        if reviewer.role not in [UserRole.MODERATOR.value, UserRole.DEVELOPER.value]:
            flash('Reviewer must be a Moderator or Developer.', 'danger')
            return redirect(url_for('admin_mcq.list_questions'))
        
        # Parse datetime-local input (format: YYYY-MM-DDTHH:MM)
        scheduled_datetime_ist = datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M')
        
        # Convert to UTC (IST is UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        scheduled_datetime_utc = scheduled_datetime_ist - ist_offset
        
        # Create assignment
        new_assignment = TestAssignment(
            test_id=test_id,
            candidate_id=candidate_id,
            reviewer_id=reviewer_id,
            scheduled_start_time=scheduled_datetime_utc,
            status='pending'
        )
        
        db.session.add(new_assignment)
        db.session.commit()
        
        log_user_action("Create Test Assignment", 
                       f"Assigned test '{test.title}' to {candidate.username}, reviewer: {reviewer.username}")
        
        # Send email notifications
        try:
            # Format scheduled time for display (IST)
            scheduled_time_display = scheduled_datetime_ist.strftime('%d %b %Y, %I:%M %p') + ' IST'
            
            # 1. Email to Candidate - Test Assignment Notification
            send_email(
                to=candidate.email,
                subject=f"MCQ Test Assigned: {test.title}",
                template="mail/mcq_test_assigned.html",
                candidate=candidate,
                test=test,
                reviewer=reviewer,
                scheduled_time=scheduled_time_display
            )
            
            # 2. Email to Reviewer/Moderator - Assignment Notification
            send_email(
                to=reviewer.email,
                subject=f"New MCQ Test Review Assignment: {candidate.username} - {test.title}",
                template="mail/mcq_test_assigned_reviewer.html",
                candidate=candidate,
                test=test,
                reviewer=reviewer,
                scheduled_time=scheduled_time_display
            )
        except Exception as email_error:
            print(f"Error sending assignment emails: {email_error}")
        
        flash(f'Test assigned successfully to {candidate.username}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating assignment: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_questions'))

@admin_mcq_bp.route('/assignments/<int:assignment_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def view_assignment(assignment_id):
    """View assignment details and results"""
    assignment = TestAssignment.query.get_or_404(assignment_id)
    
    # Format questions with answers if test is completed
    questions_data = None
    if assignment.result:
        questions_data = _format_test_results(assignment.result, assignment.test)
    
    return render_template('admin_mcq_assignment_detail.html', 
                         assignment=assignment,
                         questions_data=questions_data,
                         now=datetime.utcnow(),
                         timedelta=timedelta)

@admin_mcq_bp.route('/assignments/<int:assignment_id>/cancel', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def cancel_assignment(assignment_id):
    """Cancel a test assignment"""
    try:
        assignment = TestAssignment.query.get_or_404(assignment_id)
        
        if assignment.status == 'completed':
            flash('Cannot cancel a completed assignment.', 'danger')
            return redirect(url_for('admin_mcq.list_assignments'))
        
        assignment.status = 'expired'
        db.session.commit()
        
        log_user_action("Cancel Test Assignment", f"Cancelled assignment ID: {assignment_id}")
        flash('Assignment cancelled successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling assignment: {str(e)}', 'danger')
    
    return redirect(url_for('admin_mcq.list_assignments'))

# ==================== HELPER FUNCTIONS ====================

def _format_test_results(test_result, test):
    """Format test results for display in email and web"""
    import json
    
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
