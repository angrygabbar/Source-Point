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


class InterviewFeedback(db.Model):
    """Model for storing interview feedback from moderators"""
    __tablename__ = 'interview_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Interview-specific ratings (1-5 scale)
    communication_skills = db.Column(db.Integer, nullable=False, default=0)
    technical_knowledge = db.Column(db.Integer, nullable=False, default=0)
    problem_solving = db.Column(db.Integer, nullable=False, default=0)
    cultural_fit = db.Column(db.Integer, nullable=False, default=0)
    overall_impression = db.Column(db.Integer, nullable=False, default=0)
    
    # Recommendation: 'hire', 'maybe', 'no_hire'
    recommendation = db.Column(db.String(20), nullable=False, default='maybe')
    
    # Detailed remarks
    remarks = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    interview = db.relationship('Interview', backref=db.backref('feedbacks', lazy=True))
    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='interview_feedback_given')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='interview_feedback_received')
    
    @property
    def rating(self):
        """Calculates average rating from the 5 parameters."""
        try:
            total = (self.communication_skills + self.technical_knowledge + 
                     self.problem_solving + self.cultural_fit + 
                     self.overall_impression)
            return round(total / 5, 1)
        except TypeError:
            return 0
    
    def __repr__(self):
        return f'<InterviewFeedback {self.id} - Interview {self.interview_id}>'
