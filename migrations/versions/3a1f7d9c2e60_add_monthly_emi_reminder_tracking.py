"""add monthly EMI reminder tracking

Revision ID: 3a1f7d9c2e60
Revises: b671c2d9e40f
Create Date: 2026-11-02

"""
from alembic import op
import sqlalchemy as sa


revision = '3a1f7d9c2e60'
down_revision = 'b671c2d9e40f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('emi_payment', sa.Column('monthly_reminder_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('emi_payment', 'monthly_reminder_sent_at')
