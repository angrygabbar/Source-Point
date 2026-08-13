"""Add InvoicePayment model

Revision ID: b53653812ad7
Revises: 3dc0065e59f8
Create Date: 2026-08-13 14:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b53653812ad7'
down_revision = '3dc0065e59f8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('invoice_payment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('recorded_by_id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoice.id'], ),
        sa.ForeignKeyConstraint(['recorded_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('invoice_payment')
