from dotenv import load_dotenv
import os
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager, migrate
from models import User, Message, LearningContent
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from utils import send_email

# Load env
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
    app.config['UPLOAD_FOLDER'] = 'static/resumes'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Import and Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.admin import admin_bp
    from blueprints.buyer import buyer_bp
    from blueprints.candidate import candidate_bp
    from blueprints.developer import developer_bp
    from blueprints.moderator import moderator_bp
    from blueprints.events import events_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(developer_bp)
    app.register_blueprint(moderator_bp)
    app.register_blueprint(events_bp)

    # Global Context Processor
    @app.context_processor
    def inject_messages():
        from flask_login import current_user
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            messages = Message.query.filter(
                (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
            ).order_by(Message.timestamp.desc()).all()
            return dict(messages=messages)
        return dict(messages=[])

    # CLI Commands
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
                with open(f'templates/learn_{lang}.html', 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    content_div = soup.select_one('main > div')
                    if content_div:
                        new_content = LearningContent(id=lang, content=str(content_div))
                        db.session.add(new_content)
            except FileNotFoundError:
                db.session.add(LearningContent(id=lang, content=f"<h1>{lang.upper()}</h1><p>Coming soon.</p>"))
        db.session.commit()
        print("Database populated.")

    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Scheduler Logic (Dev Only)
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

if os.environ.get('FLASK_ENV') == 'development':
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(check_completed_tests, 'interval', minutes=15)
    scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)