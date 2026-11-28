from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Institute Management System"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "insecure-development-key-change-me"
    ENCRYPTION_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 14
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    PASSWORD_RESET_MINUTES: int = 60
    COOKIE_SECURE: bool = False
    CORS_ORIGINS: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:8080"
    SOURCEPOINT_SSO_SECRET: str = ""

    DATABASE_URL: str = "postgresql+psycopg://classflow:classflow@localhost:5432/classflow"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    REDIS_URL: str = "redis://localhost:6379/0"

    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "classflow"
    S3_REGION: str = "us-east-1"

    MAX_UPLOAD_MB: int = 25
    ALLOWED_UPLOAD_EXTENSIONS: str = (
        "pdf,doc,docx,xls,xlsx,ppt,pptx,txt,csv,rtf,odt,ods,odp,png,jpg,jpeg,gif,webp,"
        "mp3,mp4,m4a,wav,webm,zip"
    )
    BLOCKED_UPLOAD_EXTENSIONS: str = (
        "exe,dll,bat,cmd,com,msi,sh,ps1,vbs,js,jar,scr,apk,app,bin,php,py,pl,rb,html,htm,svg"
    )

    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_CURRENCY: str = "INR"

    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCK_MINUTES: int = 15
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    MAX_PAGE_SIZE: int = 200
    SYNC_EXPORT_ROW_LIMIT: int = 5000

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@example.com"

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if e.strip()}

    @property
    def blocked_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.BLOCKED_UPLOAD_EXTENSIONS.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_production:
        if len(s.SECRET_KEY) < 32 or "change-me" in s.SECRET_KEY or "insecure" in s.SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be a long random value in production")
        if not s.ENCRYPTION_KEY or "change-me" in s.ENCRYPTION_KEY:
            raise RuntimeError("ENCRYPTION_KEY must be configured in production")
    return s


settings = get_settings()
