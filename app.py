import traceback
import sys
import os
import logging
from logging.config import dictConfig
from dotenv import load_dotenv
from flask import Flask, render_template, flash, redirect, request
from flask_talisman import Talisman
from whitenoise import WhiteNoise
from extensions import db, bcrypt, login_manager, migrate, cache, limiter, celery
from models.auth import User, Message
from models.learning import LearningContent
from models.interview import Interview, InterviewParticipant
from bs4 import BeautifulSoup
from flask_login import current_user
from config import DevelopmentConfig, ProductionConfig
from errors import BusinessValidationError, ResourceNotFoundError, PermissionDeniedError
from enums import UserRole, OrderStatus, InvoiceStatus, ApplicationStatus, JobStatus, PaymentStatus

load_dotenv()

# --- 1. STRUCTURED LOGGING ---
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

def create_app():
    app = Flask(__name__)
    
    # Detect environment
    if os.environ.get('FLASK_DEBUG') == '0' or os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    if app.config.get('UPLOAD_FOLDER'):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- 2. PERFORMANCE: WhiteNoise ---
    app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

    # --- 3. SECURITY HEADERS ---
   # --- 3. SECURITY HEADERS ---
    csp = {
        'default-src': ["'self'", "https://cdnjs.cloudflare.com", "https://cdn.tailwindcss.com", "https://unpkg.com", "https://cdn.jsdelivr.net", "https://cdn.tiny.cloud"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com", "https://cdn.tailwindcss.com", "https://unpkg.com", "https://cdn.tiny.cloud", "https://cdn.jsdelivr.net"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://cdnjs.cloudflare.com", "https://cdn.tailwindcss.com", "https://unpkg.com", "https://cdn.jsdelivr.net", "https://cdn.tiny.cloud"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
        'img-src': ["'self'", "data:", "*", "https://api.dicebear.com", "https://res.cloudinary.com"],
        # MODIFIED: Added '*' to allow images from any domain
        'connect-src': ["'self'", "https://api.dicebear.com", "https://res.cloudinary.com"]
    }
    
    is_https = app.config.get('ENV') == 'production'
    Talisman(app, content_security_policy=csp, force_https=is_https)

    # --- 4. INIT EXTENSIONS ---
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    # --- 5. CELERY INIT ---
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
        timezone=app.config.get('CELERY_TIMEZONE', 'UTC'),
        beat_schedule=app.config.get('CELERY_BEAT_SCHEDULE', {}),
        beat_scheduler=app.config.get('CELERY_BEAT_SCHEDULER', 'celery.beat.PersistentScheduler'),
        redbeat_redis_url=app.config.get('CELERY_REDBEAT_REDIS_URL'),
        enable_utc=True,
        accept_content=['json', 'pickle'],
        task_serializer='json',
        result_serializer='json',
        broker_connection_retry_on_startup=True,
        imports=['worker'] 
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # --- 6. HEALTH CHECK ---
    @app.route('/health')
    def health_check():
        try:
            db.session.execute(db.text('SELECT 1'))
            cache.get('ping')
            return {'status': 'healthy'}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'reason': str(e)}, 500
    
    # --- 7. BLUEPRINTS ---
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.admin import admin_bp
    from blueprints.admin_core import admin_core_bp
    from blueprints.admin_users import admin_users_bp
    from blueprints.admin_hiring import admin_hiring_bp
    from blueprints.admin_commerce import admin_commerce_bp
    from blueprints.buyer import buyer_bp
    from blueprints.candidate import candidate_bp
    from blueprints.developer import developer_bp
    from blueprints.moderator import moderator_bp
    from blueprints.events import events_bp
    from blueprints.recruiter import recruiter_bp
    from blueprints.seller import seller_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_core_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_hiring_bp)
    app.register_blueprint(admin_commerce_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(developer_bp)
    app.register_blueprint(moderator_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(seller_bp)

    # --- 8. CONTEXT PROCESSORS (FIXED) ---
    @app.context_processor
    def inject_messages():
        # --- FIX: Check if current_user exists and is not None (for Celery tasks) ---
        if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            cache_key = f"user_messages_{current_user.id}"
            messages = cache.get(cache_key)
            
            if messages is None:
                messages = Message.query.filter(
                    (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
                ).order_by(Message.timestamp.desc()).all()
                cache.set(cache_key, messages, timeout=60)
                
            return dict(messages=messages)
        return dict(messages=[])

    @app.context_processor
    def inject_enums():
        return dict(
            UserRole=UserRole,
            OrderStatus=OrderStatus,
            InvoiceStatus=InvoiceStatus,
            ApplicationStatus=ApplicationStatus,
            JobStatus=JobStatus,
            PaymentStatus=PaymentStatus
        )

    # --- 9. ERROR HANDLERS ---
    @app.errorhandler(BusinessValidationError)
    def handle_business_error(e):
        app.logger.warning(f"Business Error: {str(e)}")
        flash(str(e), 'danger')
        return redirect(request.referrer or '/')

    @app.errorhandler(ResourceNotFoundError)
    def handle_not_found_error(e):
        app.logger.warning(f"Not Found: {str(e)}")
        flash(str(e), 'warning')
        return render_template('404.html'), 404

    @app.errorhandler(PermissionDeniedError)
    def handle_permission_error(e):
        app.logger.warning(f"Permission Denied: {current_user.id if current_user and current_user.is_authenticated else 'Guest'}")
        flash(str(e), 'danger')
        return redirect('/')

    @app.errorhandler(404)
    def page_not_found(e): return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Critical 500 Error: {traceback.format_exc()}")
        return render_template('500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e): return render_template('404.html'), 429 

    register_commands(app)
    return app

def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database tables created.")

    @app.cli.command("populate-db")
    def populate_db():
        supported_languages = ['java', 'cpp', 'c', 'sql', 'dbms', 'plsql', 'mysql']
        for lang in supported_languages:
            existing_content = LearningContent.query.get(lang)
            if existing_content: db.session.delete(existing_content)
            try:
                file_path = f'templates/learn_{lang}.html'
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                        content_div = soup.select_one('main > div')
                        if content_div:
                            new_content = LearningContent(id=lang, content=str(content_div))
                            db.session.add(new_content)
                else:
                    db.session.add(LearningContent(id=lang, content=f"<h1>{lang.upper()}</h1><p>Content initialized.</p>"))
            except Exception as e:
                print(f"Error populating {lang}: {e}")
                db.session.add(LearningContent(id=lang, content=f"<h1>{lang.upper()}</h1><p>Coming soon.</p>"))
        db.session.commit()
        print("Database populated.")

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)