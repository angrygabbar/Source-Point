from extensions import db
from datetime import datetime


class NewsArticle(db.Model):
    """
    Stores Technology news articles fetched automatically from Google News RSS.
    Articles are deduplicated by source_url to prevent storing the same article twice.
    Full article content is scraped from the source for internal display.
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
    category = db.Column(db.String(50), default='technology')
    is_sent = db.Column(db.Boolean, default=False)

    # Full article content (scraped from source)
    content = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(300), nullable=True)

    @property
    def has_content(self):
        """Check if full article content has been scraped."""
        return bool(self.content and len(self.content.strip()) > 50)

    @property
    def reading_time(self):
        """Estimate reading time in minutes (average 200 words/min)."""
        if not self.content:
            return 1
        word_count = len(self.content.split())
        minutes = max(1, round(word_count / 200))
        return minutes

    def __repr__(self):
        return f'<NewsArticle {self.id}: {self.title[:50]}>'
