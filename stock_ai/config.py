import os

# Database Credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433") # Default to 5433 per your setup
DB_NAME = os.getenv("DB_NAME", "stock_market")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password") # Update this if you have a password

# Connection String
DB_CONN_STR = f"dbname={DB_NAME} user={DB_USER} password={DB_PASS} host={DB_HOST} port={DB_PORT}"

# App Settings
SECRET_KEY = os.getenv("SECRET_KEY", "stock_ai_super_secret_key_v5")
SOURCEPOINT_SSO_SECRET = os.getenv("SOURCEPOINT_SSO_SECRET", "")
SOURCEPOINT_SSO_REQUIRED = os.getenv("SOURCEPOINT_SSO_REQUIRED", "true").lower() in {"1", "true", "yes"}
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() in {"1", "true", "yes"}
