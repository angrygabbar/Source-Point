from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    Base,
    BranchEntity,
    OptBranchEntity,
    TenantEntity,
    boolean,
    date,
    decimal,
    enum,
    fk,
    integer,
    jsonb,
    money,
    string,
    text,
    ts,
    uuid_col,
)

BILLING_TYPES = ("monthly", "quarterly", "annual", "per_subject", "per_course", "per_class", "one_time", "installment", "custom")
PAYMENT_METHODS = ("cash", "upi", "bank_transfer", "cheque", "card", "online_gateway")


class FeePlan(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "fee_plans"
    name = string(200, nullable=False)
    code = string(50, nullable=False)
    description = text()
    billing_type = enum(*BILLING_TYPES, default="monthly")
    course_id = fk("courses.id")
    subject_id = fk("subjects.id")
    amount = money()
    currency = string(3, nullable=False, default="INR")
    installments = integer(nullable=False, default=1)
    due_day = integer(nullable=False, default=10, label="Due day of month")
    late_fee_amount = money()
    late_fee_grace_days = integer(nullable=False, default=0)
    tax_applicable = boolean(False)
    is_active = boolean(True)
    __table_args__ = (
        UniqueConstraint("institute_id", "code"),
        CheckConstraint("amount >= 0", name="ck_fee_plans_amount"),
        CheckConstraint("installments >= 1", name="ck_fee_plans_installments"),
        CheckConstraint("due_day BETWEEN 1 AND 28", name="ck_fee_plans_due_day"),
    )


class FeePlanItem(TenantEntity, Base):
    __tablename__ = "fee_plan_items"
    fee_plan_id = fk("fee_plans.id", nullable=False, ondelete="CASCADE")
    name = string(200, nullable=False)
    item_type = enum("tuition", "admission", "exam", "material", "lab", "transport", "other", default="tuition")
    amount = money()
    frequency = enum("one_time", "monthly", "quarterly", "annual", "per_class", default="monthly")
    sequence = integer(nullable=False, default=1)
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_fee_plan_items_amount"),)


class StudentFeeAgreement(BranchEntity, ActorMixin, Base):
    __tablename__ = "student_fee_agreements"
    student_id = fk("students.id", nullable=False)
    fee_plan_id = fk("fee_plans.id")
    enrollment_id = fk("student_enrollments.id")
    batch_id = fk("batches.id")
    subject_id = fk("subjects.id")
    billing_type = enum(*BILLING_TYPES, default="monthly")
    amount = money(label="Agreed amount per period / class")
    currency = string(3, nullable=False, default="INR")
    discount_type = enum("none", "percent", "fixed", default="none")
    discount_value = money()
    scholarship_name = string(200)
    scholarship_amount = money()
    effective_from = date(nullable=False)
    effective_to = date()
    next_billing_date = date()
    status = enum("active", "suspended", "ended", default="active")
    notes = text()
    approved_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_agreements_dates"),
        CheckConstraint("amount >= 0 AND discount_value >= 0 AND scholarship_amount >= 0", name="ck_agreements_amounts"),
    )


INVOICE_STATUSES = ("draft", "issued", "partially_paid", "paid", "overdue", "cancelled")


class Invoice(BranchEntity, ActorMixin, Base):
    __tablename__ = "invoices"
    invoice_number = string(40)
    student_id = fk("students.id", nullable=False)
    agreement_id = fk("student_fee_agreements.id")
    issue_date = date(nullable=False)
    due_date = date(nullable=False)
    period_start = date()
    period_end = date()
    status = enum(*INVOICE_STATUSES, default="draft")
    source = enum("manual", "scheduled", "per_class", "admission", "supplementary", default="manual")
    currency = string(3, nullable=False, default="INR")
    subtotal = money()
    discount_total = money()
    tax_total = money()
    late_fee_total = money()
    total = money()
    amount_paid = money()
    credit_applied = money()
    balance_due = money()
    tax_registration_number = string(30)
    notes = text()
    posted_at = ts()
    cancelled_at = ts()
    cancellation_reason = text()
    supplementary_to_id = fk("invoices.id")
    __table_args__ = (
        Index(
            "uq_invoices_number",
            "institute_id",
            "invoice_number",
            unique=True,
            postgresql_where=sql_text("invoice_number IS NOT NULL"),
        ),
        Index(
            "uq_invoices_agreement_period",
            "agreement_id",
            "period_start",
            unique=True,
            postgresql_where=sql_text("agreement_id IS NOT NULL AND source = 'scheduled' AND status <> 'cancelled'"),
        ),
        CheckConstraint(
            "subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0 AND amount_paid >= 0 "
            "AND credit_applied >= 0 AND balance_due >= 0",
            name="ck_invoices_amounts",
        ),
        CheckConstraint("due_date >= issue_date", name="ck_invoices_dates"),
    )


