from sqlalchemy import func

from models.auth import User


def find_invoice_recipient(email):
    """Return the account matching an invoice recipient email, if one exists."""
    normalized_email = (email or '').strip().lower()
    if not normalized_email:
        return None
    return User.query.filter(func.lower(func.trim(User.email)) == normalized_email).first()


def invoice_recipient_id(email):
    recipient = find_invoice_recipient(email)
    return recipient.id if recipient else None
