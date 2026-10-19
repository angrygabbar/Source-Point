"""add teaching class announcements

Revision ID: e4c19a7f2b6d
Revises: d1288e4a6f30
Create Date: 2026-10-19

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4c19a7f2b6d'
down_revision = 'd1288e4a6f30'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teaching_announcement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['user.id']),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_teaching_announcement_class_id', 'teaching_announcement', ['class_id']
    )


def downgrade():
    op.drop_index('ix_teaching_announcement_class_id', table_name='teaching_announcement')
    op.drop_table('teaching_announcement')
