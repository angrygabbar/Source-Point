from extensions import db
from datetime import datetime


class NewsArticle(db.Model):
    """
    Stores AI & Technology news articles fetched automatically from Google News RSS.
    Articles are deduplicated by source_url to prevent storing the same article twice.
    """
    __tablename__ = 'news_article'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    source_name = db.Column(db.String(200), nullable=True)
    source_url = db.Column(db.String(1000), nullable=False, unique=True)
    image_url = db.Column(db.String(1000), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), default='ai_tech')
    is_sent = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<NewsArticle {self.id}: {self.title[:50]}>'
