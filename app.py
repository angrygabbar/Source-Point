import os
from dotenv import load_dotenv
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager, migrate, cache, limiter
from models.auth import User, Message
from models.learning import LearningContent
from bs4 import BeautifulSoup
from flask_login import current_user
from config import DevelopmentConfig, ProductionConfig

# Load environment variables
load_dotenv()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    
    # --- LOAD CONFIGURATION ---
    # Switch to ProductionConfig based on env var
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    from blueprints.seller import seller_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(developer_bp)
    app.register_blueprint(moderator_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(seller_bp)

    # --- GLOBAL CONTEXT PROCESSOR ---
    @app.context_processor
    def inject_messages():
        if current_user.is_authenticated:
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
    register_commands(app)

    return app

def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database tables created.")

    @app.cli.command("populate-db")
    def populate_db():
        """Seeds the database with initial Learning Content."""
        supported_languages = ['java', 'cpp', 'c', 'sql', 'dbms', 'plsql', 'mysql']
        for lang in supported_languages:
            existing_content = LearningContent.query.get(lang)
            if existing_content: 
                db.session.delete(existing_content)
            
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

# Create the app instance for Gunicorn
app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)