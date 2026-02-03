"""Merge conflicting migrations

Revision ID: 24a4be2f84cd
Revises: 5ef55d936ae2, da6f1175bde9
Create Date: 2026-02-03 05:26:28.325769

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '24a4be2f84cd'
down_revision = ('5ef55d936ae2', 'da6f1175bde9')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
