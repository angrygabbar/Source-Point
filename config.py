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
    
    # --- REDIS CACHE CONFIGURATION (UPDATED) ---
    # Switch from 'SimpleCache' to 'RedisCache' for high concurrency
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 500  # Stores more items now that we have a dedicated server

    # --- DATABASE POOLING OPTIMIZATION (UPDATED) ---
    # Optimized for 12GB RAM server (High Throughput)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Auto-detect and remove dead connections
        "pool_recycle": 280,    # Recycle connections before database timeout
        "pool_size": 20,        # Base number of connections (Increased from 2)
        "max_overflow": 10,     # Max extra connections during spikes (Increased from 1)
        "pool_timeout": 30      # Wait 30s for a connection before failing
    }
    
    @classmethod
    def init_app(cls, app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Fallback to sqlite if no URL is present (local testing outside docker)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Ensure secret key is set in production
        if not os.environ.get('SECRET_KEY'):
             print("WARNING: SECRET_KEY is not set in Production environment! Session security is at risk.")

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False