from app.connectors.base import SourceConnector
from app.database.enums import SourceType


class UserSubmittedConnector(SourceConnector):
    """Attribution source for operator-submitted URLs; products are added via the API, not discovered."""

    key = "user_submitted"
    display_name = "User-submitted URLs"
    source_type = SourceType.USER_SUBMITTED
    permitted_use = "Operator-provided product URLs validated against the Flipkart allowlist."
    default_rate_limit_per_minute = 30
    supports_discovery = False

    def is_configured(self) -> tuple[bool, str | None]:
        return True, None
