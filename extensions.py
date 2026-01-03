from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)

# Redirect users to this endpoint if they aren't logged in
login_manager.login_view = 'auth.login_register'
login_manager.login_message_category = 'info'