class InvoiceItem(TenantEntity, Base):
    __tablename__ = "invoice_items"
    invoice_id = fk("invoices.id", nullable=False)
    description = string(500, nullable=False)
    item_type = enum("tuition", "admission", "exam", "material", "lab", "transport", "late_fee", "per_class", "other", default="tuition")
    subject_id = fk("subjects.id")
    session_id = fk("class_sessions.id")
    quantity = decimal(10, 2, nullable=False, default=1)
    unit_price = money()
    discount = money()
    tax_rate = decimal(5, 2, nullable=False, default=0)
    tax_amount = money()
    amount = money()
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price >= 0 AND discount >= 0 AND amount >= 0", name="ck_invoice_items_amounts"),)


class BillableCharge(BranchEntity, Base):
    """Per-class charges generated from completed sessions; reviewed before invoicing."""

    __tablename__ = "billable_charges"
    student_id = fk("students.id", nullable=False)
    session_id = fk("class_sessions.id", nullable=False)
    agreement_id = fk("student_fee_agreements.id", nullable=False)
    subject_id = fk("subjects.id")
    charge_date = date(nullable=False)
    amount = money()
    attendance_status = string(40)
    status = enum("pending_review", "approved", "invoiced", "waived", default="pending_review")
    invoice_item_id = fk("invoice_items.id")
    reviewed_by_id = fk("users.id", ondelete="SET NULL")
    reviewed_at = ts()
    review_note = text()
    __table_args__ = (UniqueConstraint("student_id", "session_id"), CheckConstraint("amount >= 0", name="ck_charges_amount"))


class Payment(BranchEntity, Base):
    __tablename__ = "payments"
    receipt_number = string(40, nullable=False)
    student_id = fk("students.id", nullable=False)
    amount = money()
    currency = string(3, nullable=False, default="INR")
    method = enum(*PAYMENT_METHODS, default="cash")
    status = enum("pending", "completed", "failed", "reversed", "bounced", default="completed")
    paid_at = ts(nullable=False)
    reference_number = string(120, label="UPI / bank / cheque reference")
    cheque_date = date()
    bank_name = string(120)
    gateway_order_id = string(120)
    gateway_payment_id = string(120)
    idempotency_key = string(120, nullable=False, hidden=True)
    unallocated_amount = money()
    notes = text()
    collected_by_id = fk("users.id", ondelete="SET NULL")
    reversed_at = ts()
    reversal_reason = text()
    reversed_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (
        UniqueConstraint("institute_id", "receipt_number"),
        UniqueConstraint("institute_id", "idempotency_key"),
        Index(
            "uq_payments_reference",
            "institute_id",
            "method",
            "reference_number",
            unique=True,
            postgresql_where=sql_text("reference_number IS NOT NULL AND method <> 'cash'"),
        ),
        Index("uq_payments_gateway", "gateway_payment_id", unique=True, postgresql_where=sql_text("gateway_payment_id IS NOT NULL")),
        CheckConstraint("amount > 0", name="ck_payments_amount"),
        CheckConstraint("unallocated_amount >= 0 AND unallocated_amount <= amount", name="ck_payments_unallocated"),
    )


class PaymentAllocation(TenantEntity, Base):
    __tablename__ = "payment_allocations"
    payment_id = fk("payments.id", nullable=False)
    invoice_id = fk("invoices.id", nullable=False)
    amount = money()
    is_reversed = boolean(False)
    reversed_at = ts()
    __table_args__ = (CheckConstraint("amount > 0", name="ck_allocations_amount"),)


