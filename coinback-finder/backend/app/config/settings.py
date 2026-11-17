from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Environment-driven configuration. Secrets live only in the environment, never in the database."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "production"
    log_level: str = "INFO"

    database_url: str = Field(..., description="postgresql+psycopg://user:pass@db:5432/coinback")
    # Retained for compatibility with the old auth helpers; CoinBack login is disabled.
    secret_key: str = Field(default="coinback-sourcepoint-module-secret-disabled", min_length=32)
    coinback_sso_secret: str = Field(..., min_length=32)

    session_cookie_name: str = "cbf_session"
    session_ttl_minutes: int = Field(default=720, ge=15, le=10080)
    cookie_secure: bool = True
    cors_origins: str = ""
    login_rate_limit_per_minute: int = Field(default=10, ge=1, le=100)

    display_timezone: str = "Asia/Kolkata"
    currency: str = "INR"

    flipkart_allowed_hosts: str = "www.flipkart.com,flipkart.com,dl.flipkart.com"
    third_party_allowed_hosts: str = ""
    http_timeout_seconds: float = Field(default=15.0, ge=1, le=60)
    http_user_agent: str = "CoinBackFinder/1.0 (private price monitor)"

    default_scan_interval_minutes: int = Field(default=15, ge=5, le=1440)
    scanner_enabled: bool = True

    # Product-page access stays off unless the operator has confirmed permission to access pages automatically.
    product_page_fetch_enabled: bool = False
    product_page_permission_confirmed: bool = False

    google_cse_api_key: str | None = None
    google_cse_engine_id: str | None = None
    brave_search_api_key: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_dry_run: bool = True
    telegram_commands_enabled: bool = False

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def flipkart_host_list(self) -> list[str]:
        return _csv(self.flipkart_allowed_hosts)

    @property
    def third_party_host_list(self) -> list[str]:
        return _csv(self.third_party_allowed_hosts)

    @property
    def product_page_access_permitted(self) -> bool:
        return self.product_page_fetch_enabled and self.product_page_permission_confirmed

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
