import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from enums import UserRole
from extensions import db
from models.auth import User
from models.teaching import (
    TeachingAssignment,
    TeachingAnnouncement,
    TeachingAttendance,
    TeachingClass,
    TeachingEffortLog,
    TeachingEnrollment,
    TeachingMaterial,
    TeachingSession,
    TeachingSessionFeedback,
    TeachingSubmission,
    TeachingTest,
    TeachingTestAnswer,
    TeachingTestAssignment,
    TeachingTestQuestion,
    TeachingTestSubmission,
)
from utils import role_required, send_email


teaching_bp = Blueprint('teaching', __name__, url_prefix='/teaching')
TEACHER_ROLES = [UserRole.ADMIN.value, UserRole.TEACHER.value]
TEACHING_ROLES = TEACHER_ROLES + [UserRole.STUDENT.value]
TEACHER_EFFORT_CATEGORIES = {'preparation', 'live teaching', 'grading', 'mentoring', 'admin'}
STUDENT_EFFORT_CATEGORIES = {'class study', 'assignment', 'revision', 'practice'}
ATTENDANCE_STATUSES = {'present', 'absent', 'late', 'excused'}
BUILT_IN_NOTIFICATION_EMAILS = {'admin@sourcepoint.in', 'sourcepoint.archieve@gmail.com'}


def _owned_class_or_404(class_id):
    query = TeachingClass.query.filter_by(id=class_id)
    if current_user.role != UserRole.ADMIN.value:
        query = query.filter_by(teacher_id=current_user.id)
    return query.first_or_404()


def _enrolled_class_or_404(class_id):
    return TeachingClass.query.join(TeachingEnrollment).filter(
        TeachingClass.id == class_id,
        TeachingEnrollment.student_id == current_user.id,
    ).first_or_404()


def _class_is_open(teaching_class):
    if teaching_class.is_active:
        return True
    flash('This class is archived. Reopen it before adding new class work.', 'info')
    return False


def _eligible_teachers():
    return User.query.filter_by(
        role=UserRole.TEACHER.value,
        is_active=True,
        is_approved=True,
    ).order_by(User.username).all()


def _notify_teaching_participants(teaching_class, subject, template, **context):
    """Queue one class notice with students/admins hidden from one another."""
    teacher = teaching_class.teacher
    recipient_emails = []
    if teacher and teacher.email:
        recipient_emails.append(teacher.email.strip())

    enrolled_emails = db.session.query(User.email).join(
        TeachingEnrollment, TeachingEnrollment.student_id == User.id
    ).filter(
        TeachingEnrollment.class_id == teaching_class.id,
        User.role == UserRole.STUDENT.value,
        User.is_active.is_(True),
        User.is_approved.is_(True),
    ).all()
    recipient_emails.extend(email.strip() for (email,) in enrolled_emails if email)

    admin_emails = User.query.filter_by(
        role=UserRole.ADMIN.value,
        is_active=True,
        is_approved=True,
    ).with_entities(User.email).all()
    recipient_emails.extend(email.strip() for (email,) in admin_emails if email)

    unique_emails = list(dict.fromkeys(email.lower() for email in recipient_emails if email))
    if not unique_emails:
        current_app.logger.warning('Teaching notification skipped for class %s: no recipients', teaching_class.id)
        return

    primary_email = teacher.email.strip().lower() if teacher and teacher.email else unique_emails[0]
    if primary_email not in unique_emails:
        primary_email = unique_emails[0]
    bcc_emails = [
        email for email in unique_emails
        if email != primary_email and email not in BUILT_IN_NOTIFICATION_EMAILS
    ]
    try:
        send_email(
            to=primary_email,
            bcc=bcc_emails or None,
            subject=subject,
            template=template,
            teaching_class=teaching_class,
            teacher=teacher,
            class_url=url_for('teaching.class_detail', class_id=teaching_class.id, _external=True),
            **context,
        )
    except Exception:
        current_app.logger.exception(
            'Could not queue Teaching notification for class %s', teaching_class.id
        )


def _notify_test_assigned(test, test_assignments):
    teacher = test.teaching_class.teacher
    student_emails = [
        assignment.student.email.strip().lower()
        for assignment in test_assignments
        if assignment.student and assignment.student.email
    ]
    student_emails = list(dict.fromkeys(student_emails))
    if not student_emails:
        return
    admin_emails = User.query.filter_by(
        role=UserRole.ADMIN.value, is_active=True, is_approved=True
    ).with_entities(User.email).all()
    admin_recipients = [email.strip().lower() for (email,) in admin_emails if email]
    primary_email = student_emails[0]
    bcc_emails = [
        email for email in student_emails[1:] + admin_recipients
        if email != primary_email and email not in BUILT_IN_NOTIFICATION_EMAILS
    ]
    try:
        send_email(
            to=primary_email,
            cc=teacher.email if teacher and teacher.email else None,
            bcc=list(dict.fromkeys(bcc_emails)) or None,
            subject=f'New test assigned: {test.title}',
            template='mail/teaching_test_assigned.html',
            teaching_class=test.teaching_class,
            test=test,
            teacher=teacher,
            class_url=url_for('teaching.class_detail', class_id=test.class_id, _external=True),
        )
    except Exception:
        current_app.logger.exception('Could not queue assigned test notification for test %s', test.id)


