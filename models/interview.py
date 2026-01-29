from extensions import db
from datetime import datetime

class Interview(db.Model):
    """Model for storing interview/meeting information"""
    __tablename__ = 'interview'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, default=60, nullable=False)
    
    # Google Calendar Integration
    google_event_id = db.Column(db.String(255), nullable=True)
    google_meet_link = db.Column(db.String(500), nullable=True)
    
    # Candidate
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Status: scheduled, completed, cancelled
    status = db.Column(db.String(20), default='scheduled', nullable=False)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='interviews_as_candidate')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_interviews')
    participants = db.relationship('InterviewParticipant', backref='interview', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Interview {self.title} - {self.scheduled_time}>'


class InterviewParticipant(db.Model):
    """Model for tracking moderators and observers in interviews"""
    __tablename__ = 'interview_participant'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Role: 'moderator' or 'observer'
    role = db.Column(db.String(20), nullable=False, default='moderator')
    
    # Metadata
    notified_at = db.Column(db.DateTime, nullable=True)
    joined_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='interview_participations')
    
    def __repr__(self):
        return f'<InterviewParticipant {self.user_id} - {self.role}>'
