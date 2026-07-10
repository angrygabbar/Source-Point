from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime

from sqlalchemy import inspect

from extensions import db
from enums import UserRole, SupersCoinTransactionType, SupersCoinInvoiceStatus
from models.auth import User
from models.commerce import SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice


COIN_QUANT = Decimal("0.01")
REQUIRED_SUPERSCOIN_TABLES = {
    SupersCoinWallet.__tablename__,
    SupersCoinTransaction.__tablename__,
    SupersCoinInvoice.__tablename__,
}


class SupersCoinsService:
    @staticmethod
    def tables_ready():
        try:
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())
            return REQUIRED_SUPERSCOIN_TABLES.issubset(existing_tables)
        except Exception as e:
            print(f"SupersCoins table readiness check failed: {e}")
            return False

    @staticmethod
    def parse_amount(value):
        try:
            amount = Decimal(str(value)).quantize(COIN_QUANT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            return None
        if amount <= 0:
            return None
        return amount

    @staticmethod
    def seller_query():
        return User.query.filter_by(role=UserRole.SELLER.value)

    @staticmethod
    def get_seller(seller_id):
        return SupersCoinsService.seller_query().filter_by(id=seller_id).first()

    @staticmethod
    def get_or_create_wallet(seller):
        wallet = SupersCoinWallet.query.filter_by(seller_id=seller.id).first()
        if wallet:
            return wallet

        wallet = SupersCoinWallet(seller_id=seller.id, balance=Decimal("0.00"))
        db.session.add(wallet)
        db.session.flush()
        return wallet

    @staticmethod
    def wallet_balance(wallet):
        if not wallet or wallet.balance is None:
            return Decimal("0.00")
        return Decimal(str(wallet.balance)).quantize(COIN_QUANT, rounding=ROUND_HALF_UP)

    @staticmethod
    def adjust_wallet(seller_id, transaction_type, amount_value, admin_id, note=None, reference_type=None, reference_id=None):
        if not SupersCoinsService.tables_ready():
            return False, "SupersCoins database tables are not installed. Please run the database migration.", None, None

        seller = SupersCoinsService.get_seller(seller_id)
        if not seller:
            return False, "Selected seller was not found.", None, None

        amount = SupersCoinsService.parse_amount(amount_value)
        if amount is None:
            return False, "Enter a valid coin amount greater than zero.", None, None

        if transaction_type not in {
            SupersCoinTransactionType.CREDIT.value,
            SupersCoinTransactionType.DEBIT.value,
        }:
            return False, "Invalid SupersCoins transaction type.", None, None

        wallet = SupersCoinsService.get_or_create_wallet(seller)
        before = SupersCoinsService.wallet_balance(wallet)

        if transaction_type == SupersCoinTransactionType.DEBIT.value:
            if before < amount:
                return False, "Seller does not have enough SupersCoins for this deduction.", wallet, None
            after = before - amount
        else:
            after = before + amount

        wallet.balance = after
        wallet.updated_at = datetime.utcnow()

        transaction = SupersCoinTransaction(
            wallet_id=wallet.id,
            seller_id=seller.id,
            admin_id=admin_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=before,
            balance_after=after,
            note=note,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        db.session.add(transaction)
        db.session.flush()

        verb = "credited to" if transaction_type == SupersCoinTransactionType.CREDIT.value else "deducted from"
        return True, f"{amount:,.2f} SupersCoins {verb} {seller.username}.", wallet, transaction

    @staticmethod
    def next_invoice_number(seller_id):
        return f"SCINV-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{seller_id}"

    @staticmethod
    def create_invoice(seller_id, amount_value, admin_id, description=None, notes=None, due_date=None, transaction_id=None, spending_category=None, booking_details=None):
        if not SupersCoinsService.tables_ready():
            return False, "SupersCoins database tables are not installed. Please run the database migration.", None

        seller = SupersCoinsService.get_seller(seller_id)
        if not seller:
            return False, "Selected seller was not found.", None

        amount = SupersCoinsService.parse_amount(amount_value)
        if amount is None:
            return False, "Enter a valid invoice coin amount greater than zero.", None

        invoice = SupersCoinInvoice(
            invoice_number=SupersCoinsService.next_invoice_number(seller.id),
            seller_id=seller.id,
            admin_id=admin_id,
            transaction_id=transaction_id,
            amount=amount,
            status=SupersCoinInvoiceStatus.UNPAID.value,
            description=(description or "SupersCoins allocation").strip(),
            notes=(notes or "").strip() or None,
            due_date=due_date,
            spending_category=(spending_category or "").strip() or None,
            booking_details=(booking_details or "").strip() or None,
        )
        db.session.add(invoice)
        db.session.flush()
        return True, f"SupersCoins invoice {invoice.invoice_number} created.", invoice
