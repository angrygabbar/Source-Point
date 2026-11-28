import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.common import ensure_student_access, file_response, get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.core.errors import Conflict, Forbidden, IntegrationUnavailable, NotFound, ValidationFailed
from app.db.session import get_db
from app.integrations import providers, registry
from app.models import (
    BillableCharge,
    CreditNote,
    InboundWebhookEvent,
    Institute,
    Invoice,
    InvoiceItem,
    LedgerEntry,
    Payment,
    PaymentAllocation,
    Refund,
    Student,
    StudentParent,
    Subject,
)
from app.models.finance import PAYMENT_METHODS
from app.services import audit, feature_flags, finance, pdf

router = APIRouter(tags=["Fees & billing"], dependencies=[Depends(require_feature("billing"))])
public_router = APIRouter(tags=["Webhooks"])


def _can_view_student_fees(db: Session, p: Principal, student: Student) -> None:
    if p.can("invoices.read"):
        p.check_branch(student.branch_id)
        return
    if p.student_id == student.id:
        return
    if p.parent_id:
        link = db.scalar(select(StudentParent).where(StudentParent.student_id == student.id, StudentParent.parent_id == p.parent_id))
        if link and link.can_view_fees:
            return
    raise Forbidden("You cannot view this student's fee records")


# ----------------------------------------------------------------------------- invoices


