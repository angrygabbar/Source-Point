# Source Point/models/asset.py
from extensions import db
from datetime import datetime
from sqlalchemy import Numeric
from enums import AssetStatus, AssetCondition
import uuid


class Asset(db.Model):
    __tablename__ = 'asset'

    id = db.Column(db.Integer, primary_key=True)
    asset_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False, index=True)
    serial_number = db.Column(db.String(200), nullable=True)
    brand = db.Column(db.String(100), nullable=True)
    model_number = db.Column(db.String(150), nullable=True)

    # Purchase Details
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(Numeric(12, 2), nullable=True)
    warranty_expiry = db.Column(db.Date, nullable=True)

    # Status & Condition
    status = db.Column(db.String(30), default=AssetStatus.ACTIVE.value, nullable=False, index=True)
    condition = db.Column(db.String(30), default=AssetCondition.NEW.value, nullable=False)

    # ── Hardware Specifications ──
    processor = db.Column(db.String(200), nullable=True)
    ram = db.Column(db.String(100), nullable=True)
    storage_spec = db.Column(db.String(200), nullable=True)
    display = db.Column(db.String(200), nullable=True)
    graphics = db.Column(db.String(200), nullable=True)
    operating_system = db.Column(db.String(100), nullable=True)
    battery = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)

    # Assignment
    asset_action = db.Column(db.String(20), nullable=True, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    authorized_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    allocation_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(200), nullable=True)

    # Sale Details
    sold_to_name = db.Column(db.String(150), nullable=True)
    sold_to_email = db.Column(db.String(120), nullable=True)
    sold_date = db.Column(db.Date, nullable=True)
    sale_price = db.Column(Numeric(12, 2), nullable=True)

    # Terms & Conditions
    terms_and_conditions = db.Column(db.Text, nullable=True)
    sale_terms_email_sent_at = db.Column(db.DateTime, nullable=True)
    sale_terms_accepted_at = db.Column(db.DateTime, nullable=True)
    sale_terms_accepted_ip = db.Column(db.String(64), nullable=True)
    sale_terms_acceptance_user_agent = db.Column(db.String(255), nullable=True)
    delivery_receipt_sent_at = db.Column(db.DateTime, nullable=True)

    # Cancellation
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)

    # Shareable public page token (auto-generated)
    share_token = db.Column(db.String(64), unique=True, nullable=True, index=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_assets', lazy=True)
    authorized_by = db.relationship('User', foreign_keys=[authorized_by_id], backref='authorized_assets', lazy=True)

    def generate_share_token(self):
        """Generate a unique share token for this asset's public page."""
        self.share_token = uuid.uuid4().hex
        return self.share_token

    def __repr__(self):
        return f'<Asset {self.asset_code}: {self.name}>'