def _parse_local_datetime(value, timezone_name):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        zone = ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _safe_http_url(value):
    if not value:
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
    except ValueError:
        return None
    return value.strip()


@teaching_bp.app_template_filter('teaching_local')
def teaching_local(value, timezone_name='Asia/Kolkata'):
    if value is None:
        return ''
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo('UTC')
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(zone).strftime('%a, %b %d · %I:%M %p %Z')


@teaching_bp.route('/')
@login_required
@role_required(TEACHING_ROLES)
def home():
    is_teacher = current_user.role in TEACHER_ROLES
    if current_user.role == UserRole.ADMIN.value:
        classes = TeachingClass.query.order_by(TeachingClass.created_at.desc()).all()
    elif is_teacher:
        classes = TeachingClass.query.filter_by(teacher_id=current_user.id).order_by(
            TeachingClass.created_at.desc()
        ).all()
    else:
        classes = TeachingClass.query.join(TeachingEnrollment).filter(
            TeachingEnrollment.student_id == current_user.id
        ).order_by(TeachingClass.created_at.desc()).all()

    now = datetime.utcnow()
    upcoming_sessions = sorted(
        (session for teaching_class in classes for session in teaching_class.sessions
         if teaching_class.is_active and session.starts_at >= now),
        key=lambda session: session.starts_at,
    )[:8]
    assignments = [assignment for teaching_class in classes for assignment in teaching_class.assignments]
    pending_assignments = []
    pending_test_assignments = []
    if not is_teacher and assignments:
        submissions = TeachingSubmission.query.filter(
            TeachingSubmission.student_id == current_user.id,
            TeachingSubmission.assignment_id.in_([assignment.id for assignment in assignments]),
        ).all()
        submitted_ids = {submission.assignment_id for submission in submissions}
        pending_assignments = [
            assignment for assignment in assignments
            if assignment.teaching_class.is_active and assignment.id not in submitted_ids
            and (assignment.due_at is None or assignment.due_at >= now)
        ]
    if not is_teacher and classes:
        pending_test_assignments = TeachingTestAssignment.query.join(TeachingTest).filter(
            TeachingTestAssignment.student_id == current_user.id,
            TeachingTest.class_id.in_([teaching_class.id for teaching_class in classes]),
        ).order_by(TeachingTest.created_at.desc()).all()
        pending_test_assignments = [
            test_assignment for test_assignment in pending_test_assignments
            if test_assignment.submission is None
            and test_assignment.test.teaching_class.is_active
            and (test_assignment.test.due_at is None or test_assignment.test.due_at >= now)
        ]

    own_effort_logs = TeachingEffortLog.query.filter_by(user_id=current_user.id).order_by(
        TeachingEffortLog.logged_at.desc()
    ).limit(10).all()
    return render_template(
        'teaching/home.html',
        classes=classes,
        is_teacher=is_teacher,
        upcoming_sessions=upcoming_sessions,
        pending_assignments=pending_assignments,
        pending_test_assignments=pending_test_assignments,
        now=now,
        assignments=assignments,
        own_effort_logs=own_effort_logs,
        teacher_categories=sorted(TEACHER_EFFORT_CATEGORIES),
        student_categories=sorted(STUDENT_EFFORT_CATEGORIES),
        available_teachers=_eligible_teachers() if current_user.role == UserRole.ADMIN.value else [],
    )


