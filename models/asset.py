# Source Point/models/asset.py
from extensions import db
from datetime import datetime
from sqlalchemy import Numeric
from enums import AssetStatus, AssetCondition


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

    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    authorized_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    allocation_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(200), nullable=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_assets', lazy=True)
    authorized_by = db.relationship('User', foreign_keys=[authorized_by_id], backref='authorized_assets', lazy=True)

    def __repr__(self):
        return f'<Asset {self.asset_code}: {self.name}>'
