"""add content and author to news_article

Revision ID: a3f7c8d91e2b
Revises: 8f17a9a63f7b
Create Date: 2026-05-27 17:16:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f7c8d91e2b'
down_revision = '8f17a9a63f7b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('news_article', sa.Column('content', sa.Text(), nullable=True))
    op.add_column('news_article', sa.Column('author', sa.String(length=300), nullable=True))


def downgrade():
    op.drop_column('news_article', 'author')
    op.drop_column('news_article', 'content')