class ItemIn(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    item_type: Literal["tuition", "admission", "exam", "material", "lab", "transport", "late_fee", "other"] = "tuition"
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    subject_id: uuid.UUID | None = None


class InvoiceIn(BaseModel):
    student_id: uuid.UUID
    issue_date: date
    due_date: date
    period_start: date | None = None
    period_end: date | None = None
    items: list[ItemIn] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    post: bool = True


def _items(db: Session, inst: Institute, items: list[ItemIn]):
    out = []
    for it in items:
        rate = it.tax_rate if it.tax_rate is not None else (Decimal(inst.tax_rate) if inst.tax_enabled else Decimal("0"))
        if not inst.tax_enabled:
            rate = Decimal("0")
        out.append(finance.build_item(it.description, it.unit_price, it.quantity, it.discount, rate, it.item_type, it.subject_id))
    return out


@router.post("/invoices", status_code=201)
def create_invoice(body: InvoiceIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    student = get_tenant_obj(db, p, Student, body.student_id, label="Student")
    inst = db.get(Institute, p.institute_id)
    inv = finance.create_invoice(db, p.institute_id, student, _items(db, inst, body.items), body.issue_date, body.due_date, p.user_id,
                                 period_start=body.period_start, period_end=body.period_end, notes=body.notes, post=body.post)
    audit.record(db, p, "invoices", inv.id, "create", new={"total": inv.total, "status": inv.status, "student_id": student.id}, branch_id=inv.branch_id)
    db.commit()
    return {"id": inv.id, "invoice_number": inv.invoice_number, "total": inv.total, "status": inv.status}


@router.post("/invoices/{iid}/issue")
def issue_invoice(iid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    inv = get_tenant_obj(db, p, Invoice, iid, lock=True, label="Invoice")
    finance.post_invoice(db, inv, p.user_id)
    audit.record(db, p, "invoices", inv.id, "issue", new={"invoice_number": inv.invoice_number}, branch_id=inv.branch_id)
    db.commit()
    return {"invoice_number": inv.invoice_number, "status": inv.status}


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/invoices/{iid}/cancel")
def cancel_invoice(iid: uuid.UUID, body: ReasonIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.cancel"))):
    inv = get_tenant_obj(db, p, Invoice, iid, lock=True, label="Invoice")
    finance.cancel_invoice(db, inv, body.reason, p.user_id)
    audit.record(db, p, "invoices", inv.id, "cancel", reason=body.reason, branch_id=inv.branch_id)
    db.commit()
    return {"status": inv.status}


class CreditIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/invoices/{iid}/credit-note", status_code=201)
def credit_note(iid: uuid.UUID, body: CreditIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.adjust"))):
    inv = get_tenant_obj(db, p, Invoice, iid, lock=True, label="Invoice")
    cn = finance.issue_credit_note(db, inv, body.amount, body.reason, p.user_id)
    audit.record(db, p, "invoices", inv.id, "credit_note", new={"credit_note": cn.credit_note_number, "amount": body.amount}, reason=body.reason)
    db.commit()
    return {"credit_note_number": cn.credit_note_number, "balance_due": inv.balance_due}


class SupplementaryIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=50)
    due_date: date
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/invoices/{iid}/supplementary", status_code=201)
def supplementary(iid: uuid.UUID, body: SupplementaryIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.adjust"))):
    inv = get_tenant_obj(db, p, Invoice, iid, label="Invoice")
    if inv.status in ("draft", "cancelled"):
        raise Conflict("Supplementary invoices apply to issued invoices")
    student = db.get(Student, inv.student_id)
    inst = db.get(Institute, p.institute_id)
    new = finance.create_invoice(db, p.institute_id, student, _items(db, inst, body.items), date.today(), body.due_date, p.user_id,
                                 source="supplementary", supplementary_to_id=inv.id, notes=f"Adjustment to {inv.invoice_number}: {body.reason}")
    audit.record(db, p, "invoices", inv.id, "supplementary", new={"invoice_id": new.id, "total": new.total}, reason=body.reason)
    db.commit()
    return {"id": new.id, "invoice_number": new.invoice_number}


def _invoice_bundle(db: Session, inv: Invoice):
    items = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).all()
    allocs = db.execute(select(Payment.receipt_number, Payment.paid_at, PaymentAllocation.amount, PaymentAllocation.is_reversed, Payment.id)
                        .join(Payment, Payment.id == PaymentAllocation.payment_id).where(PaymentAllocation.invoice_id == inv.id)
                        .order_by(Payment.paid_at)).all()
    return items, allocs


@router.get("/invoices/{iid}/detail")
def invoice_detail(iid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    inv = get_tenant_obj(db, p, Invoice, iid, label="Invoice")
    student = db.get(Student, inv.student_id)
    _can_view_student_fees(db, p, student)
    items, allocs = _invoice_bundle(db, inv)
    cns = db.scalars(select(CreditNote).where(CreditNote.invoice_id == inv.id)).all()
    return {"invoice": audit.snapshot(inv), "student": {"id": student.id, "full_name": student.full_name, "student_code": student.student_code},
            "items": [audit.snapshot(i) for i in items],
            "allocations": [{"receipt_number": r, "paid_at": d, "amount": a, "is_reversed": rev, "payment_id": pid} for r, d, a, rev, pid in allocs],
            "credit_notes": [audit.snapshot(c) for c in cns],
            "online_payment_available": feature_flags.is_enabled(db, p.institute_id, "online_payments")
            and registry.get_active(db, p.institute_id, "payment") is not None}


@router.get("/invoices/{iid}/pdf")
def invoice_pdf(iid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    inv = get_tenant_obj(db, p, Invoice, iid, label="Invoice")
    student = db.get(Student, inv.student_id)
    _can_view_student_fees(db, p, student)
    items, allocs = _invoice_bundle(db, inv)
    data = pdf.invoice_pdf(db.get(Institute, p.institute_id), inv, student, items, [(r, d, a) for r, d, a, rev, _ in allocs if not rev])
    return file_response(data, f"{(inv.invoice_number or 'draft').replace('/', '-')}.pdf", "application/pdf", inline=True)


# ----------------------------------------------------------------------------- scheduled & per-class billing


class AsOfIn(BaseModel):
    as_of: date


@router.post("/billing/generate-invoices")
def generate_invoices(body: AsOfIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    r = finance.generate_scheduled_invoices(db, p.institute_id, body.as_of, p.user_id)
    audit.record(db, p, "invoices", None, "scheduled_generation", new={**r, "as_of": body.as_of})
    db.commit()
    return r


class RangeIn(BaseModel):
    from_date: date
    to_date: date


@router.post("/billing/per-class/generate")
def per_class_generate(body: RangeIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    if body.to_date < body.from_date:
        raise ValidationFailed("Invalid range")
    r = finance.generate_per_class_charges(db, p.institute_id, body.from_date, body.to_date)
    audit.record(db, p, "billable_charges", None, "generate", new=r)
    db.commit()
    return r


class ReviewIn(BaseModel):
    charge_ids: list[uuid.UUID] = Field(min_length=1, max_length=2000)
    action: Literal["approve", "waive"]
    note: str | None = Field(default=None, max_length=1000)


@router.post("/billing/per-class/review")
def per_class_review(body: ReviewIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    if body.action == "waive" and not body.note:
        raise ValidationFailed("A note is required when waiving charges")
    rows = db.scalars(select(BillableCharge).where(BillableCharge.id.in_(body.charge_ids), BillableCharge.institute_id == p.institute_id,
                                                  BillableCharge.status == "pending_review").with_for_update()).all()
    now = datetime.now(timezone.utc)
    for c in rows:
        p.check_branch(c.branch_id)
        c.status = "approved" if body.action == "approve" else "waived"
        c.reviewed_by_id = p.user_id
        c.reviewed_at = now
        c.review_note = body.note
    audit.record(db, p, "billable_charges", None, f"review_{body.action}", new={"count": len(rows)}, reason=body.note)
    db.commit()
    return {"updated": len(rows)}


class PerClassInvoiceIn(BaseModel):
    issue_date: date
    due_date: date
    student_ids: list[uuid.UUID] | None = None


@router.post("/billing/per-class/invoice")
def per_class_invoice(body: PerClassInvoiceIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("invoices.write"))):
    r = finance.invoice_approved_charges(db, p.institute_id, body.issue_date, body.due_date, p.user_id, body.student_ids)
    audit.record(db, p, "invoices", None, "per_class_invoicing", new=r)
    db.commit()
    return r


# ----------------------------------------------------------------------------- payments


class AllocIn(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentIn(BaseModel):
    student_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["cash", "upi", "bank_transfer", "cheque", "card"]
    paid_at: datetime | None = None
    reference_number: str | None = Field(default=None, max_length=120)
    cheque_date: date | None = None
    bank_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    allocations: list[AllocIn] | None = None


@router.post("/payments", status_code=201)
def collect_payment(body: PaymentIn, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
                    db: Session = Depends(get_db), p: Principal = Depends(require_perm("payments.write"))):
    student = get_tenant_obj(db, p, Student, body.student_id, lock=True, label="Student")
    pay, created = finance.record_payment(
        db, p.institute_id, student, body.amount, body.method, body.paid_at or datetime.now(timezone.utc), idempotency_key, p.user_id,
        reference_number=body.reference_number, allocations=[(a.invoice_id, a.amount) for a in body.allocations] if body.allocations else None,
        notes=body.notes, cheque_date=body.cheque_date, bank_name=body.bank_name)
    if created:
        audit.record(db, p, "payments", pay.id, "collect", new={"amount": pay.amount, "method": pay.method, "receipt": pay.receipt_number},
                     branch_id=pay.branch_id)
    db.commit()
    return {"id": pay.id, "receipt_number": pay.receipt_number, "unallocated_amount": pay.unallocated_amount, "replayed": not created}


@router.get("/payments/{pid}/receipt.pdf")
def receipt(pid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    pay = get_tenant_obj(db, p, Payment, pid, label="Payment")
    student = db.get(Student, pay.student_id)
    _can_view_student_fees(db, p, student)
    allocs = db.execute(select(Invoice.invoice_number, PaymentAllocation.amount).join(Invoice, Invoice.id == PaymentAllocation.invoice_id)
                        .where(PaymentAllocation.payment_id == pay.id, PaymentAllocation.is_reversed.is_(False))).all()
    data = pdf.receipt_pdf(db.get(Institute, p.institute_id), pay, student, list(allocs))
    return file_response(data, f"{pay.receipt_number.replace('/', '-')}.pdf", "application/pdf", inline=True)


class ReverseIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    bounced: bool = False


@router.post("/payments/{pid}/reverse")
def reverse(pid: uuid.UUID, body: ReverseIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payments.reverse"))):
    pay = get_tenant_obj(db, p, Payment, pid, lock=True, label="Payment")
    finance.reverse_payment(db, pay, body.reason, p.user_id, body.bounced)
    audit.record(db, p, "payments", pay.id, "reverse", reason=body.reason, branch_id=pay.branch_id)
    db.commit()
    return {"status": pay.status}


@router.post("/payments/{pid}/allocate")
def allocate(pid: uuid.UUID, body: AllocIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payments.write"))):
    pay = get_tenant_obj(db, p, Payment, pid, lock=True, label="Payment")
    inv = get_tenant_obj(db, p, Invoice, body.invoice_id, lock=True, label="Invoice")
    if inv.status not in ("issued", "partially_paid", "overdue"):
        raise Conflict("Invoice is not open")
    done = finance.allocate_existing(db, pay, inv, body.amount)
    audit.record(db, p, "payments", pay.id, "allocate", new={"invoice_id": inv.id, "amount": done})
    db.commit()
    return {"allocated": done, "unallocated_amount": pay.unallocated_amount}


class RefundIn(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal[PAYMENT_METHODS] = "bank_transfer"  # type: ignore[valid-type]
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/refunds", status_code=201)
def create_refund(body: RefundIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("refunds.write"))):
    pay = get_tenant_obj(db, p, Payment, body.payment_id, lock=True, label="Payment")
    r = finance.request_refund(db, pay, body.amount, body.method, body.reason, p.user_id)
    audit.record(db, p, "refunds", r.id, "request", new={"amount": body.amount}, reason=body.reason, branch_id=r.branch_id)
    db.commit()
    return {"id": r.id}


@router.post("/refunds/{rid}/approve")
def approve_refund(rid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("refunds.approve"))):
    r = get_tenant_obj(db, p, Refund, rid, lock=True, label="Refund")
    if r.status != "pending":
        raise Conflict("Refund is not pending")
    if r.created_by_id == p.user_id and not p.can("tenant.admin"):
        raise Forbidden("Refunds must be approved by a different user")
    r.status = "approved"
    r.approved_by_id = p.user_id
    r.approved_at = datetime.now(timezone.utc)
    audit.record(db, p, "refunds", r.id, "approve")
    db.commit()
    return {"status": r.status}


@router.post("/refunds/{rid}/reject")
def reject_refund(rid: uuid.UUID, body: ReasonIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("refunds.approve"))):
    r = get_tenant_obj(db, p, Refund, rid, lock=True, label="Refund")
    if r.status not in ("pending", "approved"):
        raise Conflict("Refund cannot be rejected now")
    r.status = "rejected"
    audit.record(db, p, "refunds", r.id, "reject", reason=body.reason)
    db.commit()
    return {"status": r.status}


class ProcessIn(BaseModel):
    reference_number: str | None = Field(default=None, max_length=120)


@router.post("/refunds/{rid}/process")
def process_refund(rid: uuid.UUID, body: ProcessIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("refunds.approve"))):
    r = get_tenant_obj(db, p, Refund, rid, lock=True, label="Refund")
    finance.process_refund(db, r, body.reference_number, p.user_id)
    audit.record(db, p, "refunds", r.id, "process", new={"refund_number": r.refund_number})
    db.commit()
    return {"status": r.status, "refund_number": r.refund_number}


@router.get("/students/{student_id}/ledger")
def student_ledger(student_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    _can_view_student_fees(db, p, s)
    rows = db.scalars(select(LedgerEntry).where(LedgerEntry.student_id == s.id).order_by(LedgerEntry.entry_date, LedgerEntry.created_at)).all()
    bal = Decimal("0")
    out = []
    for r in rows:
        bal += Decimal(r.debit) - Decimal(r.credit)
        out.append({"id": r.id, "entry_date": r.entry_date, "entry_type": r.entry_type, "description": r.description, "debit": r.debit,
                    "credit": r.credit, "balance": finance.q2(bal), "reference_type": r.reference_type, "reference_id": r.reference_id})
    return {"student": {"id": s.id, "full_name": s.full_name, "student_code": s.student_code}, "summary": finance.student_balance(db, s.id),
            "entries": out}


@router.get("/students/{student_id}/open-invoices")
def student_open_invoices(student_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    _can_view_student_fees(db, p, s)
    return [{"id": i.id, "invoice_number": i.invoice_number, "issue_date": i.issue_date, "due_date": i.due_date, "total": i.total,
             "balance_due": i.balance_due, "status": i.status} for i in finance.open_invoices(db, s.id, lock=False)]


# ----------------------------------------------------------------------------- online payments (Razorpay)


def _gateway(db: Session, institute_id: uuid.UUID):
    if not feature_flags.is_enabled(db, institute_id, "online_payments"):
        raise IntegrationUnavailable("Online payments are disabled")
    cfg = registry.get_active(db, institute_id, "payment")
    if cfg is None:
        raise IntegrationUnavailable("No payment gateway is configured")
    return cfg


class OrderIn(BaseModel):
    invoice_id: uuid.UUID


@router.post("/payments/online/order")
def online_order(body: OrderIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    inv = get_tenant_obj(db, p, Invoice, body.invoice_id, label="Invoice")
    student = db.get(Student, inv.student_id)
    _can_view_student_fees(db, p, student)
    if inv.status not in ("issued", "partially_paid", "overdue") or inv.balance_due <= 0:
        raise Conflict("Invoice has no payable balance")
    cfg = _gateway(db, p.institute_id)
    try:
        order = providers.razorpay_create_order(cfg, int(inv.balance_due * 100), inv.currency, inv.invoice_number or str(inv.id),
                                                {"invoice_id": str(inv.id), "institute_id": str(p.institute_id), "student_id": str(student.id)})
    except providers.ProviderError as e:
        raise IntegrationUnavailable(str(e))
    audit.record(db, p, "invoices", inv.id, "online_order_created", new={"order_id": order.get("id")})
    db.commit()
    return {"provider": cfg.provider, "key_id": cfg.config.get("key_id"), "order_id": order.get("id"), "amount": order.get("amount"),
            "currency": order.get("currency"), "invoice_number": inv.invoice_number, "student_name": student.full_name}


class VerifyIn(BaseModel):
    invoice_id: uuid.UUID
    razorpay_order_id: str = Field(max_length=120)
    razorpay_payment_id: str = Field(max_length=120)
    razorpay_signature: str = Field(max_length=256)


def _record_gateway_payment(db: Session, institute_id: uuid.UUID, inv: Invoice, gw_payment: dict, order_id: str, actor_id) -> Payment:
    if gw_payment.get("status") != "captured":
        raise Conflict("Payment is not captured by the gateway yet")
    if gw_payment.get("order_id") != order_id:
        raise ValidationFailed("Payment does not belong to this order")
    amount = finance.q2(Decimal(gw_payment["amount"]) / 100)
    student = db.get(Student, inv.student_id)
    allocs = [(inv.id, min(amount, inv.balance_due))] if inv.balance_due > 0 else None
    pay, _ = finance.record_payment(db, institute_id, student, amount, "online_gateway", datetime.now(timezone.utc),
                                    f"gw:{gw_payment['id']}", actor_id, reference_number=gw_payment["id"], allocations=allocs,
                                    gateway_order_id=order_id, gateway_payment_id=gw_payment["id"], notes="Online payment")
    return pay


@router.post("/payments/online/verify")
def online_verify(body: VerifyIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    inv = get_tenant_obj(db, p, Invoice, body.invoice_id, lock=True, label="Invoice")
    _can_view_student_fees(db, p, db.get(Student, inv.student_id))
    cfg = _gateway(db, p.institute_id)
    if not providers.razorpay_verify_checkout(cfg, body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature):
        raise ValidationFailed("Payment signature verification failed")
    try:
        gw = providers.razorpay_fetch_payment(cfg, body.razorpay_payment_id)
    except providers.ProviderError as e:
        raise IntegrationUnavailable(str(e))
    pay = _record_gateway_payment(db, p.institute_id, inv, gw, body.razorpay_order_id, p.user_id)
    db.commit()
    return {"receipt_number": pay.receipt_number, "payment_id": pay.id}


@public_router.post("/webhooks/razorpay/{institute_id}", include_in_schema=True)
async def razorpay_webhook(institute_id: uuid.UUID, request: Request, db: Session = Depends(get_db),
                           x_razorpay_signature: str = Header(...), x_razorpay_event_id: str | None = Header(default=None)):
    body = await request.body()
    cfg = registry.get_active(db, institute_id, "payment")
    if cfg is None or not providers.razorpay_verify_webhook(cfg, body, x_razorpay_signature):
        raise Forbidden("Invalid webhook signature")
    payload = json.loads(body)
    event_id = x_razorpay_event_id or payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id", "")
    if db.scalar(select(InboundWebhookEvent.id).where(InboundWebhookEvent.provider == "razorpay", InboundWebhookEvent.event_id == event_id)):
        return {"status": "duplicate"}
    ev = InboundWebhookEvent(institute_id=institute_id, provider="razorpay", event_id=event_id, event_type=payload.get("event"),
                             payload=payload, signature_valid=True)
    db.add(ev)
    db.flush()
    try:
        with db.begin_nested():
            if payload.get("event") == "payment.captured":
                ent = payload["payload"]["payment"]["entity"]
                notes = ent.get("notes") or {}
                inv_id = uuid.UUID(notes["invoice_id"])
                inv = db.scalar(select(Invoice).where(Invoice.id == inv_id, Invoice.institute_id == institute_id).with_for_update())
                if inv is None:
                    raise NotFound("Invoice not found")
                _record_gateway_payment(db, institute_id, inv, ent, ent.get("order_id"), None)
        ev.processed_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001
        ev.error = type(exc).__name__
    db.commit()
    return {"status": "ok"}
