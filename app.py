import traceback
import sys
import os
from dotenv import load_dotenv
from flask import Flask, render_template, flash, redirect, request
from extensions import db, bcrypt, login_manager, migrate, cache, limiter, celery
from models.auth import User, Message
from models.learning import LearningContent
from bs4 import BeautifulSoup
from flask_login import current_user
from config import DevelopmentConfig, ProductionConfig
from errors import BusinessValidationError, ResourceNotFoundError, PermissionDeniedError
from enums import UserRole, OrderStatus, InvoiceStatus, ApplicationStatus, JobStatus, PaymentStatus

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Detect environment (UPDATED for Robustness)
    # Checks FLASK_DEBUG or falls back to FLASK_ENV for legacy support
    if os.environ.get('FLASK_DEBUG') == '0' or os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    if app.config.get('UPLOAD_FOLDER'):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    # --- CELERY INIT (FIXED) ---
    # We explicitly map Flask's uppercase keys to Celery's lowercase keys.
    # We do NOT pass the entire app.config to avoid "Cannot mix new and old setting keys" errors.
   
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
        timezone=app.config.get('CELERY_TIMEZONE', 'UTC'),
        enable_utc=True,
        accept_content=['json', 'pickle'],
        task_serializer='json',
        result_serializer='json',
        # FIX: Silence the startup deprecation warning
        broker_connection_retry_on_startup=True,
        # Explicitly tell Celery where the tasks are
        imports=['worker'] 
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    # -------------------

    # --- REGISTER BLUEPRINTS ---
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    
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

    # --- CONTEXT PROCESSORS ---
    @app.context_processor
    def inject_messages():
        if current_user.is_authenticated:
            # OPTIMIZATION: Cache the message query to reduce DB load
            cache_key = f"user_messages_{current_user.id}"
            messages = cache.get(cache_key)
            
            if messages is None:
                messages = Message.query.filter(
                    (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
                ).order_by(Message.timestamp.desc()).all()
                # Cache for 60 seconds
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

    # --- ERROR HANDLERS ---
    @app.errorhandler(BusinessValidationError)
    def handle_business_error(e):
        flash(str(e), 'danger')
        return redirect(request.referrer or '/')

    @app.errorhandler(ResourceNotFoundError)
    def handle_not_found_error(e):
        flash(str(e), 'warning')
        return render_template('404.html'), 404

    @app.errorhandler(PermissionDeniedError)
    def handle_permission_error(e):
        flash(str(e), 'danger')
        return redirect('/')

    @app.errorhandler(404)
    def page_not_found(e): return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        print("CRITICAL SERVER ERROR:", file=sys.stderr)
        traceback.print_exc()
        print("------------------------------------------------", file=sys.stderr)
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