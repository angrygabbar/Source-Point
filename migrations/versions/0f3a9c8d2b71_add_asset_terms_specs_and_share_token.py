"""add_asset_terms_specs_and_share_token

Revision ID: 0f3a9c8d2b71
Revises: b53653812ad7
Create Date: 2026-10-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f3a9c8d2b71'
down_revision = 'b53653812ad7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('asset')}
    indexes = {index['name'] for index in inspector.get_indexes('asset')}

    with op.batch_alter_table('asset', schema=None) as batch_op:
        if 'processor' not in columns:
            batch_op.add_column(sa.Column('processor', sa.String(length=200), nullable=True))
        if 'ram' not in columns:
            batch_op.add_column(sa.Column('ram', sa.String(length=100), nullable=True))
        if 'storage_spec' not in columns:
            batch_op.add_column(sa.Column('storage_spec', sa.String(length=200), nullable=True))
        if 'display' not in columns:
            batch_op.add_column(sa.Column('display', sa.String(length=200), nullable=True))
        if 'graphics' not in columns:
            batch_op.add_column(sa.Column('graphics', sa.String(length=200), nullable=True))
        if 'operating_system' not in columns:
            batch_op.add_column(sa.Column('operating_system', sa.String(length=100), nullable=True))
        if 'battery' not in columns:
            batch_op.add_column(sa.Column('battery', sa.String(length=100), nullable=True))
        if 'color' not in columns:
            batch_op.add_column(sa.Column('color', sa.String(length=50), nullable=True))
        if 'terms_and_conditions' not in columns:
            batch_op.add_column(sa.Column('terms_and_conditions', sa.Text(), nullable=True))
        if 'share_token' not in columns:
            batch_op.add_column(sa.Column('share_token', sa.String(length=64), nullable=True))
        if batch_op.f('ix_asset_share_token') not in indexes:
            batch_op.create_index(batch_op.f('ix_asset_share_token'), ['share_token'], unique=True)


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_asset_share_token'))
        batch_op.drop_column('share_token')
        batch_op.drop_column('terms_and_conditions')
        batch_op.drop_column('color')
        batch_op.drop_column('battery')
        batch_op.drop_column('operating_system')
        batch_op.drop_column('graphics')
        batch_op.drop_column('display')
        batch_op.drop_column('storage_spec')
        batch_op.drop_column('ram')
        batch_op.drop_column('processor')
