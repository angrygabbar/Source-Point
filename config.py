# Source Point/config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Uploads
    UPLOAD_FOLDER = os.path.join('static', 'resumes')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Cache (Simple for Dev, Redis for Prod recommended)
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 200

    # DB Pooling (Stability)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 2,
        "max_overflow": 1,
        "pool_timeout": 30
    }
    
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
    
    # In production, ensure we don't use default keys
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Security Enhancement: Fail fast if no secret key
        if not os.environ.get('SECRET_KEY'):
             raise RuntimeError("CRITICAL: SECRET_KEY is not set in Production environment!")

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory DB for tests
    WTF_CSRF_ENABLED = False # Disable CSRF for easier testing