from dotenv import load_dotenv
import os
from flask import Flask, render_template, redirect, url_for
from extensions import db, bcrypt, login_manager, migrate, cache, limiter
from models import User, Message, LearningContent
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from utils import send_email
from flask_login import login_required, current_user

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # --- CONFIGURATION ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30) 
    
    # --- CACHE CONFIG (In-Memory for Free Tier) ---
    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300 # 5 minutes default

    # Uploads 
    app.config['UPLOAD_FOLDER'] = 'static/resumes'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- DATABASE POOLING STABILITY ---
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,  
        "pool_recycle": 280,    
        "pool_size": 10,        
        "max_overflow": 20      
    }

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    # --- REGISTER BLUEPRINTS ---
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.admin import admin_bp
    from blueprints.buyer import buyer_bp
    from blueprints.candidate import candidate_bp
    from blueprints.developer import developer_bp
    from blueprints.moderator import moderator_bp
    from blueprints.events import events_bp
    from blueprints.recruiter import recruiter_bp
    from blueprints.seller import seller_bp  # <--- IMPORT SELLER

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(developer_bp)
    app.register_blueprint(moderator_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(seller_bp)  # <--- REGISTER SELLER

    # --- GLOBAL CONTEXT PROCESSOR ---
    @app.context_processor
    def inject_messages():
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            messages = Message.query.filter(
                (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
            ).order_by(Message.timestamp.desc()).all()
            return dict(messages=messages)
        return dict(messages=[])

    # --- ERROR HANDLERS ---
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('404.html'), 429 

    # --- CLI COMMANDS ---
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
        print("Database populated with learning content.")

    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- TEMPORARY FIX ROUTE (RUN ONCE THEN DELETE) ---
@app.route('/force-seller-role')
@login_required
def force_seller_role():
    from flask_login import logout_user
    
    # Update the current user's role to seller
    user = User.query.get(current_user.id)
    user.role = 'seller'
    db.session.commit()
    
    # Log them out so the session refreshes cleanly
    logout_user()
    
    return "<h1>Success! Your account is now a SELLER. <a href='/login-register'>Click here to Login again</a></h1>"

# --- BACKGROUND SCHEDULER ---
def check_completed_tests():
    with app.app_context():
        now = datetime.utcnow()
        completed_candidates = User.query.filter(
            User.role == 'candidate',
            User.test_end_time <= now,
            User.test_completed == False,
            User.problem_statement_id != None
        ).all()

        if completed_candidates:
            for candidate in completed_candidates:
                problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "your assigned problem"
                if send_email(to=candidate.email, subject="Test Completed", template="mail/test_completed_candidate.html", candidate=candidate, problem_title=problem_title):
                    candidate.test_completed = True
                    db.session.commit()
            print(f"Checked tests: {len(completed_candidates)} marked as completed.")

if os.environ.get('FLASK_ENV') == 'development':
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(check_completed_tests, 'interval', minutes=15)
    scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)