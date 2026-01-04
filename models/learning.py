from extensions import db
from datetime import datetime

class LearningContent(db.Model):
    # Primary Key
    id = db.Column(db.String(50), primary_key=True)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProblemStatement(db.Model):
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='Medium') # Easy, Medium, Hard
    
    # Restored Column: This was causing the "mapped column" error
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    # 1. Users working on this problem (candidates)
    users = db.relationship('User', foreign_keys='User.problem_statement_id', back_populates='assigned_problem', lazy=True)
    
    # 2. History of moderator assignments
    assignment_history = db.relationship('ModeratorAssignmentHistory', back_populates='problem', lazy=True)

# --- NEW: Chat History Model ---
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False) # e.g., 'java', 'python'
    role = db.Column(db.String(10), nullable=False) # 'user' or 'ai'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('chat_history', lazy=True))