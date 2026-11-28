import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.common import file_response, get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.db.session import get_db
from app.models import (
    BankTransaction,
    Book,
    BookLoan,
    CashbookEntry,
    ClassSession,
    CompensationRule,
    Expense,
    ExpenseCategory,
    FinancialYear,
    Institute,
    LedgerEntry,
    LibraryMember,
    Payment,
    PayrollPeriod,
    Payslip,
    PurchaseRecord,
    Refund,
    Teacher,
    TeacherAttendance,
    TeacherPayableEntry,
    TeacherPayout,
)
from app.models.finance import PAYMENT_METHODS
from app.services import audit, finance, notifications, numbering, pdf
from app.services.finance import q2

router = APIRouter(tags=["Accounting, payroll & resources"])


# ----------------------------------------------------------------------------- expenses & purchases


class DecideIn(BaseModel):
    status: Literal["approved", "rejected"]
    remarks: str | None = Field(default=None, max_length=1000)


@router.post("/expenses/{eid}/decide", dependencies=[Depends(require_feature("accounting"))])
def decide_expense(eid: uuid.UUID, body: DecideIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("expenses.write"))):
    e = get_tenant_obj(db, p, Expense, eid, lock=True, label="Expense")
    if e.status not in ("draft", "submitted"):
        raise Conflict("Only submitted expenses can be decided")
    if e.created_by_id == p.user_id and not p.can("tenant.admin"):
        raise Forbidden("Expenses must be approved by a different user")
    finance.ensure_period_open(db, p.institute_id, e.expense_date)
    e.status = body.status
    e.approved_by_id = p.user_id
    e.approved_at = datetime.now(timezone.utc)
    if body.status == "approved":
        finance.ledger(db, e, None, "expense", "expense", e.id, debit=q2(e.amount + e.tax_amount), description=e.description[:400],
                       actor_id=p.user_id, entry_date=e.expense_date, currency=e.currency)
    audit.record(db, p, "expenses", e.id, f"expense_{body.status}", reason=body.remarks, branch_id=e.branch_id)
    db.commit()
    return {"status": e.status}


class PaidIn(BaseModel):
    paid_on: date
    payment_method: Literal[PAYMENT_METHODS] = "cash"  # type: ignore[valid-type]
    reference_number: str | None = Field(default=None, max_length=120)
    bank_account_name: str | None = Field(default=None, max_length=120)


@router.post("/expenses/{eid}/mark-paid", dependencies=[Depends(require_feature("accounting"))])
def expense_paid(eid: uuid.UUID, body: PaidIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("expenses.write"))):
    e = get_tenant_obj(db, p, Expense, eid, lock=True, label="Expense")
    if e.status != "approved":
        raise Conflict("Only approved expenses can be marked paid")
    finance.ensure_period_open(db, p.institute_id, body.paid_on)
    e.status = "paid"
    e.paid_at = datetime.combine(body.paid_on, datetime.min.time(), tzinfo=timezone.utc)
    e.payment_method = body.payment_method
    e.reference_number = body.reference_number or e.reference_number
    total = q2(e.amount + e.tax_amount)
    if body.payment_method == "cash":
        db.add(CashbookEntry(institute_id=p.institute_id, branch_id=e.branch_id, entry_date=body.paid_on,
                             account="petty_cash" if e.is_petty_cash else "cash", direction="out", amount=total,
                             description=f"Expense: {e.description}"[:500], reference_type="expense", reference_id=e.id, created_by_id=p.user_id))
    else:
        db.add(BankTransaction(institute_id=p.institute_id, branch_id=e.branch_id, bank_account_name=body.bank_account_name or "Primary account",
                               txn_date=body.paid_on, description=f"Expense: {e.description}"[:500], direction="debit", amount=total,
                               reference_number=body.reference_number, matched_expense_id=e.id, is_reconciled=False, created_by_id=p.user_id))
    audit.record(db, p, "expenses", e.id, "expense_paid", new=body.model_dump(), branch_id=e.branch_id)
    db.commit()
    return {"status": e.status}


