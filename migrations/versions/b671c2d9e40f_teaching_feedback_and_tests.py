"""add session feedback and assigned teaching tests

Revision ID: b671c2d9e40f
Revises: e4c19a7f2b6d
Create Date: 2026-10-19

"""
from alembic import op
import sqlalchemy as sa


revision = 'b671c2d9e40f'
down_revision = 'e4c19a7f2b6d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teaching_session_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_teaching_session_feedback_rating'),
        sa.ForeignKeyConstraint(['session_id'], ['teaching_session.id']),
        sa.ForeignKeyConstraint(['student_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'session_id', 'student_id', name='uq_teaching_session_feedback_student'
        ),
    )
    op.create_index(
        'ix_teaching_session_feedback_session_id',
        'teaching_session_feedback', ['session_id']
    )
    op.create_index(
        'ix_teaching_session_feedback_student_id',
        'teaching_session_feedback', ['student_id']
    )

    op.create_table(
        'teaching_test',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('question_type', sa.String(length=20), nullable=False),
        sa.Column('opens_at', sa.DateTime(), nullable=True),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "question_type IN ('mcq', 'short_answer')",
            name='ck_teaching_test_question_type',
        ),
        sa.ForeignKeyConstraint(['class_id'], ['teaching_class.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teaching_test_class_id', 'teaching_test', ['class_id'])

    op.create_table(
        'teaching_test_question',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('choices', sa.JSON(), nullable=True),
        sa.Column('correct_option', sa.String(length=1), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['test_id'], ['teaching_test.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_teaching_test_question_test_id', 'teaching_test_question', ['test_id']
    )

    op.create_table(
        'teaching_test_assignment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['user.id']),
        sa.ForeignKeyConstraint(['test_id'], ['teaching_test.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'test_id', 'student_id', name='uq_teaching_test_assignment_student'
        ),
    )
    op.create_index(
        'ix_teaching_test_assignment_test_id', 'teaching_test_assignment', ['test_id']
    )
    op.create_index(
        'ix_teaching_test_assignment_student_id', 'teaching_test_assignment', ['student_id']
    )

    op.create_table(
        'teaching_test_submission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('score', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('graded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['teaching_test_assignment.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_teaching_test_submission_assignment_id',
        'teaching_test_submission', ['assignment_id'], unique=True
    )

    op.create_table(
        'teaching_test_answer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['teaching_test_question.id']),
        sa.ForeignKeyConstraint(['submission_id'], ['teaching_test_submission.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'submission_id', 'question_id', name='uq_teaching_test_answer_question'
        ),
    )
    op.create_index(
        'ix_teaching_test_answer_submission_id', 'teaching_test_answer', ['submission_id']
    )
    op.create_index(
        'ix_teaching_test_answer_question_id', 'teaching_test_answer', ['question_id']
    )


def downgrade():
    op.drop_index('ix_teaching_test_answer_question_id', table_name='teaching_test_answer')
    op.drop_index('ix_teaching_test_answer_submission_id', table_name='teaching_test_answer')
    op.drop_table('teaching_test_answer')
    op.drop_index('ix_teaching_test_submission_assignment_id', table_name='teaching_test_submission')
    op.drop_table('teaching_test_submission')
    op.drop_index('ix_teaching_test_assignment_student_id', table_name='teaching_test_assignment')
    op.drop_index('ix_teaching_test_assignment_test_id', table_name='teaching_test_assignment')
    op.drop_table('teaching_test_assignment')
    op.drop_index('ix_teaching_test_question_test_id', table_name='teaching_test_question')
    op.drop_table('teaching_test_question')
    op.drop_index('ix_teaching_test_class_id', table_name='teaching_test')
    op.drop_table('teaching_test')
    op.drop_index('ix_teaching_session_feedback_student_id', table_name='teaching_session_feedback')
    op.drop_index('ix_teaching_session_feedback_session_id', table_name='teaching_session_feedback')
    op.drop_table('teaching_session_feedback')
