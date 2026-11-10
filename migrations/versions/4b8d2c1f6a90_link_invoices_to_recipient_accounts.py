"""Link invoices to matching recipient accounts.

Revision ID: 4b8d2c1f6a90
Revises: 3a1f7d9c2e60
Create Date: 2026-11-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '4b8d2c1f6a90'
down_revision = '3a1f7d9c2e60'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    invoice_columns = {column['name'] for column in inspector.get_columns('invoice')}
    foreign_keys = inspector.get_foreign_keys('invoice')
    indexes = {index['name'] for index in inspector.get_indexes('invoice')}

    with op.batch_alter_table('invoice', schema=None) as batch_op:
        if 'recipient_user_id' not in invoice_columns:
            batch_op.add_column(sa.Column('recipient_user_id', sa.Integer(), nullable=True))
        if not any(
            fk.get('constrained_columns') == ['recipient_user_id'] and fk.get('referred_table') == 'user'
            for fk in foreign_keys
        ):
            batch_op.create_foreign_key(
                'fk_invoice_recipient_user_id_user',
                'user',
                ['recipient_user_id'],
                ['id'],
            )
        if 'ix_invoice_recipient_user_id' not in indexes:
            batch_op.create_index('ix_invoice_recipient_user_id', ['recipient_user_id'], unique=False)

    invoice = sa.table(
        'invoice',
        sa.column('recipient_email', sa.String()),
        sa.column('recipient_user_id', sa.Integer()),
    )
    user = sa.table('user', sa.column('id', sa.Integer()), sa.column('email', sa.String()))
    matching_user_id = sa.select(user.c.id).where(
        sa.func.lower(sa.func.trim(user.c.email)) == sa.func.lower(sa.func.trim(invoice.c.recipient_email))
    ).limit(1).scalar_subquery()
    op.execute(
        invoice.update()
        .where(invoice.c.recipient_user_id.is_(None))
        .values(recipient_user_id=matching_user_id)
    )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('invoice')}
    if 'recipient_user_id' not in columns:
        return

    foreign_keys = inspector.get_foreign_keys('invoice')
    indexes = {index['name'] for index in inspector.get_indexes('invoice')}
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        if 'ix_invoice_recipient_user_id' in indexes:
            batch_op.drop_index('ix_invoice_recipient_user_id')
        for fk in foreign_keys:
            if fk.get('constrained_columns') == ['recipient_user_id'] and fk.get('name'):
                batch_op.drop_constraint(fk['name'], type_='foreignkey')
        batch_op.drop_column('recipient_user_id')
