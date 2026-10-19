"""add teaching management module

Revision ID: c7b5e2a1f9d0
Revises: 8a1e4c6b2d90
Create Date: 2026-10-18

"""
from alembic import op
import sqlalchemy as sa


revision = 'c7b5e2a1f9d0'
down_revision = '8a1e4c6b2d90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teaching_class',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=True),
        sa.Column('level', sa.String(length=80), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timezone_name', sa.String(length=64), nullable=False),
        sa.Column('invite_code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['teacher_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_class_teacher_id', 'teaching_class', ['teacher_id'])
    op.create_index('ix_teaching_class_invite_code', 'teaching_class', ['invite_code'], unique=True)

    op.create_table(
        'teaching_enrollment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.ForeignKeyConstraint(['student_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_id', 'student_id', name='uq_teaching_class_student'),
    )
    op.create_index('ix_teaching_enrollment_class_id', 'teaching_enrollment', ['class_id'])
    op.create_index('ix_teaching_enrollment_student_id', 'teaching_enrollment', ['student_id'])

    op.create_table(
        'teaching_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('meeting_url', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_session_class_id', 'teaching_session', ['class_id'])
    op.create_index('ix_teaching_session_starts_at', 'teaching_session', ['starts_at'])

    op.create_table(
        'teaching_material',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_material_class_id', 'teaching_material', ['class_id'])

    op.create_table(
        'teaching_assignment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_assignment_class_id', 'teaching_assignment', ['class_id'])
    op.create_index('ix_teaching_assignment_due_at', 'teaching_assignment', ['due_at'])

    op.create_table(
        'teaching_submission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('grade', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('graded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['teaching_assignment.id']),
        sa.ForeignKeyConstraint(['student_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assignment_id', 'student_id', name='uq_teaching_assignment_student'),
    )
    op.create_index('ix_teaching_submission_assignment_id', 'teaching_submission', ['assignment_id'])
    op.create_index('ix_teaching_submission_student_id', 'teaching_submission', ['student_id'])

    op.create_table(
        'teaching_effort_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(length=40), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('visible_to_teacher', sa.Boolean(), nullable=False),
        sa.Column('logged_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('minutes > 0 AND minutes <= 1440', name='ck_teaching_effort_minutes'),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_effort_log_user_id', 'teaching_effort_log', ['user_id'])
    op.create_index('ix_teaching_effort_log_class_id', 'teaching_effort_log', ['class_id'])
    op.create_index('ix_teaching_effort_log_logged_at', 'teaching_effort_log', ['logged_at'])


def downgrade():
    op.drop_index('ix_teaching_effort_log_logged_at', table_name='teaching_effort_log')
    op.drop_index('ix_teaching_effort_log_class_id', table_name='teaching_effort_log')
    op.drop_index('ix_teaching_effort_log_user_id', table_name='teaching_effort_log')
    op.drop_table('teaching_effort_log')

    op.drop_index('ix_teaching_submission_student_id', table_name='teaching_submission')
    op.drop_index('ix_teaching_submission_assignment_id', table_name='teaching_submission')
    op.drop_table('teaching_submission')

    op.drop_index('ix_teaching_assignment_due_at', table_name='teaching_assignment')
    op.drop_index('ix_teaching_assignment_class_id', table_name='teaching_assignment')
    op.drop_table('teaching_assignment')

    op.drop_index('ix_teaching_material_class_id', table_name='teaching_material')
    op.drop_table('teaching_material')

    op.drop_index('ix_teaching_session_starts_at', table_name='teaching_session')
    op.drop_index('ix_teaching_session_class_id', table_name='teaching_session')
    op.drop_table('teaching_session')

    op.drop_index('ix_teaching_enrollment_student_id', table_name='teaching_enrollment')
    op.drop_index('ix_teaching_enrollment_class_id', table_name='teaching_enrollment')
    op.drop_table('teaching_enrollment')

    op.drop_index('ix_teaching_class_invite_code', table_name='teaching_class')
    op.drop_index('ix_teaching_class_teacher_id', table_name='teaching_class')
    op.drop_table('teaching_class')