class PurchaseDecisionIn(BaseModel):
    status: Literal["approved", "rejected", "ordered", "received", "cancelled"]
    create_expense_category_id: uuid.UUID | None = None
    remarks: str | None = Field(default=None, max_length=1000)


@router.post("/purchase-records/{pid}/status", dependencies=[Depends(require_feature("accounting"))])
def purchase_status(pid: uuid.UUID, body: PurchaseDecisionIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("vendors.write"))):
    pr = get_tenant_obj(db, p, PurchaseRecord, pid, lock=True, label="Purchase")
    allowed = {"requested": {"approved", "rejected", "cancelled"}, "approved": {"ordered", "received", "cancelled"},
               "ordered": {"received", "cancelled"}}
    if body.status not in allowed.get(pr.status, set()):
        raise Conflict(f"Cannot move from {pr.status} to {body.status}")
    if body.status == "approved":
        if pr.created_by_id == p.user_id and not p.can("tenant.admin"):
            raise Forbidden("Purchases must be approved by a different user")
        pr.approved_by_id = p.user_id
        pr.approved_at = datetime.now(timezone.utc)
    old = pr.status
    pr.status = body.status
    if body.status == "received" and body.create_expense_category_id:
        if not pr.amount or pr.amount <= 0:
            raise ValidationFailed("Set the purchase amount before creating an expense")
        get_tenant_obj(db, p, ExpenseCategory, body.create_expense_category_id, label="Category")
        e = Expense(institute_id=p.institute_id, branch_id=pr.branch_id, category_id=body.create_expense_category_id, vendor_id=pr.vendor_id,
                    expense_date=date.today(), description=f"Purchase {pr.po_number or ''}: {pr.description}"[:500], amount=pr.amount,
                    tax_amount=pr.tax_amount or 0, status="submitted", created_by_id=p.user_id, updated_by_id=p.user_id)
        db.add(e)
        db.flush()
        pr.expense_id = e.id
    audit.record(db, p, "purchase_records", pr.id, "status_change", {"status": old}, {"status": body.status}, body.remarks)
    db.commit()
    return {"status": pr.status, "expense_id": pr.expense_id}


@router.get("/accounting/cashbook", dependencies=[Depends(require_feature("accounting"))])
def cashbook(account: Literal["cash", "petty_cash", "bank"] = "cash", start: date | None = None, end: date | None = None,
             db: Session = Depends(get_db), p: Principal = Depends(require_perm("accounting.read"))):
    base = select(CashbookEntry).where(CashbookEntry.institute_id == p.institute_id, CashbookEntry.account == account)
    if p.selected_branch_id:
        base = base.where(CashbookEntry.branch_id == p.selected_branch_id)
    elif p.branch_ids is not None:
        base = base.where(CashbookEntry.branch_id.in_(p.branch_ids))
    opening = Decimal("0")
    if start:
        for d, a in db.execute(select(CashbookEntry.direction, func.sum(CashbookEntry.amount)).where(
                CashbookEntry.id.in_(base.with_only_columns(CashbookEntry.id).where(CashbookEntry.entry_date < start))).group_by(CashbookEntry.direction)):
            opening += Decimal(a) if d == "in" else -Decimal(a)
        base = base.where(CashbookEntry.entry_date >= start)
    if end:
        base = base.where(CashbookEntry.entry_date <= end)
    bal = opening
    rows = []
    for r in db.scalars(base.order_by(CashbookEntry.entry_date, CashbookEntry.created_at)):
        bal += r.amount if r.direction == "in" else -r.amount
        rows.append({"id": r.id, "entry_date": r.entry_date, "description": r.description, "direction": r.direction, "amount": r.amount,
                     "balance": q2(bal), "reference_type": r.reference_type})
    return {"account": account, "opening_balance": q2(opening), "closing_balance": q2(bal), "entries": rows}


