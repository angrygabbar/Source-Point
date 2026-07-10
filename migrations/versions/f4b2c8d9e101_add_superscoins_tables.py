"""add superscoins tables

Revision ID: f4b2c8d9e101
Revises: a3f7c8d91e2b
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f4b2c8d9e101'
down_revision = 'a3f7c8d91e2b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'supers_coin_wallet',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['seller_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seller_id'),
    )
    op.create_index(op.f('ix_supers_coin_wallet_seller_id'), 'supers_coin_wallet', ['seller_id'], unique=False)

    op.create_table(
        'supers_coin_transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wallet_id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('balance_before', sa.Numeric(12, 2), nullable=False),
        sa.Column('balance_after', sa.Numeric(12, 2), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('reference_type', sa.String(length=40), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['user.id']),
        sa.ForeignKeyConstraint(['seller_id'], ['user.id']),
        sa.ForeignKeyConstraint(['wallet_id'], ['supers_coin_wallet.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supers_coin_transaction_admin_id'), 'supers_coin_transaction', ['admin_id'], unique=False)
    op.create_index(op.f('ix_supers_coin_transaction_created_at'), 'supers_coin_transaction', ['created_at'], unique=False)
    op.create_index(op.f('ix_supers_coin_transaction_seller_id'), 'supers_coin_transaction', ['seller_id'], unique=False)
    op.create_index(op.f('ix_supers_coin_transaction_transaction_type'), 'supers_coin_transaction', ['transaction_type'], unique=False)
    op.create_index(op.f('ix_supers_coin_transaction_wallet_id'), 'supers_coin_transaction', ['wallet_id'], unique=False)

    op.create_table(
        'supers_coin_invoice',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=60), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['user.id']),
        sa.ForeignKeyConstraint(['seller_id'], ['user.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['supers_coin_transaction.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
    )
    op.create_index(op.f('ix_supers_coin_invoice_admin_id'), 'supers_coin_invoice', ['admin_id'], unique=False)
    op.create_index(op.f('ix_supers_coin_invoice_created_at'), 'supers_coin_invoice', ['created_at'], unique=False)
    op.create_index(op.f('ix_supers_coin_invoice_invoice_number'), 'supers_coin_invoice', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_supers_coin_invoice_seller_id'), 'supers_coin_invoice', ['seller_id'], unique=False)
    op.create_index(op.f('ix_supers_coin_invoice_status'), 'supers_coin_invoice', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_supers_coin_invoice_status'), table_name='supers_coin_invoice')
    op.drop_index(op.f('ix_supers_coin_invoice_seller_id'), table_name='supers_coin_invoice')
    op.drop_index(op.f('ix_supers_coin_invoice_invoice_number'), table_name='supers_coin_invoice')
    op.drop_index(op.f('ix_supers_coin_invoice_created_at'), table_name='supers_coin_invoice')
    op.drop_index(op.f('ix_supers_coin_invoice_admin_id'), table_name='supers_coin_invoice')
    op.drop_table('supers_coin_invoice')

    op.drop_index(op.f('ix_supers_coin_transaction_wallet_id'), table_name='supers_coin_transaction')
    op.drop_index(op.f('ix_supers_coin_transaction_transaction_type'), table_name='supers_coin_transaction')
    op.drop_index(op.f('ix_supers_coin_transaction_seller_id'), table_name='supers_coin_transaction')
    op.drop_index(op.f('ix_supers_coin_transaction_created_at'), table_name='supers_coin_transaction')
    op.drop_index(op.f('ix_supers_coin_transaction_admin_id'), table_name='supers_coin_transaction')
    op.drop_table('supers_coin_transaction')

    op.drop_index(op.f('ix_supers_coin_wallet_seller_id'), table_name='supers_coin_wallet')
    op.drop_table('supers_coin_wallet')
