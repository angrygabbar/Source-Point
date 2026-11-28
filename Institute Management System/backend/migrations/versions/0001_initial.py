"""Initial ClassFlow ERP schema (baseline) with integrity triggers.

The baseline materialises the full SQLAlchemy metadata at this revision. All later schema
changes must be added as new revisions (`alembic revision --autogenerate -m "..."`).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-27
"""
from alembic import op

from app.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

IMMUTABLE_TABLES = ("ledger_entries", "audit_logs")
NO_DELETE_TABLES = ("payments", "payment_allocations", "refunds", "credit_notes", "class_sessions", "student_attendance",
                    "teacher_attendance", "teacher_payouts", "payslips", "material_versions", "submission_versions", "exam_results")

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION cf_block_change() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Records in % are append-only (% blocked)', TG_TABLE_NAME, TG_OP USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cf_block_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Records in % cannot be deleted; use reversal, cancellation or archival', TG_TABLE_NAME USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cf_invoice_guard() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'draft' THEN
      RAISE EXCEPTION 'Posted invoices cannot be deleted' USING ERRCODE = 'check_violation';
    END IF;
    RETURN OLD;
  END IF;
  IF OLD.status <> 'draft' AND (
       NEW.student_id IS DISTINCT FROM OLD.student_id OR NEW.invoice_number IS DISTINCT FROM OLD.invoice_number
    OR NEW.subtotal IS DISTINCT FROM OLD.subtotal OR NEW.discount_total IS DISTINCT FROM OLD.discount_total
    OR NEW.tax_total IS DISTINCT FROM OLD.tax_total OR NEW.total IS DISTINCT FROM OLD.total
    OR NEW.issue_date IS DISTINCT FROM OLD.issue_date OR NEW.currency IS DISTINCT FROM OLD.currency) THEN
    RAISE EXCEPTION 'Posted invoice amounts are immutable; use credit notes or supplementary invoices' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cf_invoice_item_guard() RETURNS trigger AS $$
DECLARE st text;
BEGIN
  SELECT status INTO st FROM invoices WHERE id = COALESCE(OLD.invoice_id, NEW.invoice_id);
  IF st IS NOT NULL AND st <> 'draft' THEN
    RAISE EXCEPTION 'Items of posted invoices are immutable' USING ERRCODE = 'check_violation';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cf_payment_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.amount IS DISTINCT FROM OLD.amount OR NEW.student_id IS DISTINCT FROM OLD.student_id
     OR NEW.receipt_number IS DISTINCT FROM OLD.receipt_number OR NEW.paid_at IS DISTINCT FROM OLD.paid_at
     OR NEW.method IS DISTINCT FROM OLD.method THEN
    RAISE EXCEPTION 'Posted payments are immutable; reverse them instead' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)
    op.execute(TRIGGER_SQL)
    for t in IMMUTABLE_TABLES:
        op.execute(f"CREATE TRIGGER trg_{t}_immutable BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION cf_block_change()")
    for t in NO_DELETE_TABLES:
        op.execute(f"CREATE TRIGGER trg_{t}_nodelete BEFORE DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION cf_block_delete()")
    op.execute("CREATE TRIGGER trg_invoices_guard BEFORE UPDATE OR DELETE ON invoices FOR EACH ROW EXECUTE FUNCTION cf_invoice_guard()")
    op.execute("CREATE TRIGGER trg_invoice_items_guard BEFORE UPDATE OR DELETE ON invoice_items FOR EACH ROW EXECUTE FUNCTION cf_invoice_item_guard()")
    op.execute("CREATE TRIGGER trg_payments_guard BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION cf_payment_guard()")


def downgrade() -> None:
    for t in IMMUTABLE_TABLES + NO_DELETE_TABLES + ("invoices", "invoice_items", "payments"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{t}_immutable ON {t}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{t}_nodelete ON {t}")
    op.execute("DROP TRIGGER IF EXISTS trg_invoices_guard ON invoices")
    op.execute("DROP TRIGGER IF EXISTS trg_invoice_items_guard ON invoice_items")
    op.execute("DROP TRIGGER IF EXISTS trg_payments_guard ON payments")
    Base.metadata.drop_all(bind=op.get_bind())
    op.execute("DROP FUNCTION IF EXISTS cf_block_change, cf_block_delete, cf_invoice_guard, cf_invoice_item_guard, cf_payment_guard")