class Refund(BranchEntity, ActorMixin, Base):
    __tablename__ = "refunds"
    refund_number = string(40)
    payment_id = fk("payments.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    amount = money()
    method = enum(*PAYMENT_METHODS, default="bank_transfer")
    reference_number = string(120)
    reason = text(nullable=False)
    status = enum("pending", "approved", "processed", "rejected", default="pending")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    approved_at = ts()
    processed_at = ts()
    __table_args__ = (CheckConstraint("amount > 0", name="ck_refunds_amount"),)


class CreditNote(BranchEntity, ActorMixin, Base):
    __tablename__ = "credit_notes"
    credit_note_number = string(40, nullable=False)
    invoice_id = fk("invoices.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    amount = money()
    reason = text(nullable=False)
    status = enum("issued", "void", default="issued")
    __table_args__ = (UniqueConstraint("institute_id", "credit_note_number"), CheckConstraint("amount > 0", name="ck_credit_notes_amount"))


class LedgerEntry(BranchEntity, Base):
    """Append-only financial ledger. Protected from UPDATE/DELETE by database triggers."""

    __tablename__ = "ledger_entries"
    student_id = fk("students.id")
    entry_date = date(nullable=False, index=True)
    entry_type = enum("invoice", "payment", "refund", "credit_note", "reversal", "adjustment", "expense", "payroll", "cancellation")
    reference_type = string(60, nullable=False)
    reference_id = uuid_col(nullable=False)
    debit = money()
    credit = money()
    currency = string(3, nullable=False, default="INR")
    description = string(500)
    created_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (CheckConstraint("debit >= 0 AND credit >= 0", name="ck_ledger_amounts"),)


class NumberSequence(TenantEntity, Base):
    __tablename__ = "number_sequences"
    key = string(60, nullable=False)
    next_value = integer(nullable=False, default=1)
    __table_args__ = (UniqueConstraint("institute_id", "key"),)


# ----------------------------------------------------------------------------- accounting


class Vendor(TenantEntity, ActorMixin, Base):
    __tablename__ = "vendors"
    name = string(200, nullable=False)
    contact_person = string(200)
    phone = string(30)
    email = string(255)
    address = text()
    tax_registration_number = string(30, label="GSTIN")
    payment_terms = string(200)
    is_active = boolean(True)


class ExpenseCategory(TenantEntity, Base):
    __tablename__ = "expense_categories"
    name = string(120, nullable=False)
    code = string(40, nullable=False)
    description = text()
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "code"),)


class Expense(BranchEntity, ActorMixin, Base):
    __tablename__ = "expenses"
    category_id = fk("expense_categories.id", nullable=False)
    vendor_id = fk("vendors.id")
    expense_date = date(nullable=False)
    description = string(500, nullable=False)
    amount = money()
    tax_amount = money()
    currency = string(3, nullable=False, default="INR")
    payment_method = enum(*PAYMENT_METHODS, default="cash")
    reference_number = string(120)
    is_petty_cash = boolean(False)
    status = enum("draft", "submitted", "approved", "rejected", "paid", "void", default="submitted")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    approved_at = ts()
    paid_at = ts()
    __table_args__ = (CheckConstraint("amount > 0 AND tax_amount >= 0", name="ck_expenses_amount"),)


class PurchaseRecord(BranchEntity, ActorMixin, Base):
    __tablename__ = "purchase_records"
    vendor_id = fk("vendors.id", nullable=False)
    purchase_date = date(nullable=False)
    po_number = string(60)
    description = text(nullable=False)
    amount = money()
    tax_amount = money()
    status = enum("requested", "approved", "rejected", "ordered", "received", "cancelled", default="requested")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    approved_at = ts()
    expense_id = fk("expenses.id")
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_purchases_amount"),)


class CashbookEntry(BranchEntity, ActorMixin, Base):
    __tablename__ = "cashbook_entries"
    entry_date = date(nullable=False, index=True)
    account = enum("cash", "petty_cash", "bank", default="cash")
    direction = enum("in", "out", default="in")
    amount = money()
    description = string(500, nullable=False)
    reference_type = string(60)
    reference_id = uuid_col()
    __table_args__ = (CheckConstraint("amount > 0", name="ck_cashbook_amount"),)


class BankTransaction(BranchEntity, ActorMixin, Base):
    __tablename__ = "bank_transactions"
    bank_account_name = string(120, nullable=False)
    txn_date = date(nullable=False)
    description = string(500)
    direction = enum("credit", "debit", default="credit")
    amount = money()
    reference_number = string(120)
    is_reconciled = boolean(False)
    matched_payment_id = fk("payments.id")
    matched_expense_id = fk("expenses.id")
    __table_args__ = (CheckConstraint("amount > 0", name="ck_bank_txn_amount"),)


