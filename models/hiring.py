from extensions import db
from datetime import datetime
import uuid

class JobOpening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    applications = db.relationship('JobApplication', backref='job', lazy=True, cascade="all, delete-orphan")

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_opening.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    resume_url = db.Column(db.String(500), nullable=True) 
    applied_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # Safe user relationship
    candidate = db.relationship('User', foreign_keys=[user_id], backref=db.backref('applications', lazy=True))

class CodeTestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(50), nullable=False, default='java')
    submitted_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='test_submissions')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_tests')

class CodeSnippet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False, default='java')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    snippet_sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_snippets')
    snippet_recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_snippets')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Detailed Scores
    code_correctness = db.Column(db.Integer, nullable=False, default=0)
    code_efficiency = db.Column(db.Integer, nullable=False, default=0)
    code_readability = db.Column(db.Integer, nullable=False, default=0)
    problem_solving = db.Column(db.Integer, nullable=False, default=0)
    time_management = db.Column(db.Integer, nullable=False, default=0)
    
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='feedback_given')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='feedback_received')

    # NEW: Calculated Property for the Template
    @property
    def rating(self):
        """Calculates average rating from the 5 parameters."""
        try:
            total = (self.code_correctness + self.code_efficiency + 
                     self.code_readability + self.problem_solving + 
                     self.time_management)
            return round(total / 5, 1)
        except TypeError:
            return 0

class ModeratorAssignmentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_statement_id = db.Column(db.Integer, db.ForeignKey('problem_statement.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='candidate_assignments')
    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='moderator_assignments')
    
    # Use back_populates to avoid conflicts with learning.py
    problem = db.relationship('ProblemStatement', foreign_keys=[problem_statement_id], back_populates='assignment_history')