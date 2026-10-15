"""add_travel_invoice_types

Revision ID: 8a1e4c6b2d90
Revises: 4c2f8a7e1b96
Create Date: 2026-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a1e4c6b2d90'
down_revision = '4c2f8a7e1b96'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = {column['name'] for column in sa.inspect(conn).get_columns('invoice')}

    with op.batch_alter_table('invoice', schema=None) as batch_op:
        if 'invoice_type' not in columns:
            batch_op.add_column(sa.Column(
                'invoice_type', sa.String(length=20), nullable=False, server_default='ecommerce'
            ))
        if 'booking_details' not in columns:
            batch_op.add_column(sa.Column('booking_details', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.drop_column('booking_details')
        batch_op.drop_column('invoice_type')