@router.post("/financial-years/{fid}/close", dependencies=[Depends(require_feature("accounting"))])
def close_year(fid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("finance.close_year"))):
    fy = get_tenant_obj(db, p, FinancialYear, fid, lock=True, label="Financial year")
    if fy.status == "closed":
        raise Conflict("Already closed")
    if fy.end_date >= date.today():
        raise ValidationFailed("A financial year can be closed only after it ends")
    dt_start = datetime.combine(fy.start_date, datetime.min.time(), tzinfo=timezone.utc)
    dt_end = datetime.combine(fy.end_date, datetime.max.time(), tzinfo=timezone.utc)
    income = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.institute_id == p.institute_id, Payment.status == "completed",
                                                                              Payment.paid_at.between(dt_start, dt_end)))
    refunds = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.institute_id == p.institute_id, Refund.status == "processed",
                                                                               Refund.processed_at.between(dt_start, dt_end)))
    expenses = db.scalar(select(func.coalesce(func.sum(Expense.amount + Expense.tax_amount), 0)).where(
        Expense.institute_id == p.institute_id, Expense.status.in_(("approved", "paid")), Expense.expense_date.between(fy.start_date, fy.end_date)))
    payroll = db.scalar(select(func.coalesce(func.sum(TeacherPayout.amount), 0)).where(
        TeacherPayout.institute_id == p.institute_id, TeacherPayout.status == "paid", TeacherPayout.paid_at.between(dt_start, dt_end)))
    pending = db.scalar(select(func.count()).where(Expense.institute_id == p.institute_id, Expense.status == "submitted",
                                                   Expense.expense_date.between(fy.start_date, fy.end_date)))
    if pending:
        raise Conflict(f"{pending} expense(s) in this year are still awaiting approval")
    fy.closing_summary = {"income": str(q2(income)), "refunds": str(q2(refunds)), "expenses": str(q2(expenses)), "payroll": str(q2(payroll)),
                          "net": str(q2(Decimal(income) - Decimal(refunds) - Decimal(expenses) - Decimal(payroll)))}
    fy.status = "closed"
    fy.closed_at = datetime.now(timezone.utc)
    fy.closed_by_id = p.user_id
    audit.record(db, p, "financial_years", fy.id, "close", new=fy.closing_summary)
    db.commit()
    return fy.closing_summary


# ----------------------------------------------------------------------------- payroll


def _rule_for(rules: list[CompensationRule], on: date, subject_id=None, batch_id=None) -> CompensationRule | None:
    best, best_score = None, -1
    for r in rules:
        if r.effective_from > on or (r.effective_to and r.effective_to < on):
            continue
        if r.subject_id and r.subject_id != subject_id:
            continue
        if r.batch_id and r.batch_id != batch_id:
            continue
        score = (2 if r.subject_id else 0) + (1 if r.batch_id else 0)
        if score > best_score:
            best, best_score = r, score
    return best


