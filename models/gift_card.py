# Source Point/models/gift_card.py
from extensions import db
from datetime import datetime
from cryptography.fernet import Fernet
from enums import GiftCardStatus
import os

def _get_cipher():
    """Get Fernet cipher using the encryption key from environment."""
    key = os.environ.get('GIFT_CARD_ENCRYPTION_KEY')
    if not key:
        raise ValueError("GIFT_CARD_ENCRYPTION_KEY environment variable is not set.")
    return Fernet(key.encode() if isinstance(key, str) else key)

class GiftCard(db.Model):
    __tablename__ = 'gift_card'
    
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False, index=True)
    denomination = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    
    # Encrypted fields — NEVER store plaintext
    card_number_encrypted = db.Column(db.Text, nullable=False)
    pin_encrypted = db.Column(db.Text, nullable=False)
    
    expiry_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default=GiftCardStatus.AVAILABLE.value, nullable=False, index=True)
    
    # Recipient info (populated when sent)
    recipient_name = db.Column(db.String(150), nullable=True)
    recipient_email = db.Column(db.String(150), nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Audit
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_gift_cards')
    sent_by = db.relationship('User', foreign_keys=[sent_by_id], backref='sent_gift_cards')

    # --- ENCRYPTION HELPERS ---
    def set_card_number(self, plaintext):
        """Encrypt and store the card number."""
        cipher = _get_cipher()
        self.card_number_encrypted = cipher.encrypt(plaintext.encode()).decode()

    def get_card_number(self):
        """Decrypt and return the card number."""
        cipher = _get_cipher()
        return cipher.decrypt(self.card_number_encrypted.encode()).decode()

    def set_pin(self, plaintext):
        """Encrypt and store the PIN."""
        cipher = _get_cipher()
        self.pin_encrypted = cipher.encrypt(plaintext.encode()).decode()

    def get_pin(self):
        """Decrypt and return the PIN."""
        cipher = _get_cipher()
        return cipher.decrypt(self.pin_encrypted.encode()).decode()

    @property
    def masked_card_number(self):
        """Return masked card number for display (e.g., ****1234)."""
        try:
            full = self.get_card_number()
            if len(full) <= 4:
                return '****'
            return '●' * (len(full) - 4) + full[-4:]
        except Exception:
            return '●●●●●●●●'

    @property
    def masked_pin(self):
        """Return masked PIN for display."""
        try:
            full = self.get_pin()
            return '●' * len(full)
        except Exception:
            return '●●●●'

    @property
    def is_expired(self):
        """Check if the gift card is past its expiry date."""
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.utcnow().date()

    def __repr__(self):
        return f'<GiftCard {self.brand} ****{self.masked_card_number[-4:]}>'
