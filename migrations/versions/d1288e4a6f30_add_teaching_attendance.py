"""add teaching session attendance

Revision ID: d1288e4a6f30
Revises: c7b5e2a1f9d0
Create Date: 2026-10-19

"""
from alembic import op
import sqlalchemy as sa


revision = 'd1288e4a6f30'
down_revision = 'c7b5e2a1f9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teaching_attendance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('marked_by_id', sa.Integer(), nullable=False),
        sa.Column('marked_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('present', 'absent', 'late', 'excused')",
            name='ck_teaching_attendance_status',
        ),
        sa.ForeignKeyConstraint(['marked_by_id'], ['user.id']),
        sa.ForeignKeyConstraint(['session_id'], ['teaching_session.id']),
        sa.ForeignKeyConstraint(['student_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'session_id', 'student_id', name='uq_teaching_attendance_session_student'
        ),
    )
    op.create_index('ix_teaching_attendance_session_id', 'teaching_attendance', ['session_id'])
    op.create_index('ix_teaching_attendance_student_id', 'teaching_attendance', ['student_id'])


def downgrade():
    op.drop_index('ix_teaching_attendance_student_id', table_name='teaching_attendance')
    op.drop_index('ix_teaching_attendance_session_id', table_name='teaching_attendance')
    op.drop_table('teaching_attendance')
