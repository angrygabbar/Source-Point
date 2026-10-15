"""add_asset_cancellation_fields

Revision ID: 4c2f8a7e1b96
Revises: 9b2c1e7a4f80
Create Date: 2026-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c2f8a7e1b96'
down_revision = '9b2c1e7a4f80'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = {column['name'] for column in sa.inspect(conn).get_columns('asset')}

    with op.batch_alter_table('asset', schema=None) as batch_op:
        if 'cancelled_at' not in columns:
            batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        if 'cancellation_reason' not in columns:
            batch_op.add_column(sa.Column('cancellation_reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('cancellation_reason')
        batch_op.drop_column('cancelled_at')
