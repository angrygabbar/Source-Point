from app.config import Settings
from app.connectors.base import ConnectorError, ConnectorInfo, SourceConnector
from app.connectors.http import SafeHttpClient
from app.connectors.json_feed import JsonFeedConnector
from app.connectors.product_page import FlipkartProductPageConnector
from app.connectors.public_search import BraveSearchConnector, GoogleCseConnector
from app.connectors.user_submitted import UserSubmittedConnector
from app.database.models import DiscoverySource

CONNECTORS: dict[str, type[SourceConnector]] = {
    cls.key: cls
    for cls in (
        UserSubmittedConnector,
        GoogleCseConnector,
        BraveSearchConnector,
        FlipkartProductPageConnector,
        JsonFeedConnector,
    )
}


def build_connector(source: DiscoverySource, settings: Settings, http: SafeHttpClient) -> SourceConnector:
    cls = CONNECTORS.get(source.connector_key)
    if cls is None:
        raise ConnectorError(f"Unknown connector '{source.connector_key}'.")
    return cls(dict(source.config or {}), settings, http)


def connector_info(key: str) -> ConnectorInfo | None:
    cls = CONNECTORS.get(key)
    return cls.info() if cls else None
