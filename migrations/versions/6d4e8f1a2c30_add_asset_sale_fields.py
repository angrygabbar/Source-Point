"""add_asset_sale_fields

Revision ID: 6d4e8f1a2c30
Revises: 0f3a9c8d2b71
Create Date: 2026-10-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d4e8f1a2c30'
down_revision = '0f3a9c8d2b71'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('asset_action', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('sold_to_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('sold_to_email', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('sold_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('sale_price', sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.create_index(batch_op.f('ix_asset_asset_action'), ['asset_action'], unique=False)


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_asset_asset_action'))
        batch_op.drop_column('sale_price')
        batch_op.drop_column('sold_date')
        batch_op.drop_column('sold_to_email')
        batch_op.drop_column('sold_to_name')
        batch_op.drop_column('asset_action')
