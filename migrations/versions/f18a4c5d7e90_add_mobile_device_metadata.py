"""Add Android app and device metadata to registered installations.

Revision ID: f18a4c5d7e90
Revises: 9d2a6b4c1e70
Create Date: 2026-11-21
"""

from alembic import op
import sqlalchemy as sa


revision = "f18a4c5d7e90"
down_revision = "9d2a6b4c1e70"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mobile_push_device",
        sa.Column("app_version", sa.String(length=40), server_default="", nullable=False),
    )
    op.add_column(
        "mobile_push_device",
        sa.Column("device_model", sa.String(length=160), server_default="", nullable=False),
    )
    op.add_column(
        "mobile_push_device",
        sa.Column("android_version", sa.String(length=80), server_default="", nullable=False),
    )


def downgrade():
    op.drop_column("mobile_push_device", "android_version")
    op.drop_column("mobile_push_device", "device_model")
    op.drop_column("mobile_push_device", "app_version")