class Budget(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "budgets"
    financial_year_id = fk("financial_years.id", nullable=False)
    category_id = fk("expense_categories.id")
    budget_type = enum("expense", "revenue", default="expense")
    amount = money()
    notes = text()


class FinancialYear(TenantEntity, ActorMixin, Base):
    __tablename__ = "financial_years"
    name = string(20, nullable=False)
    start_date = date(nullable=False)
    end_date = date(nullable=False)
    status = enum("open", "closed", default="open")
    closed_at = ts()
    closed_by_id = fk("users.id", ondelete="SET NULL")
    closing_summary = jsonb()
    __table_args__ = (UniqueConstraint("institute_id", "name"), CheckConstraint("end_date > start_date", name="ck_fy_dates"))


class TaxRate(TenantEntity, Base):
    __tablename__ = "tax_rates"
    name = string(60, nullable=False)
    rate = decimal(5, 2, nullable=False, default=0)
    hsn_sac_code = string(20)
    is_default = boolean(False)
    is_active = boolean(True)


# ----------------------------------------------------------------------------- payroll


class CompensationRule(TenantEntity, ActorMixin, Base):
    __tablename__ = "compensation_rules"
    teacher_id = fk("teachers.id", nullable=False)
    compensation_type = enum("fixed_monthly", "per_class", "per_hour", "custom", default="fixed_monthly")
    amount = money()
    subject_id = fk("subjects.id")
    batch_id = fk("batches.id")
    effective_from = date(nullable=False)
    effective_to = date()
    notes = text()
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_comp_rules_dates"),
        CheckConstraint("amount >= 0", name="ck_comp_rules_amount"),
    )


class PayrollPeriod(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "payroll_periods"
    name = string(60, nullable=False)
    start_date = date(nullable=False)
    end_date = date(nullable=False)
    status = enum("open", "processing", "approved", "paid", "closed", default="open")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    approved_at = ts()
    __table_args__ = (UniqueConstraint("institute_id", "name"), CheckConstraint("end_date >= start_date", name="ck_payroll_dates"))


class TeacherPayableEntry(TenantEntity, ActorMixin, Base):
    __tablename__ = "teacher_payable_entries"
    teacher_id = fk("teachers.id", nullable=False)
    payroll_period_id = fk("payroll_periods.id")
    session_id = fk("class_sessions.id")
    rule_id = fk("compensation_rules.id")
    entry_type = enum("salary", "per_class", "per_hour", "bonus", "allowance", "adjustment", "deduction", default="salary")
    entry_date = date(nullable=False)
    description = string(500, nullable=False)
    quantity = decimal(10, 2, nullable=False, default=1)
    rate = money()
    amount = money(label="Amount (deductions are subtracted)")
    status = enum("pending", "approved", "rejected", "paid", default="pending")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (
        Index(
            "uq_payable_session",
            "teacher_id",
            "session_id",
            unique=True,
            postgresql_where=sql_text("session_id IS NOT NULL AND status <> 'rejected'"),
        ),
        CheckConstraint("amount >= 0", name="ck_payable_amount"),
    )


class Payslip(TenantEntity, ActorMixin, Base):
    __tablename__ = "payslips"
    payslip_number = string(40, nullable=False)
    payroll_period_id = fk("payroll_periods.id", nullable=False)
    teacher_id = fk("teachers.id", nullable=False)
    gross_amount = money()
    deductions = money()
    net_amount = money()
    status = enum("draft", "approved", "paid", "void", default="draft")
    details = jsonb()
    approved_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (UniqueConstraint("payroll_period_id", "teacher_id"), UniqueConstraint("institute_id", "payslip_number"))


class TeacherPayout(TenantEntity, ActorMixin, Base):
    __tablename__ = "teacher_payouts"
    teacher_id = fk("teachers.id", nullable=False)
    payslip_id = fk("payslips.id")
    amount = money()
    method = enum(*PAYMENT_METHODS, default="bank_transfer")
    reference_number = string(120)
    paid_at = ts(nullable=False)
    status = enum("paid", "failed", "reversed", default="paid")
    notes = text()
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payouts_amount"),)
