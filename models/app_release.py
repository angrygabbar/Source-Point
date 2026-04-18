from extensions import db
from datetime import datetime


class AndroidAppRelease(db.Model):
    """Stores metadata for Android APK releases uploaded by admin."""
    __tablename__ = 'android_app_release'

    id = db.Column(db.Integer, primary_key=True)
    version_name = db.Column(db.String(50), nullable=False)
    version_code = db.Column(db.Integer, nullable=False, default=1)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)
    release_notes = db.Column(db.Text, nullable=False, default='')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    uploaded_by = db.relationship('User', backref='app_releases', lazy=True)

    def file_size_human(self):
        if not self.file_size:
            return 'Unknown'
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def __repr__(self):
        return f'<AndroidAppRelease v{self.version_name}>'


class AppFeature(db.Model):
    """App features shown on the public download page — managed by admin."""
    __tablename__ = 'app_feature'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon        = db.Column(db.String(80), nullable=False, default='fa-star')
    color       = db.Column(db.String(30), nullable=False, default='emerald')
    sort_order  = db.Column(db.Integer, nullable=False, default=0)
    is_active   = db.Column(db.Boolean, default=True, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<AppFeature {self.title}>'
