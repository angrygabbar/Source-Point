from datetime import datetime

from extensions import db


class TeachingClass(db.Model):
    __tablename__ = 'teaching_class'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(140), nullable=False)
    subject = db.Column(db.String(100), nullable=True)
    level = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=True)
    timezone_name = db.Column(db.String(64), nullable=False, default='Asia/Kolkata')
    invite_code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teacher = db.relationship('User', foreign_keys=[teacher_id])
    enrollments = db.relationship(
        'TeachingEnrollment', back_populates='teaching_class', cascade='all, delete-orphan'
    )
    sessions = db.relationship(
        'TeachingSession', back_populates='teaching_class', cascade='all, delete-orphan',
        order_by='TeachingSession.starts_at'
    )
    materials = db.relationship(
        'TeachingMaterial', back_populates='teaching_class', cascade='all, delete-orphan',
        order_by='TeachingMaterial.created_at.desc()'
    )
    assignments = db.relationship(
        'TeachingAssignment', back_populates='teaching_class', cascade='all, delete-orphan',
        order_by='TeachingAssignment.created_at.desc()'
    )
    announcements = db.relationship(
        'TeachingAnnouncement', back_populates='teaching_class', cascade='all, delete-orphan',
        order_by='TeachingAnnouncement.created_at.desc()'
    )
    tests = db.relationship(
        'TeachingTest', back_populates='teaching_class', cascade='all, delete-orphan',
        order_by='TeachingTest.created_at.desc()'
    )


class TeachingAnnouncement(db.Model):
    __tablename__ = 'teaching_announcement'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='announcements')
    author = db.relationship('User', foreign_keys=[author_id])


class TeachingTest(db.Model):
    __tablename__ = 'teaching_test'
    __table_args__ = (
        db.CheckConstraint("question_type IN ('mcq', 'short_answer')", name='ck_teaching_test_question_type'),
    )

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    question_type = db.Column(db.String(20), nullable=False)
    opens_at = db.Column(db.DateTime, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='tests')
    creator = db.relationship('User', foreign_keys=[created_by_id])
    questions = db.relationship(
        'TeachingTestQuestion', back_populates='test', cascade='all, delete-orphan',
        order_by='TeachingTestQuestion.position'
    )
    assignments = db.relationship(
        'TeachingTestAssignment', back_populates='test', cascade='all, delete-orphan',
        order_by='TeachingTestAssignment.assigned_at.desc()'
    )


class TeachingTestQuestion(db.Model):
    __tablename__ = 'teaching_test_question'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('teaching_test.id'), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    choices = db.Column(db.JSON, nullable=True)
    correct_option = db.Column(db.String(1), nullable=True)
    points = db.Column(db.Integer, nullable=False, default=1)
    position = db.Column(db.Integer, nullable=False, default=0)

    test = db.relationship('TeachingTest', back_populates='questions')


class TeachingTestAssignment(db.Model):
    __tablename__ = 'teaching_test_assignment'
    __table_args__ = (
        db.UniqueConstraint('test_id', 'student_id', name='uq_teaching_test_assignment_student'),
    )

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('teaching_test.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    test = db.relationship('TeachingTest', back_populates='assignments')
    student = db.relationship('User', foreign_keys=[student_id])
    submission = db.relationship(
        'TeachingTestSubmission', back_populates='assignment', uselist=False,
        cascade='all, delete-orphan'
    )


class TeachingTestSubmission(db.Model):
    __tablename__ = 'teaching_test_submission'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('teaching_test_assignment.id'), nullable=False, unique=True, index=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    score = db.Column(db.Numeric(8, 2), nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)

    assignment = db.relationship('TeachingTestAssignment', back_populates='submission')
    answers = db.relationship(
        'TeachingTestAnswer', back_populates='submission', cascade='all, delete-orphan',
        order_by='TeachingTestAnswer.id'
    )


class TeachingTestAnswer(db.Model):
    __tablename__ = 'teaching_test_answer'
    __table_args__ = (
        db.UniqueConstraint('submission_id', 'question_id', name='uq_teaching_test_answer_question'),
    )

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('teaching_test_submission.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('teaching_test_question.id'), nullable=False, index=True)
    response = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=True)

    submission = db.relationship('TeachingTestSubmission', back_populates='answers')
    question = db.relationship('TeachingTestQuestion')


class TeachingEnrollment(db.Model):
    __tablename__ = 'teaching_enrollment'
    __table_args__ = (db.UniqueConstraint('class_id', 'student_id', name='uq_teaching_class_student'),)

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='enrollments')
    student = db.relationship('User', foreign_keys=[student_id])


class TeachingSession(db.Model):
    __tablename__ = 'teaching_session'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    meeting_url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='sessions')
    attendance_records = db.relationship(
        'TeachingAttendance', back_populates='session', cascade='all, delete-orphan'
    )
    feedback_entries = db.relationship(
        'TeachingSessionFeedback', back_populates='session', cascade='all, delete-orphan',
        order_by='TeachingSessionFeedback.created_at.desc()'
    )


class TeachingSessionFeedback(db.Model):
    __tablename__ = 'teaching_session_feedback'
    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_teaching_session_feedback_student'),
        db.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_teaching_session_feedback_rating'),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('teaching_session.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = db.relationship('TeachingSession', back_populates='feedback_entries')
    student = db.relationship('User', foreign_keys=[student_id])


class TeachingAttendance(db.Model):
    __tablename__ = 'teaching_attendance'
    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_teaching_attendance_session_student'),
        db.CheckConstraint(
            "status IN ('present', 'absent', 'late', 'excused')",
            name='ck_teaching_attendance_status',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('teaching_session.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    marked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    session = db.relationship('TeachingSession', back_populates='attendance_records')
    student = db.relationship('User', foreign_keys=[student_id])
    marked_by = db.relationship('User', foreign_keys=[marked_by_id])


class TeachingMaterial(db.Model):
    __tablename__ = 'teaching_material'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    resource_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='materials')


class TeachingAssignment(db.Model):
    __tablename__ = 'teaching_assignment'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    due_at = db.Column(db.DateTime, nullable=True, index=True)
    points = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    teaching_class = db.relationship('TeachingClass', back_populates='assignments')
    submissions = db.relationship(
        'TeachingSubmission', back_populates='assignment', cascade='all, delete-orphan'
    )


class TeachingSubmission(db.Model):
    __tablename__ = 'teaching_submission'
    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id', name='uq_teaching_assignment_student'),)

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('teaching_assignment.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    response = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)

    assignment = db.relationship('TeachingAssignment', back_populates='submissions')
    student = db.relationship('User', foreign_keys=[student_id])


class TeachingEffortLog(db.Model):
    __tablename__ = 'teaching_effort_log'
    __table_args__ = (db.CheckConstraint('minutes > 0 AND minutes <= 1440', name='ck_teaching_effort_minutes'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('teaching_class.id'), nullable=True, index=True)
    category = db.Column(db.String(40), nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(500), nullable=True)
    visible_to_teacher = db.Column(db.Boolean, nullable=False, default=False)
    logged_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id])
    teaching_class = db.relationship('TeachingClass', foreign_keys=[class_id])
