from extensions import db
from flask_login import UserMixin
from datetime import datetime
from enums import UserRole

# Association table for Candidate-Developer contacts
candidate_contacts = db.Table('candidate_contacts',
    db.Column('candidate_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('developer_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    # --- PRIMARY KEY ---
    id = db.Column(db.Integer, primary_key=True)
    
    # --- Columns ---
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Role - Defaults to CANDIDATE
    role = db.Column(db.String(20), nullable=False, default=UserRole.CANDIDATE.value)
    
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    avatar_url = db.Column(db.String(200), nullable=False, default='https://api.dicebear.com/8.x/initials/svg?seed=User')
    
    # Foreign Keys
    problem_statement_id = db.Column(db.Integer, db.ForeignKey('problem_statement.id'), nullable=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Tracking Fields
    test_start_time = db.Column(db.DateTime, nullable=True)
    test_end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    test_completed = db.Column(db.Boolean, default=False, nullable=False) 

    # Profile Fields
    mobile_number = db.Column(db.String(20), nullable=True)
    primary_skill = db.Column(db.String(100), nullable=True)
    primary_skill_experience = db.Column(db.String(50), nullable=True)
    secondary_skill = db.Column(db.String(100), nullable=True)
    secondary_skill_experience = db.Column(db.String(50), nullable=True)
    resume_filename = db.Column(db.String(200), nullable=True)

    # Security / Meetings
    secret_question = db.Column(db.String(255), nullable=True)
    secret_answer_hash = db.Column(db.String(128), nullable=True)
    meeting_link = db.Column(db.String(255), nullable=True)

    # --- Core Relationships ---
    
    allowed_contacts = db.relationship('User', secondary=candidate_contacts,
                                       primaryjoin=(candidate_contacts.c.candidate_id == id),
                                       secondaryjoin=(candidate_contacts.c.developer_id == id),
                                       backref=db.backref('contact_for', lazy='dynamic'), lazy='dynamic')

    # Relationship for problems created by an admin
    created_problems = db.relationship('ProblemStatement', foreign_keys='ProblemStatement.created_by_id', backref='creator', lazy=True)
    
    # --- FIX: Relationship for problems assigned to a candidate ---
    assigned_problem = db.relationship('ProblemStatement', foreign_keys=[problem_statement_id], back_populates='users', lazy=True)
    # -------------------------------------------------------------

    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)
    
    activity_updates = db.relationship('ActivityUpdate', backref='author', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    
    # Commerce relationships
    invoices = db.relationship('Invoice', backref='admin', lazy=True)
    orders = db.relationship('Order', foreign_keys='Order.user_id', backref='buyer', lazy=True)
    sales = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller', lazy=True)
    
    # --- HELPER METHODS ---

    def has_role(self, role_enum):
        """
        Checks if the user has a specific role using the Enum.
        Usage: if user.has_role(UserRole.ADMIN): ...
        """
        return self.role == role_enum.value

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class ActivityUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)