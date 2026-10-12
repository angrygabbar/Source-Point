from datetime import datetime

from extensions import db
from utils import send_email


ASSET_ACTION_ASSIGNED = 'assigned'
ASSET_ACTION_SOLD = 'sold'


def _ensure_share_token(asset):
    """Create a public asset token before rendering email links."""
    if asset.share_token:
        return

    asset.generate_share_token()
    db.session.commit()


def send_asset_assignment_email(asset, user):
    """Send an asset assignment email to a registered user."""
    if not user or not user.email:
        return False

    _ensure_share_token(asset)

    try:
        send_email(
            to=user.email,
            subject=f"Asset Assigned: {asset.name} ({asset.asset_code})",
            template='mail/asset_assigned.html',
            asset=asset,
            user=user,
            authorized_by=asset.authorized_by,
            now=datetime.utcnow(),
        )
        return True
    except Exception as exc:
        print(f"Failed to send asset assignment email: {exc}")
        return False


def send_asset_sale_terms_email(asset):
    """Send the sale terms acceptance email before delivery receipt."""
    if not asset.sold_to_email:
        return False

    _ensure_share_token(asset)

    try:
        send_email(
            to=asset.sold_to_email,
            subject=f"Action Required: Accept Terms for {asset.name} ({asset.asset_code})",
            template='mail/asset_sale_terms_acceptance.html',
            asset=asset,
            recipient_name=asset.sold_to_name or asset.sold_to_email,
            authorized_by=asset.authorized_by,
            now=datetime.utcnow(),
        )
        asset.sale_terms_email_sent_at = datetime.utcnow()
        db.session.commit()
        return True
    except Exception as exc:
        print(f"Failed to send asset sale terms email: {exc}")
        return False


def send_asset_delivery_receipt_email(asset):
    """Send the asset delivery receipt after terms acceptance."""
    if not asset.sold_to_email or not asset.sale_terms_accepted_at:
        return False

    try:
        send_email(
            to=asset.sold_to_email,
            subject=f"Asset Delivery Receipt: {asset.name} ({asset.asset_code})",
            template='mail/asset_delivery_receipt.html',
            asset=asset,
            recipient_name=asset.sold_to_name or asset.sold_to_email,
            authorized_by=asset.authorized_by,
            now=datetime.utcnow(),
        )
        asset.delivery_receipt_sent_at = datetime.utcnow()
        db.session.commit()
        return True
    except Exception as exc:
        print(f"Failed to send asset delivery receipt email: {exc}")
        return False
