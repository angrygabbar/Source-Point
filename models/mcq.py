from extensions import db
from datetime import datetime
import json

# Association table for many-to-many relationship between Test and MCQQuestion
test_questions = db.Table('test_questions',
    db.Column('test_id', db.Integer, db.ForeignKey('test.id'), primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('mcq_question.id'), primary_key=True)
)

class MCQQuestion(db.Model):
    """Model for individual MCQ questions"""
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    category = db.Column(db.String(100), nullable=True, index=True)  # e.g., 'Java Developer', 'Python Developer', 'Business Analyst'
    
    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_mcq_questions')
    
    def __repr__(self):
        return f'<MCQQuestion {self.id}: {self.question_text[:50]}...>'

class Test(db.Model):
    """Model for MCQ test bundles"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)  # Test duration in minutes
    
    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_tests')
    questions = db.relationship('MCQQuestion', secondary=test_questions, backref=db.backref('tests', lazy='dynamic'))
    assignments = db.relationship('TestAssignment', backref='test', lazy=True, cascade="all, delete-orphan")
    
    @property
    def question_count(self):
        """Returns the number of questions in this test"""
        return len(self.questions)
    
    def __repr__(self):
        return f'<Test {self.id}: {self.title}>'

class TestAssignment(db.Model):
    """Model for assigning tests to candidates with reviewers"""
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Scheduling
    scheduled_start_time = db.Column(db.DateTime, nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, in_progress, completed, expired
    started_at = db.Column(db.DateTime, nullable=True)  # When candidate actually started
    
    # Relationships
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='assigned_mcq_tests')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewing_mcq_tests')
    result = db.relationship('TestResult', backref='assignment', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<TestAssignment {self.id}: Test {self.test_id} -> Candidate {self.candidate_id}>'

class TestResult(db.Model):
    """Model for storing test submission results"""
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('test_assignment.id'), nullable=False, unique=True)
    
    # Results
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    score = db.Column(db.Integer, nullable=False)  # Number of correct answers
    total_questions = db.Column(db.Integer, nullable=False)
    time_taken_minutes = db.Column(db.Integer, nullable=True)  # Actual time taken
    
    # Answer storage (JSON format: {"question_id": "selected_option", ...})
    answers_json = db.Column(db.Text, nullable=False)
    
    @property
    def percentage(self):
        """Calculate percentage score"""
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100, 2)
    
    def get_answers(self):
        """Parse and return answers as dictionary"""
        try:
            return json.loads(self.answers_json)
        except:
            return {}
    
    def set_answers(self, answers_dict):
        """Store answers dictionary as JSON"""
        self.answers_json = json.dumps(answers_dict)
    
    def __repr__(self):
        return f'<TestResult {self.id}: {self.score}/{self.total_questions}>'
