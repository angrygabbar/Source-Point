import os
from dotenv import load_dotenv
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager, migrate, cache, limiter
from models.auth import User, Message
from models.learning import LearningContent
from bs4 import BeautifulSoup
from flask_login import current_user
from config import DevelopmentConfig, ProductionConfig

load_dotenv()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    # --- REGISTER BLUEPRINTS ---
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    
    # NEW: Split Admin Blueprints
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
    
    # Register Admin Modules
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

    @app.context_processor
    def inject_messages():
        if current_user.is_authenticated:
            messages = Message.query.filter(
                (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
            ).order_by(Message.timestamp.desc()).all()
            return dict(messages=messages)
        return dict(messages=[])

    @app.errorhandler(404)
    def page_not_found(e): return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e): return render_template('500.html'), 500
    
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
        print("Database populated with learning content.")

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)