"""merge conflicting migrations

Revision ID: ef6c314d5ce2
Revises: b7e9752b169b, create_interview_tables
Create Date: 2026-01-29 18:24:13.742645

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef6c314d5ce2'
down_revision = ('b7e9752b169b', 'create_interview_tables')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