@teaching_bp.route('/classes', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def create_class():
    title = request.form.get('title', '').strip()
    if not title or len(title) > 140:
        flash('Enter a class name with 1 to 140 characters.', 'danger')
        return redirect(url_for('teaching.home'))
    timezone_name = request.form.get('timezone_name', 'Asia/Kolkata').strip() or 'Asia/Kolkata'
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        flash('Choose a valid time zone, such as Asia/Kolkata or Europe/London.', 'danger')
        return redirect(url_for('teaching.home'))

    assigned_teacher = current_user
    if current_user.role == UserRole.ADMIN.value:
        try:
            teacher_id = int(request.form.get('teacher_id', ''))
        except (TypeError, ValueError):
            teacher_id = 0
        assigned_teacher = User.query.filter_by(
            id=teacher_id,
            role=UserRole.TEACHER.value,
            is_active=True,
            is_approved=True,
        ).first()
        if assigned_teacher is None:
            flash('Select an active, approved teacher for this class.', 'danger')
            return redirect(url_for('teaching.home'))

    teaching_class = TeachingClass(
        teacher_id=assigned_teacher.id,
        title=title,
        subject=request.form.get('subject', '').strip()[:100] or None,
        level=request.form.get('level', '').strip()[:80] or None,
        description=request.form.get('description', '').strip()[:4000] or None,
        timezone_name=timezone_name,
        invite_code=secrets.token_hex(5).upper(),
    )
    db.session.add(teaching_class)
    db.session.commit()
    _notify_teaching_participants(
        teaching_class,
        subject=f'New class created: {teaching_class.title}',
        template='mail/teaching_class_created.html',
        actor=current_user,
        class_action='created',
    )
    flash('Class created. Share its invite code with your students.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=teaching_class.id))


@teaching_bp.route('/join', methods=['POST'])
@login_required
@role_required(UserRole.STUDENT.value)
def join_class():
    invite_code = request.form.get('invite_code', '').strip().upper()
    teaching_class = TeachingClass.query.filter_by(invite_code=invite_code, is_active=True).first()
    if not teaching_class:
        flash('That class code was not found. Check the code and try again.', 'danger')
        return redirect(url_for('teaching.home'))
    already_enrolled = TeachingEnrollment.query.filter_by(
        class_id=teaching_class.id, student_id=current_user.id
    ).first()
    if already_enrolled:
        flash('You are already enrolled in that class.', 'info')
    else:
        db.session.add(TeachingEnrollment(class_id=teaching_class.id, student_id=current_user.id))
        db.session.commit()
        flash(f'You joined {teaching_class.title}.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=teaching_class.id))


@teaching_bp.route('/classes/<int:class_id>')
@login_required
@role_required(TEACHING_ROLES)
def class_detail(class_id):
    is_teacher = current_user.role in TEACHER_ROLES
    teaching_class = _owned_class_or_404(class_id) if is_teacher else _enrolled_class_or_404(class_id)
    now = datetime.utcnow()
    students = []
    test_students = []
    submissions = []
    effort_logs = []
    my_submissions = {}
    attendance_by_session = {}
    my_attendance = {}
    feedback_by_session = {}
    test_assignments = []
    if is_teacher:
        students = User.query.join(TeachingEnrollment, TeachingEnrollment.student_id == User.id).filter(
            TeachingEnrollment.class_id == teaching_class.id
        ).order_by(User.username).all()
        test_students = [
            student for student in students if student.is_active and student.is_approved
        ]
        submissions = TeachingSubmission.query.join(TeachingAssignment).filter(
            TeachingAssignment.class_id == teaching_class.id
        ).order_by(TeachingSubmission.submitted_at.desc()).all()
        effort_logs = TeachingEffortLog.query.join(User, TeachingEffortLog.user_id == User.id).filter(
            TeachingEffortLog.class_id == teaching_class.id,
            TeachingEffortLog.visible_to_teacher.is_(True),
            User.role == UserRole.STUDENT.value,
        ).order_by(TeachingEffortLog.logged_at.desc()).limit(40).all()
        attendance_records = TeachingAttendance.query.join(TeachingSession).filter(
            TeachingSession.class_id == teaching_class.id
        ).all()
        attendance_by_session = {}
        for record in attendance_records:
            attendance_by_session.setdefault(record.session_id, {})[record.student_id] = record
        feedback_records = TeachingSessionFeedback.query.join(TeachingSession).filter(
            TeachingSession.class_id == teaching_class.id
        ).order_by(TeachingSessionFeedback.created_at.desc()).all()
        for record in feedback_records:
            feedback_by_session.setdefault(record.session_id, []).append(record)
    else:
        my_submissions = {
            submission.assignment_id: submission
            for submission in TeachingSubmission.query.join(TeachingAssignment).filter(
                TeachingAssignment.class_id == teaching_class.id,
                TeachingSubmission.student_id == current_user.id,
            ).all()
        }
        effort_logs = TeachingEffortLog.query.filter_by(
            class_id=teaching_class.id, user_id=current_user.id
        ).order_by(TeachingEffortLog.logged_at.desc()).limit(20).all()
        my_attendance = {
            record.session_id: record
            for record in TeachingAttendance.query.join(TeachingSession).filter(
                TeachingSession.class_id == teaching_class.id,
                TeachingAttendance.student_id == current_user.id,
            ).all()
        }
        feedback_by_session = {
            record.session_id: record
            for record in TeachingSessionFeedback.query.join(TeachingSession).filter(
                TeachingSession.class_id == teaching_class.id,
                TeachingSessionFeedback.student_id == current_user.id,
            ).all()
        }
        test_assignments = TeachingTestAssignment.query.join(TeachingTest).filter(
            TeachingTest.class_id == teaching_class.id,
            TeachingTestAssignment.student_id == current_user.id,
        ).order_by(TeachingTest.created_at.desc()).all()

    return render_template(
        'teaching/class_detail.html',
        teaching_class=teaching_class,
        is_teacher=is_teacher,
        students=students,
        test_students=test_students,
        submissions=submissions,
        effort_logs=effort_logs,
        my_submissions=my_submissions,
        attendance_by_session=attendance_by_session,
        my_attendance=my_attendance,
        feedback_by_session=feedback_by_session,
        completed_session_ids={
            session.id for session in teaching_class.sessions
            if session.starts_at + timedelta(minutes=session.duration_minutes) <= now
        },
        test_assignments=test_assignments,
        announcements=teaching_class.announcements,
        now=now,
        teacher_categories=sorted(TEACHER_EFFORT_CATEGORIES),
        student_categories=sorted(STUDENT_EFFORT_CATEGORIES),
        available_teachers=(
            User.query.filter_by(role=UserRole.TEACHER.value).order_by(User.username).all()
            if current_user.role == UserRole.ADMIN.value else []
        ),
    )


@teaching_bp.route('/classes/<int:class_id>/update', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def update_class(class_id):
    teaching_class = _owned_class_or_404(class_id)
    title = request.form.get('title', '').strip()
    teacher_reassigned = False
    if not title or len(title) > 140:
        flash('Enter a class name with 1 to 140 characters.', 'danger')
    else:
        if current_user.role == UserRole.ADMIN.value:
            teacher_id_raw = request.form.get('teacher_id', '').strip()
            if teacher_id_raw:
                try:
                    teacher_id = int(teacher_id_raw)
                except ValueError:
                    teacher_id = 0
                if teacher_id != teaching_class.teacher_id:
                    assigned_teacher = User.query.filter_by(
                        id=teacher_id,
                        role=UserRole.TEACHER.value,
                        is_active=True,
                        is_approved=True,
                    ).first()
                    if assigned_teacher is None:
                        flash('Choose an active, approved teacher for this class.', 'danger')
                        return redirect(url_for('teaching.class_detail', class_id=class_id))
                    teaching_class.teacher_id = assigned_teacher.id
                    teacher_reassigned = True
        teaching_class.title = title
        teaching_class.subject = request.form.get('subject', '').strip()[:100] or None
        teaching_class.level = request.form.get('level', '').strip()[:80] or None
        teaching_class.description = request.form.get('description', '').strip()[:4000] or None
        db.session.commit()
        if teacher_reassigned:
            _notify_teaching_participants(
                teaching_class,
                subject=f'Class teacher updated: {teaching_class.title}',
                template='mail/teaching_class_created.html',
                actor=current_user,
                class_action='reassigned',
            )
        flash('Class details updated.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/classes/<int:class_id>/status', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def update_class_status(class_id):
    teaching_class = _owned_class_or_404(class_id)
    action = request.form.get('action', '').strip()
    if action == 'archive':
        teaching_class.is_active = False
        db.session.commit()
        flash('Class archived. Existing class history remains available; new students, sessions, tests, and other class work are paused.', 'success')
    elif action == 'restore':
        teaching_class.is_active = True
        db.session.commit()
        flash('Class reopened. Students can join and new class work can be added.', 'success')
    else:
        flash('Choose a valid class status action.', 'danger')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/classes/<int:class_id>/announcements', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def add_announcement(class_id):
    teaching_class = _owned_class_or_404(class_id)
    if not _class_is_open(teaching_class):
        return redirect(url_for('teaching.class_detail', class_id=class_id))
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    if not title or len(title) > 140 or not body or len(body) > 5000:
        flash('Enter an announcement title and message (up to 5,000 characters).', 'danger')
    else:
        announcement = TeachingAnnouncement(
            class_id=teaching_class.id,
            author_id=current_user.id,
            title=title,
            body=body,
        )
        db.session.add(announcement)
        db.session.commit()
        _notify_teaching_participants(
            teaching_class,
            subject=f'Class announcement: {title}',
            template='mail/teaching_announcement.html',
            actor=current_user,
            announcement=announcement,
        )
        flash('Announcement posted for this class.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/classes/<int:class_id>/tests', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def create_test(class_id):
    teaching_class = _owned_class_or_404(class_id)
    if not _class_is_open(teaching_class):
        return redirect(url_for('teaching.class_detail', class_id=class_id))

    title = request.form.get('title', '').strip()
    instructions = request.form.get('instructions', '').strip()
    question_type = request.form.get('question_type', '').strip().lower()
    opens_raw = request.form.get('opens_at', '').strip()
    due_raw = request.form.get('due_at', '').strip()
    opens_at = _parse_local_datetime(opens_raw, teaching_class.timezone_name) if opens_raw else None
    due_at = _parse_local_datetime(due_raw, teaching_class.timezone_name) if due_raw else None
    student_ids_raw = request.form.getlist('student_ids')
    try:
        student_ids = [int(value) for value in student_ids_raw]
    except (TypeError, ValueError):
        student_ids = []

    question_texts = request.form.getlist('question_text[]')
    question_points_raw = request.form.getlist('question_points[]')
    option_a = request.form.getlist('question_option_a[]')
    option_b = request.form.getlist('question_option_b[]')
    option_c = request.form.getlist('question_option_c[]')
    option_d = request.form.getlist('question_option_d[]')
    correct_options = request.form.getlist('question_correct[]')
    questions = []
    if len(question_texts) == len(question_points_raw) and question_texts:
        for index, (prompt_raw, points_raw) in enumerate(zip(question_texts, question_points_raw)):
            prompt = prompt_raw.strip()
            try:
                points = int(points_raw)
            except (TypeError, ValueError):
                points = 0
            if not prompt or len(prompt) > 1000 or not 1 <= points <= 1000:
                questions = []
                break
            question_data = {'prompt': prompt, 'points': points, 'position': index}
            if question_type == 'mcq':
                choices = [
                    options[index].strip() if index < len(options) else ''
                    for options in (option_a, option_b, option_c, option_d)
                ]
                correct = correct_options[index].strip().upper() if index < len(correct_options) else ''
                if any(not choice or len(choice) > 250 for choice in choices) or correct not in {'A', 'B', 'C', 'D'}:
                    questions = []
                    break
                question_data.update(choices=choices, correct_option=correct)
            questions.append(question_data)

    valid_student_ids = set()
    if student_ids:
        valid_student_ids = {
            row[0] for row in db.session.query(User.id).join(
                TeachingEnrollment, TeachingEnrollment.student_id == User.id
            ).filter(
                TeachingEnrollment.class_id == teaching_class.id,
                User.id.in_(set(student_ids)),
                User.role == UserRole.STUDENT.value,
                User.is_active.is_(True),
                User.is_approved.is_(True),
            ).all()
        }

    effective_open_at = opens_at or datetime.utcnow()
    if not title or len(title) > 160:
        flash('Enter a test title with 1 to 160 characters.', 'danger')
    elif len(instructions) > 4000:
        flash('Test instructions must be 4,000 characters or fewer.', 'danger')
    elif question_type not in {'mcq', 'short_answer'}:
        flash('Choose a supported test type.', 'danger')
    elif opens_raw and opens_at is None:
        flash('Enter a valid test opening date and time.', 'danger')
    elif due_raw and due_at is None:
        flash('Enter a valid test deadline.', 'danger')
    elif due_at and due_at <= effective_open_at:
        flash('The deadline must be after the test opening time.', 'danger')
    elif not student_ids or len(set(student_ids)) != len(student_ids) or valid_student_ids != set(student_ids):
        flash('Select one or more active students enrolled in this class.', 'danger')
    elif not questions or len(questions) > 20 or sum(question['points'] for question in questions) > 10000:
        flash('Add 1 to 20 valid questions. Each question needs a prompt and 1 to 1,000 points.', 'danger')
    else:
        test = TeachingTest(
            class_id=teaching_class.id,
            created_by_id=current_user.id,
            title=title,
            instructions=instructions or None,
            question_type=question_type,
            opens_at=opens_at,
            due_at=due_at,
        )
        db.session.add(test)
        db.session.flush()
        for question in questions:
            db.session.add(TeachingTestQuestion(test_id=test.id, **question))
        assignments = [
            TeachingTestAssignment(test_id=test.id, student_id=student_id)
            for student_id in student_ids
        ]
        db.session.add_all(assignments)
        db.session.commit()
        _notify_test_assigned(test, assignments)
        flash('Test created and assigned to the selected students.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


def _student_test_assignment_or_404(assignment_id):
    return TeachingTestAssignment.query.join(TeachingTest).filter(
        TeachingTestAssignment.id == assignment_id,
        TeachingTestAssignment.student_id == current_user.id,
    ).first_or_404()


def _test_availability_message(test):
    now = datetime.utcnow()
    if not test.teaching_class.is_active:
        return 'This class is archived, so its test is closed.'
    if test.opens_at and now < test.opens_at:
        return 'This test is not open yet.'
    if test.due_at and now > test.due_at:
        return 'The deadline for this test has passed.'
    return None


@teaching_bp.route('/test-assignments/<int:assignment_id>')
@login_required
@role_required(UserRole.STUDENT.value)
def take_test(assignment_id):
    test_assignment = _student_test_assignment_or_404(assignment_id)
    message = _test_availability_message(test_assignment.test)
    if message:
        flash(message, 'info')
        return redirect(url_for('teaching.class_detail', class_id=test_assignment.test.class_id))
    if test_assignment.submission:
        flash('You have already submitted this test.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=test_assignment.test.class_id))
    return render_template('teaching/take_test.html', test_assignment=test_assignment)


@teaching_bp.route('/test-assignments/<int:assignment_id>/submit', methods=['POST'])
@login_required
@role_required(UserRole.STUDENT.value)
def submit_test(assignment_id):
    test_assignment = _student_test_assignment_or_404(assignment_id)
    test = test_assignment.test
    message = _test_availability_message(test)
    if message:
        flash(message, 'info')
        return redirect(url_for('teaching.class_detail', class_id=test.class_id))
    if test_assignment.submission:
        flash('You have already submitted this test.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=test.class_id))

    submitted_answers = []
    total_score = 0
    for question in test.questions:
        response = request.form.get(f'answer_{question.id}', '').strip()
        if not response or len(response) > 5000:
            flash('Answer every question using 1 to 5,000 characters.', 'danger')
            return redirect(url_for('teaching.take_test', assignment_id=assignment_id))
        if test.question_type == 'mcq':
            response = response.upper()
            if response not in {'A', 'B', 'C', 'D'}:
                flash('Choose one listed option for each multiple-choice question.', 'danger')
                return redirect(url_for('teaching.take_test', assignment_id=assignment_id))
            is_correct = response == question.correct_option
            if is_correct:
                total_score += question.points
        else:
            is_correct = None
        submitted_answers.append((question, response, is_correct))

    now = datetime.utcnow()
    submission = TeachingTestSubmission(
        assignment_id=test_assignment.id,
        score=total_score if test.question_type == 'mcq' else None,
        graded_at=now if test.question_type == 'mcq' else None,
    )
    try:
        db.session.add(submission)
        db.session.flush()
        for question, response, is_correct in submitted_answers:
            db.session.add(TeachingTestAnswer(
                submission_id=submission.id,
                question_id=question.id,
                response=response,
                is_correct=is_correct,
            ))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('This test was already submitted.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=test.class_id))

    teacher = test.teaching_class.teacher
    if teacher and teacher.email:
        try:
            send_email(
                to=teacher.email,
                subject=f'Test submitted: {test.title}',
                template='mail/teaching_test_submitted.html',
                teacher=teacher,
                student=current_user,
                test=test,
                submission=submission,
                class_url=url_for('teaching.class_detail', class_id=test.class_id, _external=True),
            )
        except Exception:
            current_app.logger.exception(
                'Could not queue test submission notification for test %s', test.id
            )
    flash('Your test has been submitted.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=test.class_id))


@teaching_bp.route('/test-submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def grade_test_submission(submission_id):
    submission = TeachingTestSubmission.query.get_or_404(submission_id)
    test = submission.assignment.test
    _owned_class_or_404(test.class_id)
    if test.question_type != 'short_answer':
        flash('Multiple-choice tests are graded automatically.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=test.class_id))
    try:
        score = float(request.form.get('score', '').strip())
    except (TypeError, ValueError):
        score = -1
    max_score = sum(question.points for question in test.questions)
    feedback = request.form.get('feedback', '').strip()
    if not 0 <= score <= max_score:
        flash(f'Enter a score from 0 to {max_score}.', 'danger')
    elif len(feedback) > 5000:
        flash('Feedback must be 5,000 characters or fewer.', 'danger')
    else:
        submission.score = score
        submission.feedback = feedback or None
        submission.graded_at = datetime.utcnow()
        db.session.commit()
        flash('Test score and feedback saved.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=test.class_id))


@teaching_bp.route('/sessions/<int:session_id>/feedback', methods=['POST'])
@login_required
@role_required(UserRole.STUDENT.value)
def submit_session_feedback(session_id):
    session = TeachingSession.query.get_or_404(session_id)
    _enrolled_class_or_404(session.class_id)
    if session.starts_at + timedelta(minutes=session.duration_minutes) > datetime.utcnow():
        flash('Session feedback will be available after the session ends.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=session.class_id))
    try:
        rating = int(request.form.get('rating', '0'))
    except (TypeError, ValueError):
        rating = 0
    comments = request.form.get('comments', '').strip()
    if rating not in range(1, 6):
        flash('Choose a rating from 1 to 5.', 'danger')
    elif len(comments) > 3000:
        flash('Feedback must be 3,000 characters or fewer.', 'danger')
    else:
        feedback = TeachingSessionFeedback.query.filter_by(
            session_id=session.id, student_id=current_user.id
        ).first()
        if feedback is None:
            feedback = TeachingSessionFeedback(
                session_id=session.id, student_id=current_user.id, rating=rating
            )
            db.session.add(feedback)
        feedback.rating = rating
        feedback.comments = comments or None
        feedback.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Session feedback saved.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=session.class_id))


@teaching_bp.route('/classes/<int:class_id>/sessions', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def add_session(class_id):
    teaching_class = _owned_class_or_404(class_id)
    if not _class_is_open(teaching_class):
        return redirect(url_for('teaching.class_detail', class_id=class_id))
    title = request.form.get('title', '').strip()
    starts_at = _parse_local_datetime(request.form.get('starts_at', ''), teaching_class.timezone_name)
    duration_raw = request.form.get('duration_minutes', '60')
    meeting_value = request.form.get('meeting_url', '').strip()
    meeting_url = _safe_http_url(meeting_value) if meeting_value else None
    try:
        duration = int(duration_raw)
    except (TypeError, ValueError):
        duration = 0
    if not title or len(title) > 160 or starts_at is None or not 1 <= duration <= 480:
        flash('Enter a title, a valid start time, and a duration from 1 to 480 minutes.', 'danger')
    elif meeting_value and not meeting_url:
        flash('The online meeting link must be a valid HTTP or HTTPS URL.', 'danger')
    else:
        session = TeachingSession(
            class_id=teaching_class.id,
            title=title,
            starts_at=starts_at,
            duration_minutes=duration,
            meeting_url=meeting_url,
            notes=request.form.get('notes', '').strip()[:4000] or None,
        )
        db.session.add(session)
        db.session.commit()
        _notify_teaching_participants(
            teaching_class,
            subject=f'Online session scheduled: {title}',
            template='mail/teaching_session_scheduled.html',
            actor=current_user,
            session=session,
        )
        flash('Online class session scheduled.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/sessions/<int:session_id>/attendance', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def update_attendance(session_id):
    session = TeachingSession.query.get_or_404(session_id)
    _owned_class_or_404(session.class_id)
    enrollments = TeachingEnrollment.query.filter_by(class_id=session.class_id).all()
    selected_statuses = {}
    for enrollment in enrollments:
        status = request.form.get(f'student_{enrollment.student_id}', '').strip().lower()
        if status and status not in ATTENDANCE_STATUSES:
            flash('An attendance status was invalid. No changes were saved.', 'danger')
            return redirect(url_for('teaching.class_detail', class_id=session.class_id))
        if status:
            selected_statuses[enrollment.student_id] = status

    if not selected_statuses:
        flash('Select an attendance status for at least one student.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=session.class_id))

    for student_id, status in selected_statuses.items():
        record = TeachingAttendance.query.filter_by(
            session_id=session.id, student_id=student_id
        ).first()
        if record is None:
            record = TeachingAttendance(
                session_id=session.id,
                student_id=student_id,
                status=status,
                marked_by_id=current_user.id,
            )
            db.session.add(record)
        else:
            record.status = status
            record.marked_by_id = current_user.id
            record.marked_at = datetime.utcnow()
    db.session.commit()
    flash('Attendance saved for the selected students.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=session.class_id))


@teaching_bp.route('/classes/<int:class_id>/materials', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def add_material(class_id):
    teaching_class = _owned_class_or_404(class_id)
    if not _class_is_open(teaching_class):
        return redirect(url_for('teaching.class_detail', class_id=class_id))
    title = request.form.get('title', '').strip()
    raw_url = request.form.get('resource_url', '').strip()
    resource_url = _safe_http_url(raw_url)
    if not title or len(title) > 160 or not resource_url:
        flash('Enter a material title and a valid HTTP or HTTPS resource link.', 'danger')
    else:
        db.session.add(TeachingMaterial(
            class_id=teaching_class.id,
            title=title,
            description=request.form.get('description', '').strip()[:2000] or None,
            resource_url=resource_url,
        ))
        db.session.commit()
        flash('Learning material added.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/classes/<int:class_id>/assignments', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def add_assignment(class_id):
    teaching_class = _owned_class_or_404(class_id)
    if not _class_is_open(teaching_class):
        return redirect(url_for('teaching.class_detail', class_id=class_id))
    title = request.form.get('title', '').strip()
    instructions = request.form.get('instructions', '').strip()
    due_raw = request.form.get('due_at', '').strip()
    due_at = _parse_local_datetime(due_raw, teaching_class.timezone_name) if due_raw else None
    points_raw = request.form.get('points', '').strip()
    try:
        points = int(points_raw) if points_raw else None
    except ValueError:
        points = -1
    if not title or len(title) > 160 or not instructions or len(instructions) > 10000:
        flash('Enter an assignment title and instructions.', 'danger')
    elif due_raw and due_at is None:
        flash('Enter a valid due date and time.', 'danger')
    elif points is not None and not 1 <= points <= 10000:
        flash('Points must be between 1 and 10,000.', 'danger')
    else:
        assignment = TeachingAssignment(
            class_id=teaching_class.id,
            title=title,
            instructions=instructions,
            due_at=due_at,
            points=points,
        )
        db.session.add(assignment)
        db.session.commit()
        _notify_teaching_participants(
            teaching_class,
            subject=f'New assignment: {title}',
            template='mail/teaching_assignment_created.html',
            actor=current_user,
            assignment=assignment,
        )
        flash('Assignment published.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=class_id))


@teaching_bp.route('/assignments/<int:assignment_id>/submit', methods=['POST'])
@login_required
@role_required(UserRole.STUDENT.value)
def submit_assignment(assignment_id):
    assignment = TeachingAssignment.query.get_or_404(assignment_id)
    teaching_class = _enrolled_class_or_404(assignment.class_id)
    if not teaching_class.is_active:
        flash('This class is archived, so new assignment submissions are paused.', 'info')
        return redirect(url_for('teaching.class_detail', class_id=assignment.class_id))
    response = request.form.get('response', '').strip()
    if not response or len(response) > 20000:
        flash('Enter a response of up to 20,000 characters.', 'danger')
    elif assignment.due_at and assignment.due_at < datetime.utcnow():
        flash('The due date has passed, so this assignment can no longer be submitted.', 'danger')
    else:
        submission = TeachingSubmission.query.filter_by(
            assignment_id=assignment.id, student_id=current_user.id
        ).first()
        if submission is None:
            submission = TeachingSubmission(
                assignment_id=assignment.id, student_id=current_user.id, response=response
            )
            db.session.add(submission)
        else:
            submission.response = response
            submission.submitted_at = datetime.utcnow()
        db.session.commit()
        flash('Assignment response submitted.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=assignment.class_id))


@teaching_bp.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
@role_required(TEACHER_ROLES)
def grade_submission(submission_id):
    submission = TeachingSubmission.query.get_or_404(submission_id)
    _owned_class_or_404(submission.assignment.class_id)
    grade_raw = request.form.get('grade', '').strip()
    feedback = request.form.get('feedback', '').strip()
    try:
        grade = float(grade_raw) if grade_raw else None
    except ValueError:
        grade = -1
    points = submission.assignment.points
    if grade is not None and (grade < 0 or (points is not None and grade > points)):
        flash('Enter a grade within the assignment point range.', 'danger')
    elif len(feedback) > 5000:
        flash('Feedback must be 5,000 characters or fewer.', 'danger')
    else:
        submission.grade = grade
        submission.feedback = feedback or None
        submission.graded_at = datetime.utcnow() if grade is not None or feedback else None
        db.session.commit()
        flash('Feedback saved.', 'success')
    return redirect(url_for('teaching.class_detail', class_id=submission.assignment.class_id))


@teaching_bp.route('/effort', methods=['POST'])
@login_required
@role_required(TEACHING_ROLES)
def log_effort():
    is_teacher = current_user.role in TEACHER_ROLES
    allowed_categories = TEACHER_EFFORT_CATEGORIES if is_teacher else STUDENT_EFFORT_CATEGORIES
    category = request.form.get('category', '').strip().lower()
    note = request.form.get('note', '').strip()
    try:
        minutes = int(request.form.get('minutes', '0'))
    except (TypeError, ValueError):
        minutes = 0
    class_id_raw = request.form.get('class_id', '').strip()
    teaching_class = None
    if class_id_raw:
        try:
            class_id = int(class_id_raw)
        except ValueError:
            abort(404)
        teaching_class = _owned_class_or_404(class_id) if is_teacher else _enrolled_class_or_404(class_id)
    if category not in allowed_categories or not 1 <= minutes <= 1440 or len(note) > 500:
        flash('Choose an activity and enter time from 1 to 1,440 minutes.', 'danger')
    else:
        db.session.add(TeachingEffortLog(
            user_id=current_user.id,
            class_id=teaching_class.id if teaching_class else None,
            category=category,
            minutes=minutes,
            note=note or None,
            visible_to_teacher=(
                not is_teacher and teaching_class is not None
                and request.form.get('visible_to_teacher') == 'yes'
            ),
        ))
        db.session.commit()
        flash('Effort log saved. Student logs stay private unless you choose to share them.', 'success')
    if teaching_class:
        return redirect(url_for('teaching.class_detail', class_id=teaching_class.id))
    return redirect(url_for('teaching.home'))
