"""Use SourcePoint administrator identities for CoinBack access.

Revision ID: 0002_sourcepoint_admin_sso
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_sourcepoint_admin_sso"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "password_hash", schema="coinback")
    op.drop_column("users", "password_changed_at", schema="coinback")
    op.drop_column("users", "last_login_at", schema="coinback")
    op.alter_column("users", "username", existing_type=sa.String(length=64), type_=sa.String(length=100),
                    existing_nullable=False, schema="coinback")
    op.drop_constraint("users_username_key", "users", type_="unique", schema="coinback")
    op.add_column("users", sa.Column("sourcepoint_user_id", sa.Integer(), nullable=True), schema="coinback")
    op.create_unique_constraint("uq_coinback_users_sourcepoint_user_id", "users", ["sourcepoint_user_id"],
                                schema="coinback")
    op.create_foreign_key(
        "fk_coinback_users_sourcepoint_user",
        "users",
        "user",
        ["sourcepoint_user_id"],
        ["id"],
        source_schema="coinback",
        referent_schema="public",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_coinback_users_sourcepoint_user", "users", type_="foreignkey", schema="coinback")
    op.drop_constraint("uq_coinback_users_sourcepoint_user_id", "users", type_="unique", schema="coinback")
    op.drop_column("users", "sourcepoint_user_id", schema="coinback")
    op.create_unique_constraint("users_username_key", "users", ["username"], schema="coinback")
    op.alter_column("users", "username", existing_type=sa.String(length=100), type_=sa.String(length=64),
                    existing_nullable=False, schema="coinback")
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True), schema="coinback")
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
                  schema="coinback")
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True), schema="coinback")
