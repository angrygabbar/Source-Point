from datetime import datetime

from extensions import db


class MobilePushDevice(db.Model):
    __tablename__ = "mobile_push_device"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    installation_id = db.Column(db.String(128), nullable=False)
    installation_id_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    platform = db.Column(db.String(24), nullable=False, default="android", server_default="android")
    app_version = db.Column(db.String(40), nullable=False, default="", server_default="")
    device_model = db.Column(db.String(160), nullable=False, default="", server_default="")
    android_version = db.Column(db.String(80), nullable=False, default="", server_default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("mobile_push_devices", lazy=True, cascade="all, delete-orphan"))


class MobileIssueReport(db.Model):
    __tablename__ = "mobile_issue_report"

    id = db.Column(db.Integer, primary_key=True)
    reference_code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    error_code = db.Column(db.String(80), nullable=False, default="USER_REPORTED", server_default="USER_REPORTED")
    screen = db.Column(db.String(160), nullable=False, default="", server_default="")
    description = db.Column(db.Text, nullable=False)
    app_version = db.Column(db.String(40), nullable=False, default="", server_default="")
    device_model = db.Column(db.String(160), nullable=False, default="", server_default="")
    android_version = db.Column(db.String(80), nullable=False, default="", server_default="")
    diagnostic_data = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(24), nullable=False, default="open", server_default="open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User", backref=db.backref("mobile_issue_reports", lazy=True))
