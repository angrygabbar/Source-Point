"""add_rollback_terms_tables

Revision ID: 7c2b9f1e4a6d
Revises: e88696ba1bc6
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '7c2b9f1e4a6d'
down_revision = 'e88696ba1bc6'
branch_labels = None
depends_on = None


DEFAULT_ROLLBACK_TERMS_CONTENT = """<h2>Inventory Rollback Terms</h2>
<ol>
  <li>Rollback requests are only for inventory that is currently assigned to your seller account.</li>
  <li>The requested rollback quantity cannot exceed your available seller inventory.</li>
  <li>Submitting a rollback request does not immediately change stock. Inventory moves back to master stock only after admin approval.</li>
  <li>You must provide accurate product and quantity details. Incorrect requests may be rejected by the admin team.</li>
  <li>Approved rollback quantities will be deducted from your seller inventory and added back to master inventory.</li>
  <li>Rejected requests will not change your seller inventory.</li>
  <li>Admin notes and decisions are final for each submitted rollback request.</li>
  <li>You are responsible for reviewing the latest terms before using the rollback feature.</li>
</ol>"""


def upgrade():
    now = datetime.utcnow()
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'inventory_rollback_terms' not in tables:
        op.create_table('inventory_rollback_terms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('inventory_rollback_terms', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_is_active'), ['is_active'], unique=False)
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_version'), ['version'], unique=True)

        op.create_table('inventory_rollback_terms_decision',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('terms_id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('decided_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['seller_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['terms_id'], ['inventory_rollback_terms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('terms_id', 'seller_id', name='uq_rollback_terms_decision_terms_seller')
        )
        with op.batch_alter_table('inventory_rollback_terms_decision', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_decision_decided_at'), ['decided_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_decision_decision'), ['decision'], unique=False)
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_decision_seller_id'), ['seller_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_inventory_rollback_terms_decision_terms_id'), ['terms_id'], unique=False)

        terms_table = sa.table(
            'inventory_rollback_terms',
            sa.column('version', sa.Integer),
            sa.column('title', sa.String),
            sa.column('content', sa.Text),
            sa.column('is_active', sa.Boolean),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        )
        op.bulk_insert(terms_table, [{
            'version': 1,
            'title': 'Inventory Rollback Terms and Conditions',
            'content': DEFAULT_ROLLBACK_TERMS_CONTENT,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }])


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'inventory_rollback_terms_decision' in tables:
        with op.batch_alter_table('inventory_rollback_terms_decision', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_decision_terms_id'))
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_decision_seller_id'))
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_decision_decision'))
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_decision_decided_at'))
        op.drop_table('inventory_rollback_terms_decision')

    if 'inventory_rollback_terms' in tables:
        with op.batch_alter_table('inventory_rollback_terms', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_version'))
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_is_active'))
            batch_op.drop_index(batch_op.f('ix_inventory_rollback_terms_created_at'))
        op.drop_table('inventory_rollback_terms')
