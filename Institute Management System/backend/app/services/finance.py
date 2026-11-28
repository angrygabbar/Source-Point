"""Financial domain logic. All functions run inside the caller's DB transaction and never commit."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import (
    BillableCharge,
    ClassSession,
    CreditNote,
    FeePlan,
    FinancialYear,
    Institute,
    Invoice,
    InvoiceItem,
    LedgerEntry,
    Payment,
    PaymentAllocation,
    Refund,
    Student,
    StudentAttendance,
    StudentFeeAgreement,
)
from app.services import numbering, outbox

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
BILLABLE_ATTENDANCE = ("present", "late")


def q2(v) -> Decimal:
    return Decimal(v or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def ensure_period_open(db: Session, institute_id: uuid.UUID, d: date | None) -> None:
    if d is None:
        return
    closed = db.scalar(
        select(FinancialYear.id).where(
            FinancialYear.institute_id == institute_id,
            FinancialYear.status == "closed",
            FinancialYear.start_date <= d,
            FinancialYear.end_date >= d,
        )
    )
    if closed:
        raise Conflict("The financial year for this date is closed; post an adjustment in the current period instead")


def ledger(
    db: Session,
    inv_or_branch,
    student_id: uuid.UUID | None,
    entry_type: str,
    ref_type: str,
    ref_id: uuid.UUID,
    debit: Decimal = ZERO,
    credit: Decimal = ZERO,
    description: str = "",
    actor_id: uuid.UUID | None = None,
    entry_date: date | None = None,
    institute_id: uuid.UUID | None = None,
    currency: str = "INR",
) -> None:
    db.add(
        LedgerEntry(
            institute_id=institute_id or inv_or_branch.institute_id,
            branch_id=inv_or_branch.branch_id,
            student_id=student_id,
            entry_date=entry_date or date.today(),
            entry_type=entry_type,
            reference_type=ref_type,
            reference_id=ref_id,
            debit=q2(debit),
            credit=q2(credit),
            currency=currency,
            description=description[:500],
            created_by_id=actor_id,
        )
    )


# ----------------------------------------------------------------------------- invoices


def recalc_totals(db: Session, inv: Invoice) -> None:
    items = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).all()
    subtotal = sum((q2(i.quantity * i.unit_price) for i in items), ZERO)
    discount = sum((q2(i.discount) for i in items), ZERO)
    tax = sum((q2(i.tax_amount) for i in items), ZERO)
    inv.subtotal = q2(subtotal)
    inv.discount_total = q2(discount)
    inv.tax_total = q2(tax)
    inv.total = q2(subtotal - discount + tax)
    refresh_status(inv)


def refresh_status(inv: Invoice, today: date | None = None) -> None:
    if inv.status in ("draft", "cancelled"):
        inv.balance_due = max(q2(inv.total - inv.amount_paid - inv.credit_applied), ZERO)
        return
    balance = q2(inv.total - inv.amount_paid - inv.credit_applied)
    inv.balance_due = max(balance, ZERO)
    today = today or date.today()
    if inv.balance_due == ZERO:
        inv.status = "paid"
    elif inv.due_date < today:
        inv.status = "overdue"
    elif inv.amount_paid > ZERO or inv.credit_applied > ZERO:
        inv.status = "partially_paid"
    else:
        inv.status = "issued"


def build_item(description: str, unit_price: Decimal, quantity: Decimal = Decimal("1"), discount: Decimal = ZERO,
               tax_rate: Decimal = ZERO, item_type: str = "tuition", subject_id=None, session_id=None) -> InvoiceItem:
    gross = q2(Decimal(quantity) * Decimal(unit_price))
    discount = min(q2(discount), gross)
    taxable = gross - discount
    tax_amount = q2(taxable * Decimal(tax_rate) / Decimal(100))
    return InvoiceItem(
        description=description[:500],
        item_type=item_type,
        quantity=Decimal(quantity),
        unit_price=q2(unit_price),
        discount=discount,
        tax_rate=Decimal(tax_rate),
        tax_amount=tax_amount,
        amount=q2(taxable + tax_amount),
        subject_id=subject_id,
        session_id=session_id,
    )


def create_invoice(
    db: Session,
    institute_id: uuid.UUID,
    student: Student,
    items: list[InvoiceItem],
    issue_date: date,
    due_date: date,
    actor_id: uuid.UUID | None,
    source: str = "manual",
    agreement_id: uuid.UUID | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    notes: str | None = None,
    post: bool = True,
    supplementary_to_id: uuid.UUID | None = None,
) -> Invoice:
    if not items:
        raise ValidationFailed("An invoice requires at least one line item")
    if due_date < issue_date:
        raise ValidationFailed("Due date cannot be before issue date")
    ensure_period_open(db, institute_id, issue_date)
    inst = db.get(Institute, institute_id)
    inv = Invoice(
        institute_id=institute_id,
        branch_id=student.branch_id,
        student_id=student.id,
        agreement_id=agreement_id,
        issue_date=issue_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        source=source,
        currency=inst.currency if inst else "INR",
        tax_registration_number=inst.tax_registration_number if inst and inst.tax_enabled else None,
        notes=notes,
        created_by_id=actor_id,
        updated_by_id=actor_id,
        supplementary_to_id=supplementary_to_id,
    )
    db.add(inv)
    db.flush()
    for it in items:
        it.institute_id = institute_id
        it.invoice_id = inv.id
        db.add(it)
    db.flush()
    recalc_totals(db, inv)
    if post:
        post_invoice(db, inv, actor_id)
    return inv


def post_invoice(db: Session, inv: Invoice, actor_id: uuid.UUID | None) -> None:
    if inv.status != "draft":
        raise Conflict("Only draft invoices can be issued")
    ensure_period_open(db, inv.institute_id, inv.issue_date)
    inst = db.get(Institute, inv.institute_id)
    inv.invoice_number = numbering.next_number(db, inv.institute_id, "invoice", inst.invoice_prefix if inst else "INV", inv.issue_date)
    inv.status = "issued"
    inv.posted_at = datetime.now(timezone.utc)
    recalc_totals(db, inv)
    ledger(db, inv, inv.student_id, "invoice", "invoice", inv.id, debit=inv.total,
           description=f"Invoice {inv.invoice_number}", actor_id=actor_id, entry_date=inv.issue_date, currency=inv.currency)
    apply_advance_credit(db, inv, actor_id)
    outbox.emit(db, inv.institute_id, "invoice.issued", "invoice", inv.id, {"student_id": inv.student_id, "total": inv.total},
                dedupe_key=f"invoice.issued:{inv.id}")


def cancel_invoice(db: Session, inv: Invoice, reason: str, actor_id: uuid.UUID | None) -> None:
    if inv.status == "cancelled":
        raise Conflict("Invoice is already cancelled")
    if inv.amount_paid > ZERO or inv.credit_applied > ZERO:
        raise Conflict("Invoices with payments or credit notes cannot be cancelled; reverse the payments or issue a credit note")
    was_posted = inv.status != "draft"
    inv.status = "cancelled"
    inv.cancelled_at = datetime.now(timezone.utc)
    inv.cancellation_reason = reason
    inv.balance_due = ZERO
    if was_posted:
        ledger(db, inv, inv.student_id, "cancellation", "invoice", inv.id, credit=inv.total,
               description=f"Cancellation of {inv.invoice_number}: {reason}", actor_id=actor_id, currency=inv.currency)
    db.execute(
        BillableCharge.__table__.update()
        .where(BillableCharge.invoice_item_id.in_(select(InvoiceItem.id).where(InvoiceItem.invoice_id == inv.id)))
        .values(status="approved", invoice_item_id=None)
    )


# ----------------------------------------------------------------------------- payments


def _allocate(db: Session, payment: Payment, inv: Invoice, amount: Decimal) -> Decimal:
    amount = min(q2(amount), inv.balance_due, payment.unallocated_amount)
    if amount <= ZERO:
        return ZERO
    db.add(PaymentAllocation(institute_id=payment.institute_id, payment_id=payment.id, invoice_id=inv.id, amount=amount))
    inv.amount_paid = q2(inv.amount_paid + amount)
    payment.unallocated_amount = q2(payment.unallocated_amount - amount)
    refresh_status(inv)
    return amount


def open_invoices(db: Session, student_id: uuid.UUID, lock: bool = True) -> list[Invoice]:
    q = (
        select(Invoice)
        .where(Invoice.student_id == student_id, Invoice.status.in_(("issued", "partially_paid", "overdue")), Invoice.balance_due > 0)
        .order_by(Invoice.due_date, Invoice.issue_date, Invoice.created_at)
    )
    if lock:
        q = q.with_for_update()
    return list(db.scalars(q).all())


def record_payment(
    db: Session,
    institute_id: uuid.UUID,
    student: Student,
    amount: Decimal,
    method: str,
    paid_at: datetime,
    idempotency_key: str,
    actor_id: uuid.UUID | None,
    reference_number: str | None = None,
    allocations: list[tuple[uuid.UUID, Decimal]] | None = None,
    notes: str | None = None,
    cheque_date: date | None = None,
    bank_name: str | None = None,
    gateway_order_id: str | None = None,
    gateway_payment_id: str | None = None,
) -> tuple[Payment, bool]:
    """Returns (payment, created). Replays with the same idempotency key return the original payment."""
    existing = db.scalar(select(Payment).where(Payment.institute_id == institute_id, Payment.idempotency_key == idempotency_key))
    if existing:
        if existing.student_id != student.id or q2(existing.amount) != q2(amount):
            raise Conflict("Idempotency key was already used for a different payment")
        return existing, False
    amount = q2(amount)
    if amount <= ZERO:
        raise ValidationFailed("Payment amount must be positive")
    if method != "cash" and method != "online_gateway" and not reference_number:
        raise ValidationFailed("A transaction / cheque reference is required for non-cash payments")
    if reference_number and method != "cash":
        dup = db.scalar(
            select(Payment.id).where(
                Payment.institute_id == institute_id, Payment.method == method, Payment.reference_number == reference_number
            )
        )
        if dup:
            raise Conflict("A payment with this reference number has already been recorded")
    ensure_period_open(db, institute_id, paid_at.date())
    inst = db.get(Institute, institute_id)
    pay = Payment(
        institute_id=institute_id,
        branch_id=student.branch_id,
        receipt_number=numbering.next_number(db, institute_id, "receipt", inst.receipt_prefix if inst else "RCT", paid_at.date()),
        student_id=student.id,
        amount=amount,
        currency=inst.currency if inst else "INR",
        method=method,
        status="completed",
        paid_at=paid_at,
        reference_number=reference_number,
        cheque_date=cheque_date,
        bank_name=bank_name,
        gateway_order_id=gateway_order_id,
        gateway_payment_id=gateway_payment_id,
        idempotency_key=idempotency_key,
        unallocated_amount=amount,
        notes=notes,
        collected_by_id=actor_id,
    )
    db.add(pay)
    db.flush()
    invoices = open_invoices(db, student.id)
    by_id = {i.id: i for i in invoices}
    if allocations:
        total_req = sum((q2(a) for _, a in allocations), ZERO)
        if total_req > amount:
            raise ValidationFailed("Allocations exceed the payment amount")
        for inv_id, alloc in allocations:
            inv = by_id.get(inv_id)
            if inv is None:
                raise ValidationFailed("Allocation targets an invoice that is not open for this student")
            if q2(alloc) > inv.balance_due:
                raise ValidationFailed(f"Allocation exceeds balance of invoice {inv.invoice_number}")
            _allocate(db, pay, inv, q2(alloc))
    else:
        for inv in invoices:
            if pay.unallocated_amount <= ZERO:
                break
            _allocate(db, pay, inv, inv.balance_due)
    ledger(db, pay, student.id, "payment", "payment", pay.id, credit=amount,
           description=f"Payment {pay.receipt_number} ({method})", actor_id=actor_id, entry_date=paid_at.date(), currency=pay.currency)
    outbox.emit(db, institute_id, "payment.received", "payment", pay.id,
                {"student_id": student.id, "amount": amount, "receipt_number": pay.receipt_number},
                dedupe_key=f"payment.received:{pay.id}")
    return pay, True


def apply_advance_credit(db: Session, inv: Invoice, actor_id: uuid.UUID | None) -> None:
    """Allocate any unallocated (advance) payments of the student to a newly issued invoice."""
    payments = db.scalars(
        select(Payment)
        .where(Payment.student_id == inv.student_id, Payment.status == "completed", Payment.unallocated_amount > 0)
        .order_by(Payment.paid_at)
        .with_for_update()
    ).all()
    for pay in payments:
        if inv.balance_due <= ZERO:
            break
        _allocate(db, pay, inv, inv.balance_due)


def allocate_existing(db: Session, payment: Payment, invoice: Invoice, amount: Decimal) -> Decimal:
    if payment.status != "completed":
        raise Conflict("Only completed payments can be allocated")
    if invoice.student_id != payment.student_id:
        raise ValidationFailed("Invoice and payment belong to different students")
    done = _allocate(db, payment, invoice, amount)
    if done <= ZERO:
        raise ValidationFailed("Nothing to allocate")
    return done


def reverse_payment(db: Session, pay: Payment, reason: str, actor_id: uuid.UUID | None, bounced: bool = False) -> None:
    if pay.status != "completed":
        raise Conflict("Only completed payments can be reversed")
    refunded = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == pay.id, Refund.status.in_(("approved", "processed")))
    )
    if q2(refunded) > ZERO:
        raise Conflict("Payment has refunds; it cannot be reversed")
    allocs = db.scalars(
        select(PaymentAllocation).where(PaymentAllocation.payment_id == pay.id, PaymentAllocation.is_reversed.is_(False))
    ).all()
    now = datetime.now(timezone.utc)
    for a in allocs:
        inv = db.scalar(select(Invoice).where(Invoice.id == a.invoice_id).with_for_update())
        inv.amount_paid = q2(inv.amount_paid - a.amount)
        refresh_status(inv)
        a.is_reversed = True
        a.reversed_at = now
    pay.status = "bounced" if bounced else "reversed"
    pay.reversed_at = now
    pay.reversal_reason = reason
    pay.reversed_by_id = actor_id
    pay.unallocated_amount = ZERO
    ledger(db, pay, pay.student_id, "reversal", "payment", pay.id, debit=pay.amount,
           description=f"Reversal of {pay.receipt_number}: {reason}", actor_id=actor_id, currency=pay.currency)


def issue_credit_note(db: Session, inv: Invoice, amount: Decimal, reason: str, actor_id: uuid.UUID | None) -> CreditNote:
    amount = q2(amount)
    if inv.status in ("draft", "cancelled"):
        raise Conflict("Credit notes apply to issued invoices only")
    max_credit = q2(inv.total - inv.credit_applied)
    if amount <= ZERO or amount > max_credit:
        raise ValidationFailed(f"Credit amount must be between 0.01 and {max_credit}")
    cn = CreditNote(
        institute_id=inv.institute_id,
        branch_id=inv.branch_id,
        credit_note_number=numbering.next_number(db, inv.institute_id, "credit_note", "CN"),
        invoice_id=inv.id,
        student_id=inv.student_id,
        amount=amount,
        reason=reason,
        status="issued",
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    db.add(cn)
    db.flush()
    inv.credit_applied = q2(inv.credit_applied + amount)
    excess = q2(inv.amount_paid + inv.credit_applied - inv.total)
    if excess > ZERO:
        # Release over-allocated payments back to the student's advance balance (latest first).
        allocs = db.scalars(
            select(PaymentAllocation)
            .where(PaymentAllocation.invoice_id == inv.id, PaymentAllocation.is_reversed.is_(False))
            .order_by(PaymentAllocation.created_at.desc())
        ).all()
        now = datetime.now(timezone.utc)
        for a in allocs:
            if excess <= ZERO:
                break
            release = min(a.amount, excess)
            pay = db.scalar(select(Payment).where(Payment.id == a.payment_id).with_for_update())
            a.is_reversed = True
            a.reversed_at = now
            keep = q2(a.amount - release)
            if keep > ZERO:
                db.add(PaymentAllocation(institute_id=a.institute_id, payment_id=a.payment_id, invoice_id=inv.id, amount=keep))
            pay.unallocated_amount = q2(pay.unallocated_amount + release)
            inv.amount_paid = q2(inv.amount_paid - release)
            excess = q2(excess - release)
    refresh_status(inv)
    ledger(db, inv, inv.student_id, "credit_note", "credit_note", cn.id, credit=amount,
           description=f"Credit note {cn.credit_note_number} on {inv.invoice_number}: {reason}", actor_id=actor_id, currency=inv.currency)
    return cn


def request_refund(db: Session, pay: Payment, amount: Decimal, method: str, reason: str, actor_id) -> Refund:
    amount = q2(amount)
    if pay.status != "completed":
        raise Conflict("Refunds can only be raised against completed payments")
    pending = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == pay.id, Refund.status.in_(("pending", "approved")))
    )
    available = q2(pay.unallocated_amount - q2(pending))
    if amount <= ZERO or amount > available:
        raise ValidationFailed(
            f"Refundable amount is {available}. Issue a credit note first to release amounts allocated to invoices."
        )
    r = Refund(
        institute_id=pay.institute_id,
        branch_id=pay.branch_id,
        payment_id=pay.id,
        student_id=pay.student_id,
        amount=amount,
        method=method,
        reason=reason,
        status="pending",
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    db.add(r)
    db.flush()
    return r


def process_refund(db: Session, refund: Refund, reference_number: str | None, actor_id) -> None:
    if refund.status != "approved":
        raise Conflict("Refund must be approved before processing")
    pay = db.scalar(select(Payment).where(Payment.id == refund.payment_id).with_for_update())
    if refund.amount > pay.unallocated_amount:
        raise Conflict("Payment no longer has enough unallocated balance for this refund")
    pay.unallocated_amount = q2(pay.unallocated_amount - refund.amount)
    refund.status = "processed"
    refund.processed_at = datetime.now(timezone.utc)
    refund.reference_number = reference_number
    refund.refund_number = numbering.next_number(db, refund.institute_id, "refund", "RFD")
    ledger(db, refund, refund.student_id, "refund", "refund", refund.id, debit=refund.amount,
           description=f"Refund {refund.refund_number} against {pay.receipt_number}", actor_id=actor_id, currency=pay.currency)


# ----------------------------------------------------------------------------- scheduled billing

PERIOD_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12, "per_subject": 1, "per_course": 1, "installment": 1}


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 28)


def _agreement_items(db: Session, ag: StudentFeeAgreement, inst: Institute, description: str) -> list[InvoiceItem]:
    plan = db.get(FeePlan, ag.fee_plan_id) if ag.fee_plan_id else None
    tax_rate = Decimal(inst.tax_rate) if inst.tax_enabled and plan and plan.tax_applicable else ZERO
    discount = ZERO
    if ag.discount_type == "percent":
        discount = q2(ag.amount * ag.discount_value / Decimal(100))
    elif ag.discount_type == "fixed":
        discount = q2(ag.discount_value)
    discount = q2(discount + (ag.scholarship_amount or ZERO))
    return [build_item(description, ag.amount, discount=discount, tax_rate=tax_rate, subject_id=ag.subject_id)]


def generate_scheduled_invoices(db: Session, institute_id: uuid.UUID, as_of: date, actor_id: uuid.UUID | None = None) -> dict:
    inst = db.get(Institute, institute_id)
    agreements = db.scalars(
        select(StudentFeeAgreement).where(
            StudentFeeAgreement.institute_id == institute_id,
            StudentFeeAgreement.status == "active",
            StudentFeeAgreement.billing_type != "per_class",
            StudentFeeAgreement.effective_from <= as_of,
        )
    ).all()
    created = skipped = 0
    for ag in agreements:
        student = db.get(Student, ag.student_id)
        if student is None or student.status not in ("active",):
            continue
        plan = db.get(FeePlan, ag.fee_plan_id) if ag.fee_plan_id else None
        due_day = plan.due_day if plan else 10
        next_date = ag.next_billing_date or ag.effective_from
        guard = 0
        while next_date <= as_of and guard < 24:
            guard += 1
            if ag.effective_to and next_date > ag.effective_to:
                break
            if ag.billing_type in ("one_time", "custom"):
                period_end = ag.effective_to or next_date
            else:
                months = PERIOD_MONTHS.get(ag.billing_type, 1)
                period_end = add_months(next_date, months) - timedelta(days=1)
            exists = db.scalar(
                select(Invoice.id).where(
                    Invoice.agreement_id == ag.id, Invoice.period_start == next_date, Invoice.status != "cancelled",
                    Invoice.source == "scheduled",
                )
            )
            if exists:
                skipped += 1
            else:
                if ag.billing_type == "installment" and plan:
                    issued = db.scalar(
                        select(func.count()).where(Invoice.agreement_id == ag.id, Invoice.status != "cancelled", Invoice.source == "scheduled")
                    )
                    if issued >= plan.installments:
                        ag.status = "ended"
                        break
                label = plan.name if plan else ag.billing_type.replace("_", " ").title()
                desc = f"{label} ({next_date.strftime('%d-%m-%Y')} to {period_end.strftime('%d-%m-%Y')})"
                try:
                    due = date(next_date.year, next_date.month, min(due_day, 28))
                except ValueError:
                    due = next_date
                issue = min(next_date, as_of)
                due = max(due, issue)
                with db.begin_nested():
                    create_invoice(
                        db, institute_id, student, _agreement_items(db, ag, inst, desc), issue, due, actor_id,
                        source="scheduled", agreement_id=ag.id, period_start=next_date, period_end=period_end,
                    )
                created += 1
            if ag.billing_type in ("one_time", "custom"):
                ag.next_billing_date = date(9999, 12, 31)
                ag.status = "ended"
                break
            next_date = add_months(next_date, PERIOD_MONTHS.get(ag.billing_type, 1))
            ag.next_billing_date = next_date
    db.flush()
    return {"created": created, "skipped": skipped}


def generate_per_class_charges(db: Session, institute_id: uuid.UUID, from_date: date, to_date: date) -> dict:
    """Create reviewable charges from completed sessions with submitted attendance. Unique per student/session."""
    sessions = db.scalars(
        select(ClassSession).where(
            ClassSession.institute_id == institute_id,
            ClassSession.status == "completed",
            ClassSession.attendance_state == "submitted",
            ClassSession.billing_processed.is_(False),
            ClassSession.session_date.between(from_date, to_date),
        )
    ).all()
    created = 0
    for s in sessions:
        rows = db.execute(
            select(StudentAttendance.student_id, StudentAttendance.status).where(
                StudentAttendance.session_id == s.id, StudentAttendance.status.in_(BILLABLE_ATTENDANCE)
            )
        ).all()
        for student_id, status in rows:
            ag = db.scalar(
                select(StudentFeeAgreement)
                .where(
                    StudentFeeAgreement.student_id == student_id,
                    StudentFeeAgreement.billing_type == "per_class",
                    StudentFeeAgreement.status == "active",
                    StudentFeeAgreement.effective_from <= s.session_date,
                    or_(StudentFeeAgreement.effective_to.is_(None), StudentFeeAgreement.effective_to >= s.session_date),
                    or_(StudentFeeAgreement.subject_id.is_(None), StudentFeeAgreement.subject_id == s.subject_id),
                    or_(StudentFeeAgreement.batch_id.is_(None), StudentFeeAgreement.batch_id == s.batch_id),
                )
                .order_by(StudentFeeAgreement.subject_id.is_(None), StudentFeeAgreement.effective_from.desc())
                .limit(1)
            )
            if ag is None:
                continue
            res = db.execute(
                insert(BillableCharge)
                .values(
                    id=uuid.uuid4(),
                    institute_id=institute_id,
                    branch_id=s.branch_id,
                    student_id=student_id,
                    session_id=s.id,
                    agreement_id=ag.id,
                    subject_id=s.subject_id,
                    charge_date=s.session_date,
                    amount=q2(ag.amount),
                    attendance_status=status,
                    status="pending_review",
                )
                .on_conflict_do_nothing(index_elements=["student_id", "session_id"])
                .returning(BillableCharge.id)
            ).first()
            if res:
                created += 1
        s.billing_processed = True
    db.flush()
    return {"sessions": len(sessions), "charges_created": created}


def invoice_approved_charges(db: Session, institute_id: uuid.UUID, issue_date: date, due_date: date, actor_id,
                             student_ids: list[uuid.UUID] | None = None) -> dict:
    q = select(BillableCharge).where(BillableCharge.institute_id == institute_id, BillableCharge.status == "approved").with_for_update()
    if student_ids:
        q = q.where(BillableCharge.student_id.in_(student_ids))
    charges = db.scalars(q.order_by(BillableCharge.student_id, BillableCharge.charge_date)).all()
    grouped: dict[uuid.UUID, list[BillableCharge]] = {}
    for c in charges:
        grouped.setdefault(c.student_id, []).append(c)
    inst = db.get(Institute, institute_id)
    invoices = 0
    for student_id, rows in grouped.items():
        student = db.get(Student, student_id)
        items = []
        for c in rows:
            ag = db.get(StudentFeeAgreement, c.agreement_id)
            plan = db.get(FeePlan, ag.fee_plan_id) if ag and ag.fee_plan_id else None
            tax = Decimal(inst.tax_rate) if inst.tax_enabled and plan and plan.tax_applicable else ZERO
            items.append(build_item(f"Class on {c.charge_date.strftime('%d-%m-%Y')}", c.amount, tax_rate=tax,
                                    item_type="per_class", subject_id=c.subject_id, session_id=c.session_id))
        inv = create_invoice(db, institute_id, student, items, issue_date, due_date, actor_id, source="per_class",
                             period_start=min(c.charge_date for c in rows), period_end=max(c.charge_date for c in rows))
        item_rows = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).all()
        by_session = {i.session_id: i.id for i in item_rows}
        for c in rows:
            c.status = "invoiced"
            c.invoice_item_id = by_session.get(c.session_id)
        invoices += 1
    db.flush()
    return {"invoices_created": invoices, "charges_invoiced": len(charges)}


def apply_late_fees(db: Session, institute_id: uuid.UUID, today: date) -> int:
    rows = db.execute(
        select(Invoice, FeePlan)
        .join(StudentFeeAgreement, StudentFeeAgreement.id == Invoice.agreement_id)
        .join(FeePlan, FeePlan.id == StudentFeeAgreement.fee_plan_id)
        .where(
            Invoice.institute_id == institute_id,
            Invoice.status.in_(("issued", "partially_paid", "overdue")),
            Invoice.balance_due > 0,
            FeePlan.late_fee_amount > 0,
        )
    ).all()
    created = 0
    for inv, plan in rows:
        if inv.due_date + timedelta(days=plan.late_fee_grace_days) >= today:
            continue
        exists = db.scalar(select(Invoice.id).where(Invoice.supplementary_to_id == inv.id, Invoice.status != "cancelled"))
        if exists:
            continue
        student = db.get(Student, inv.student_id)
        create_invoice(db, institute_id, student, [build_item(f"Late fee for {inv.invoice_number}", plan.late_fee_amount, item_type="late_fee")],
                       today, today + timedelta(days=7), None, source="supplementary", supplementary_to_id=inv.id)
        created += 1
    return created


def refresh_overdue(db: Session, institute_id: uuid.UUID, today: date) -> int:
    rows = db.scalars(
        select(Invoice).where(
            Invoice.institute_id == institute_id, Invoice.status.in_(("issued", "partially_paid")), Invoice.due_date < today
        )
    ).all()
    for inv in rows:
        refresh_status(inv, today)
    return len(rows)


def student_balance(db: Session, student_id: uuid.UUID) -> dict:
    debit, credit = db.execute(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0), func.coalesce(func.sum(LedgerEntry.credit), 0)).where(
            LedgerEntry.student_id == student_id
        )
    ).one()
    outstanding = db.scalar(
        select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(
            Invoice.student_id == student_id, Invoice.status.in_(("issued", "partially_paid", "overdue"))
        )
    )
    advance = db.scalar(
        select(func.coalesce(func.sum(Payment.unallocated_amount), 0)).where(Payment.student_id == student_id, Payment.status == "completed")
    )
    return {
        "total_debits": q2(debit),
        "total_credits": q2(credit),
        "net_balance": q2(Decimal(debit) - Decimal(credit)),
        "outstanding": q2(outstanding),
        "advance": q2(advance),
    }
