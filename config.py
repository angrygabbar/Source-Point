import os
from datetime import timedelta
from celery.schedules import crontab

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Uploads
    UPLOAD_FOLDER = os.path.join('static', 'resumes')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # --- REDIS & CELERY CONFIGURATION ---
    CACHE_TYPE = 'RedisCache'
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 500

    # Celery Configuration
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Timezone: India Standard Time
    CELERY_TIMEZONE = 'Asia/Kolkata'
    
    # RedBeat Configuration (Redis-based scheduler)
    CELERY_BEAT_SCHEDULER = 'redbeat.RedBeatScheduler'
    CELERY_REDBEAT_REDIS_URL = REDIS_URL

    # --- SCHEDULED TASKS (Celery Beat) ---
    CELERY_BEAT_SCHEDULE = {
        # 1. Invoice Reminders (9 AM & 5 PM IST)
        'send-invoice-reminders-twice-daily': {
            'task': 'worker.send_invoice_reminders_task',
            'schedule': crontab(hour='9,17', minute=0),
        },
        # 2. Finance EMI Reminders (10 AM IST Daily)
        'send-emi-reminders-daily': {
            'task': 'worker.process_emi_reminders_task',
            'schedule': crontab(hour=10, minute=0),
        },
        # 3. NEW: Hiring Event Checks (Every 15 Minutes)
        # Checks for upcoming tests (2hr reminder) AND expired tests (auto-complete)
        'check-hiring-events': {
            'task': 'worker.check_hiring_events_task',
            'schedule': crontab(minute='*/15'),
        },
    }

    # --- DATABASE POOLING OPTIMIZATION ---
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30
    }
    
    # --- GOOGLE CALENDAR API ---
    GOOGLE_CALENDAR_CREDENTIALS_FILE = os.environ.get('GOOGLE_CALENDAR_CREDENTIALS_FILE', 'credentials.json')
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
    GOOGLE_CALENDAR_TIMEZONE = os.environ.get('GOOGLE_CALENDAR_TIMEZONE', 'Asia/Kolkata')
    
    @classmethod
    def init_app(cls, app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        if not os.environ.get('SECRET_KEY'):
             print("WARNING: SECRET_KEY is not set in Production environment!")

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False