@router.post("/payroll-periods/{pid}/generate", dependencies=[Depends(require_feature("teacher_compensation"))])
def generate_payroll(pid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payroll.write"))):
    period = get_tenant_obj(db, p, PayrollPeriod, pid, lock=True, label="Payroll period")
    if period.status not in ("open", "processing"):
        raise Conflict("Payroll period is not open")
    tq = select(Teacher).where(Teacher.institute_id == p.institute_id, Teacher.joining_date <= period.end_date,
                               or_(Teacher.exit_date.is_(None), Teacher.exit_date >= period.start_date))
    if period.branch_id:
        tq = tq.where(Teacher.branch_id == period.branch_id)
    created = 0
    for t in db.scalars(tq):
        rules = list(db.scalars(select(CompensationRule).where(CompensationRule.teacher_id == t.id)))
        if not rules and t.compensation_amount:
            rules = [CompensationRule(teacher_id=t.id, compensation_type=t.compensation_type, amount=t.compensation_amount,
                                      effective_from=t.joining_date)]
        fixed = _rule_for([r for r in rules if r.compensation_type == "fixed_monthly"], period.end_date)
        if fixed and not db.scalar(select(TeacherPayableEntry.id).where(TeacherPayableEntry.teacher_id == t.id, TeacherPayableEntry.payroll_period_id == period.id,
                                                                         TeacherPayableEntry.entry_type == "salary", TeacherPayableEntry.status != "rejected")):
            days = (period.end_date - period.start_date).days + 1
            start = max(period.start_date, t.joining_date)
            end = min(period.end_date, t.exit_date or period.end_date)
            worked = (end - start).days + 1
            amount = q2(Decimal(fixed.amount) * Decimal(worked) / Decimal(days)) if worked < days else q2(fixed.amount)
            db.add(TeacherPayableEntry(institute_id=p.institute_id, teacher_id=t.id, payroll_period_id=period.id, rule_id=fixed.id,
                                       entry_type="salary", entry_date=period.end_date, quantity=Decimal(worked) / Decimal(days) if worked < days else 1,
                                       rate=fixed.amount, amount=amount, description=f"Salary {period.name}" + (" (prorated)" if worked < days else ""),
                                       status="pending", created_by_id=p.user_id))
            created += 1
        variable = [r for r in rules if r.compensation_type in ("per_class", "per_hour")]
        if variable:
            att = db.execute(
                select(TeacherAttendance, ClassSession).join(ClassSession, ClassSession.id == TeacherAttendance.session_id).where(
                    TeacherAttendance.teacher_id == t.id, TeacherAttendance.is_verified.is_(True), TeacherAttendance.status.in_(("present", "late")),
                    ClassSession.status == "completed", ClassSession.session_date.between(period.start_date, period.end_date))
            ).all()
            for ta, s in att:
                rule = _rule_for(variable, s.session_date, s.subject_id, s.batch_id)
                if rule is None:
                    continue
                if db.scalar(select(TeacherPayableEntry.id).where(TeacherPayableEntry.teacher_id == t.id, TeacherPayableEntry.session_id == s.id,
                                                                  TeacherPayableEntry.status != "rejected")):
                    continue
                if rule.compensation_type == "per_class":
                    qty, amount, typ, desc = Decimal(1), q2(rule.amount), "per_class", f"Class {s.session_date:%d-%m-%Y}"
                else:
                    hours = Decimal(ta.teaching_minutes or 0) / Decimal(60)
                    qty, amount, typ, desc = q2(hours), q2(hours * Decimal(rule.amount)), "per_hour", f"{q2(hours)} h on {s.session_date:%d-%m-%Y}"
                db.add(TeacherPayableEntry(institute_id=p.institute_id, teacher_id=t.id, payroll_period_id=period.id, session_id=s.id, rule_id=rule.id,
                                           entry_type=typ, entry_date=s.session_date, quantity=qty, rate=rule.amount, amount=amount,
                                           description=desc, status="pending", created_by_id=p.user_id))
                s.compensation_processed = True
                created += 1
    manual = db.scalars(select(TeacherPayableEntry).where(TeacherPayableEntry.institute_id == p.institute_id,
                                                          TeacherPayableEntry.payroll_period_id.is_(None),
                                                          TeacherPayableEntry.entry_date.between(period.start_date, period.end_date))).all()
    for m in manual:
        m.payroll_period_id = period.id
    period.status = "processing"
    audit.record(db, p, "payroll_periods", period.id, "generate", new={"entries_created": created, "manual_attached": len(manual)})
    db.commit()
    return {"entries_created": created, "manual_entries_attached": len(manual)}


@router.post("/teacher-payables/{eid}/decide", dependencies=[Depends(require_feature("teacher_compensation"))])
def decide_payable(eid: uuid.UUID, body: DecideIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payroll.approve"))):
    e = get_tenant_obj(db, p, TeacherPayableEntry, eid, lock=True, label="Payable entry")
    if e.status != "pending":
        raise Conflict("Entry already decided")
    e.status = body.status
    e.approved_by_id = p.user_id
    audit.record(db, p, "teacher_payable_entries", e.id, f"payable_{body.status}", reason=body.remarks)
    db.commit()
    return {"status": e.status}


@router.post("/payroll-periods/{pid}/approve", dependencies=[Depends(require_feature("teacher_compensation"))])
def approve_payroll(pid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payroll.approve"))):
    period = get_tenant_obj(db, p, PayrollPeriod, pid, lock=True, label="Payroll period")
    if period.status != "processing":
        raise Conflict("Generate payroll entries before approval")
    entries = db.scalars(select(TeacherPayableEntry).where(TeacherPayableEntry.payroll_period_id == period.id,
                                                           TeacherPayableEntry.status.in_(("pending", "approved")))).all()
    by_teacher: dict[uuid.UUID, list[TeacherPayableEntry]] = {}
    for e in entries:
        if e.status == "pending":
            e.status = "approved"
            e.approved_by_id = p.user_id
        by_teacher.setdefault(e.teacher_id, []).append(e)
    slips = 0
    for tid, rows in by_teacher.items():
        gross = sum((r.amount for r in rows if r.entry_type != "deduction"), Decimal("0"))
        ded = sum((r.amount for r in rows if r.entry_type == "deduction"), Decimal("0"))
        slip = db.scalar(select(Payslip).where(Payslip.payroll_period_id == period.id, Payslip.teacher_id == tid))
        if slip is None:
            slip = Payslip(institute_id=p.institute_id, payroll_period_id=period.id, teacher_id=tid,
                           payslip_number=numbering.next_number(db, p.institute_id, "payslip", "PS", period.end_date), created_by_id=p.user_id)
            db.add(slip)
        slip.gross_amount, slip.deductions, slip.net_amount = q2(gross), q2(ded), q2(max(gross - ded, Decimal("0")))
        slip.status = "approved"
        slip.approved_by_id = p.user_id
        slip.details = {"entries": len(rows)}
        slips += 1
        t = db.get(Teacher, tid)
        notifications.notify(db, p.institute_id, [t.user_id], "system", f"Payslip ready: {period.name}", f"Net pay {slip.net_amount}",
                             link="/r/payslips", dedupe_key=f"payslip:{period.id}:{tid}")
    period.status = "approved"
    period.approved_by_id = p.user_id
    period.approved_at = datetime.now(timezone.utc)
    audit.record(db, p, "payroll_periods", period.id, "approve", new={"payslips": slips})
    db.commit()
    return {"payslips": slips}


class PayoutIn(BaseModel):
    method: Literal[PAYMENT_METHODS] = "bank_transfer"  # type: ignore[valid-type]
    reference_number: str | None = Field(default=None, max_length=120)
    paid_at: datetime | None = None


@router.post("/payslips/{sid}/pay", dependencies=[Depends(require_feature("teacher_compensation"))])
def pay_payslip(sid: uuid.UUID, body: PayoutIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("payroll.approve"))):
    slip = get_tenant_obj(db, p, Payslip, sid, lock=True, label="Payslip")
    if slip.status != "approved":
        raise Conflict("Only approved payslips can be paid")
    if body.method != "cash" and not body.reference_number:
        raise ValidationFailed("A transaction reference is required")
    paid_at = body.paid_at or datetime.now(timezone.utc)
    finance.ensure_period_open(db, p.institute_id, paid_at.date())
    t = db.get(Teacher, slip.teacher_id)
    payout = TeacherPayout(institute_id=p.institute_id, teacher_id=slip.teacher_id, payslip_id=slip.id, amount=slip.net_amount, method=body.method,
                           reference_number=body.reference_number, paid_at=paid_at, status="paid", created_by_id=p.user_id)
    if slip.net_amount <= 0:
        raise ValidationFailed("Net amount is zero")
    db.add(payout)
    db.flush()
    slip.status = "paid"
    for e in db.scalars(select(TeacherPayableEntry).where(TeacherPayableEntry.payroll_period_id == slip.payroll_period_id,
                                                          TeacherPayableEntry.teacher_id == slip.teacher_id, TeacherPayableEntry.status == "approved")):
        e.status = "paid"
    db.add(LedgerEntry(institute_id=p.institute_id, branch_id=t.branch_id, student_id=None, entry_date=paid_at.date(), entry_type="payroll",
                       reference_type="teacher_payout", reference_id=payout.id, debit=slip.net_amount, credit=0,
                       description=f"Payout {slip.payslip_number} to {t.full_name}", created_by_id=p.user_id))
    if body.method == "cash":
        db.add(CashbookEntry(institute_id=p.institute_id, branch_id=t.branch_id, entry_date=paid_at.date(), account="cash", direction="out",
                             amount=slip.net_amount, description=f"Salary {slip.payslip_number}", reference_type="teacher_payout",
                             reference_id=payout.id, created_by_id=p.user_id))
    remaining = db.scalar(select(func.count()).where(Payslip.payroll_period_id == slip.payroll_period_id, Payslip.status != "paid"))
    if remaining == 0:
        db.get(PayrollPeriod, slip.payroll_period_id).status = "paid"
    audit.record(db, p, "payslips", slip.id, "paid", new={"amount": slip.net_amount, "method": body.method})
    db.commit()
    return {"payout_id": payout.id}


@router.get("/payslips/{sid}/pdf")
def payslip_pdf(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    slip = get_tenant_obj(db, p, Payslip, sid, label="Payslip")
    if not (p.can("payroll.read") or slip.teacher_id == p.teacher_id):
        raise Forbidden("You cannot view this payslip")
    period = db.get(PayrollPeriod, slip.payroll_period_id)
    t = db.get(Teacher, slip.teacher_id)
    entries = db.scalars(select(TeacherPayableEntry).where(TeacherPayableEntry.payroll_period_id == period.id, TeacherPayableEntry.teacher_id == t.id,
                                                           TeacherPayableEntry.status.in_(("approved", "paid"))).order_by(TeacherPayableEntry.entry_date)).all()
    data = pdf.payslip_pdf(db.get(Institute, p.institute_id), slip, t, period, entries)
    return file_response(data, f"{slip.payslip_number.replace('/', '-')}.pdf", "application/pdf", inline=True)


# ----------------------------------------------------------------------------- library


class IssueIn(BaseModel):
    book_id: uuid.UUID
    member_id: uuid.UUID
    due_date: date
    remarks: str | None = Field(default=None, max_length=500)


@router.post("/library/issue", status_code=201, dependencies=[Depends(require_feature("library"))])
def issue_book(body: IssueIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("library.write"))):
    book = get_tenant_obj(db, p, Book, body.book_id, lock=True, label="Book")
    member = get_tenant_obj(db, p, LibraryMember, body.member_id, label="Member")
    if not member.is_active or (member.valid_until and member.valid_until < date.today()):
        raise Conflict("Membership is inactive or expired")
    if book.is_digital:
        raise ValidationFailed("Digital resources are accessed online, not issued")
    if book.copies_available <= 0:
        raise Conflict("No copies available")
    out = db.scalar(select(func.count()).where(BookLoan.member_id == member.id, BookLoan.status.in_(("issued", "overdue"))))
    if out >= member.max_books:
        raise Conflict(f"Member already has {out} book(s) issued (limit {member.max_books})")
    if body.due_date < date.today():
        raise ValidationFailed("Due date must be in the future")
    loan = BookLoan(institute_id=p.institute_id, book_id=book.id, member_id=member.id, issued_on=date.today(), due_date=body.due_date,
                    status="issued", remarks=body.remarks, created_by_id=p.user_id)
    book.copies_available -= 1
    db.add(loan)
    db.flush()
    audit.record(db, p, "book_loans", loan.id, "issue", new={"book": book.title, "member": member.full_name})
    db.commit()
    return {"id": loan.id}


class ReturnIn(BaseModel):
    outcome: Literal["returned", "lost", "damaged"] = "returned"
    fine_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=500)


@router.post("/library/loans/{lid}/return", dependencies=[Depends(require_feature("library"))])
def return_book(lid: uuid.UUID, body: ReturnIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("library.write"))):
    loan = get_tenant_obj(db, p, BookLoan, lid, lock=True, label="Loan")
    if loan.status not in ("issued", "overdue"):
        raise Conflict("Loan already closed")
    book = db.scalar(select(Book).where(Book.id == loan.book_id).with_for_update())
    loan.status = body.outcome
    loan.returned_on = date.today()
    loan.fine_amount = body.fine_amount
    loan.remarks = body.remarks or loan.remarks
    if body.outcome == "returned":
        book.copies_available = min(book.copies_total, book.copies_available + 1)
    else:
        book.copies_total = max(0, book.copies_total - 1)
    audit.record(db, p, "book_loans", loan.id, f"loan_{body.outcome}", new={"fine": body.fine_amount})
    db.commit()
    return {"status": loan.status}
