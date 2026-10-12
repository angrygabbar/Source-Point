"""add_asset_sale_acceptance_tracking

Revision ID: 9b2c1e7a4f80
Revises: 6d4e8f1a2c30
Create Date: 2026-10-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b2c1e7a4f80'
down_revision = '6d4e8f1a2c30'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('asset')}

    with op.batch_alter_table('asset', schema=None) as batch_op:
        if 'sale_terms_email_sent_at' not in columns:
            batch_op.add_column(sa.Column('sale_terms_email_sent_at', sa.DateTime(), nullable=True))
        if 'sale_terms_accepted_at' not in columns:
            batch_op.add_column(sa.Column('sale_terms_accepted_at', sa.DateTime(), nullable=True))
        if 'sale_terms_accepted_ip' not in columns:
            batch_op.add_column(sa.Column('sale_terms_accepted_ip', sa.String(length=64), nullable=True))
        if 'sale_terms_acceptance_user_agent' not in columns:
            batch_op.add_column(sa.Column('sale_terms_acceptance_user_agent', sa.String(length=255), nullable=True))
        if 'delivery_receipt_sent_at' not in columns:
            batch_op.add_column(sa.Column('delivery_receipt_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('delivery_receipt_sent_at')
        batch_op.drop_column('sale_terms_acceptance_user_agent')
        batch_op.drop_column('sale_terms_accepted_ip')
        batch_op.drop_column('sale_terms_accepted_at')
        batch_op.drop_column('sale_terms_email_sent_at')
