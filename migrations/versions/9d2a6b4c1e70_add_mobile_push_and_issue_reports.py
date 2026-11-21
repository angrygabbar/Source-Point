"""Add Android push registration and issue reporting tables."""

from alembic import op
import sqlalchemy as sa


revision = "9d2a6b4c1e70"
down_revision = "4b8d2c1f6a90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mobile_push_device",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("installation_id", sa.String(length=128), nullable=False),
        sa.Column("installation_id_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=24), server_default="android", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mobile_push_device_user_id", "mobile_push_device", ["user_id"])
    op.create_index("ix_mobile_push_device_installation_id_hash", "mobile_push_device", ["installation_id_hash"], unique=True)

    op.create_table(
        "mobile_issue_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference_code", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=80), server_default="USER_REPORTED", nullable=False),
        sa.Column("screen", sa.String(length=160), server_default="", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("app_version", sa.String(length=40), server_default="", nullable=False),
        sa.Column("device_model", sa.String(length=160), server_default="", nullable=False),
        sa.Column("android_version", sa.String(length=80), server_default="", nullable=False),
        sa.Column("diagnostic_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mobile_issue_report_reference_code", "mobile_issue_report", ["reference_code"], unique=True)
    op.create_index("ix_mobile_issue_report_user_id", "mobile_issue_report", ["user_id"])
    op.create_index("ix_mobile_issue_report_status", "mobile_issue_report", ["status"])
    op.create_index("ix_mobile_issue_report_created_at", "mobile_issue_report", ["created_at"])


def downgrade():
    op.drop_index("ix_mobile_issue_report_created_at", table_name="mobile_issue_report")
    op.drop_index("ix_mobile_issue_report_status", table_name="mobile_issue_report")
    op.drop_index("ix_mobile_issue_report_user_id", table_name="mobile_issue_report")
    op.drop_index("ix_mobile_issue_report_reference_code", table_name="mobile_issue_report")
    op.drop_table("mobile_issue_report")
    op.drop_index("ix_mobile_push_device_installation_id_hash", table_name="mobile_push_device")
    op.drop_index("ix_mobile_push_device_user_id", table_name="mobile_push_device")
    op.drop_table("mobile_push_device")
