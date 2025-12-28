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
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    # 1. Users working on this problem (candidates)
    # We use string reference 'User' to avoid circular imports
    users = db.relationship('User', foreign_keys='User.problem_statement_id', backref='assigned_problem', lazy=True)
    
    # 2. History of moderator assignments
    # FIX: Changed 'backref' to 'back_populates' to match hiring.py
    assignment_history = db.relationship('ModeratorAssignmentHistory', back_populates='problem', lazy=True)