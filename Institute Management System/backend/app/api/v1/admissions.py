import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.common import get_tenant_obj
from app.api.deps import Principal, require_feature, require_perm
from app.core.errors import Conflict, ValidationFailed
from app.db.session import get_db
from app.models import (
    AdmissionRecord,
    Batch,
    Campaign,
    Enquiry,
    FeePlan,
    FollowUp,
    Lead,
    Student,
    StudentEnrollment,
    StudentFeeAgreement,
)
from app.models.admissions import ENQUIRY_STAGES, LEAD_SOURCES
from app.services import audit, finance, notifications, numbering, outbox

router = APIRouter(prefix="/admissions", tags=["Admissions"], dependencies=[Depends(require_feature("admissions"))])

TRANSITIONS = {
    "new": {"contacted", "counselling", "demo_class", "lost"},
    "contacted": {"counselling", "demo_class", "admission_offered", "lost"},
    "counselling": {"demo_class", "admission_offered", "contacted", "lost"},
    "demo_class": {"counselling", "admission_offered", "lost"},
    "admission_offered": {"counselling", "lost"},
    "lost": {"contacted"},
    "enrolled": set(),
}


class QuickEnquiryIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    guardian_name: str | None = Field(default=None, max_length=200)
    guardian_phone: str | None = Field(default=None, max_length=30)
    source: Literal[LEAD_SOURCES] = "walk_in"  # type: ignore[valid-type]
    campaign_id: uuid.UUID | None = None
    referred_by_student_id: uuid.UUID | None = None
    referral_name: str | None = Field(default=None, max_length=200)
    course_id: uuid.UUID | None = None
    preferred_batch_id: uuid.UUID | None = None
    interested_subjects: str | None = Field(default=None, max_length=500)
    enquiry_mode: Literal["walk_in", "online", "phone", "email"] = "walk_in"
    assigned_to_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


@router.post("/enquiries", status_code=201)
def quick_enquiry(body: QuickEnquiryIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.write"))):
    if not body.phone and not body.email:
        raise ValidationFailed("Provide a phone number or email")
    branch_id = body.branch_id or p.selected_branch_id or (next(iter(p.branch_ids)) if p.branch_ids and len(p.branch_ids) == 1 else None)
    if branch_id is None:
        from app.models import Branch

        branch_id = db.scalar(select(Branch.id).where(Branch.institute_id == p.institute_id, Branch.is_head_office.is_(True)))
    p.check_branch(branch_id)
    conds = []
    if body.phone:
        conds.append(Lead.phone == body.phone)
    if body.email:
        conds.append(func.lower(Lead.email) == body.email.lower())
    lead = db.scalar(select(Lead).where(Lead.institute_id == p.institute_id, or_(*conds)))
    reused = lead is not None
    if lead is None:
        lead = Lead(institute_id=p.institute_id, branch_id=branch_id, full_name=body.full_name, phone=body.phone, email=body.email,
                    guardian_name=body.guardian_name, guardian_phone=body.guardian_phone, source=body.source, campaign_id=body.campaign_id,
                    referred_by_student_id=body.referred_by_student_id, referral_name=body.referral_name,
                    assigned_to_id=body.assigned_to_id or p.user_id, notes=body.notes, created_by_id=p.user_id, updated_by_id=p.user_id)
        db.add(lead)
        db.flush()
    enq = Enquiry(institute_id=p.institute_id, branch_id=branch_id, lead_id=lead.id, contact_name=lead.full_name, course_id=body.course_id,
                  preferred_batch_id=body.preferred_batch_id, interested_subjects=body.interested_subjects, enquiry_mode=body.enquiry_mode,
                  stage="new", assigned_to_id=body.assigned_to_id or lead.assigned_to_id, next_follow_up_at=body.next_follow_up_at,
                  created_by_id=p.user_id, updated_by_id=p.user_id)
    db.add(enq)
    db.flush()
    if body.next_follow_up_at:
        db.add(FollowUp(institute_id=p.institute_id, enquiry_id=enq.id, due_at=body.next_follow_up_at, mode="call",
                        assigned_to_id=enq.assigned_to_id, created_by_id=p.user_id))
    audit.record(db, p, "enquiries", enq.id, "create", new={"lead_id": lead.id, "reused_lead": reused}, branch_id=branch_id)
    outbox.emit(db, p.institute_id, "admission.enquiry", "enquiry", enq.id, {"name": lead.full_name}, dedupe_key=f"enquiry:{enq.id}")
    db.commit()
    return {"enquiry_id": enq.id, "lead_id": lead.id, "existing_lead": reused}


@router.get("/pipeline")
def pipeline(course_id: uuid.UUID | None = None, assigned_to_id: uuid.UUID | None = None, q: str | None = Query(None, max_length=100),
             db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.read"))):
    base = select(Enquiry).where(Enquiry.institute_id == p.institute_id)
    if p.branch_ids is not None:
        base = base.where(Enquiry.branch_id.in_(p.branch_ids))
    if p.selected_branch_id:
        base = base.where(Enquiry.branch_id == p.selected_branch_id)
    if course_id:
        base = base.where(Enquiry.course_id == course_id)
    if assigned_to_id:
        base = base.where(Enquiry.assigned_to_id == assigned_to_id)
    if q:
        base = base.where(Enquiry.contact_name.ilike(f"%{q}%"))
    out = {}
    for stage in ENQUIRY_STAGES:
        rows = db.scalars(base.where(Enquiry.stage == stage).order_by(Enquiry.updated_at.desc()).limit(50)).all()
        count = db.scalar(select(func.count()).select_from(base.where(Enquiry.stage == stage).subquery()))
        leads = {l.id: l for l in db.scalars(select(Lead).where(Lead.id.in_([r.lead_id for r in rows] or [uuid.uuid4()])))}
        out[stage] = {"count": count, "items": [{"id": r.id, "contact_name": r.contact_name, "phone": leads[r.lead_id].phone if r.lead_id in leads else None,
                                                  "source": leads[r.lead_id].source if r.lead_id in leads else None, "course_id": r.course_id,
                                                  "next_follow_up_at": r.next_follow_up_at, "updated_at": r.updated_at, "lost_reason": r.lost_reason}
                                                 for r in rows]}
    return out


class StageIn(BaseModel):
    stage: Literal[ENQUIRY_STAGES]  # type: ignore[valid-type]
    lost_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)


@router.post("/enquiries/{eid}/stage")
def move_stage(eid: uuid.UUID, body: StageIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.write"))):
    e = get_tenant_obj(db, p, Enquiry, eid, lock=True, label="Enquiry")
    if body.stage == "enrolled":
        raise ValidationFailed("Use the convert action to enroll a student")
    if body.stage not in TRANSITIONS.get(e.stage, set()):
        raise Conflict(f"Cannot move from {e.stage} to {body.stage}")
    if body.stage == "lost" and not body.lost_reason:
        raise ValidationFailed("A lost reason is required")
    old = e.stage
    e.stage = body.stage
    e.lost_reason = body.lost_reason if body.stage == "lost" else None
    e.last_contacted_at = datetime.now(timezone.utc)
    if body.notes:
        if p.can("admissions.counselling") or body.stage == "counselling":
            e.counselling_notes = ((e.counselling_notes or "") + f"\n[{date.today():%d-%m-%Y}] {body.notes}").strip()
    audit.record(db, p, "enquiries", e.id, "stage_change", {"stage": old}, {"stage": body.stage}, body.lost_reason)
    db.commit()
    return {"stage": e.stage}


class OfferIn(BaseModel):
    offer_date: date
    offered_batch_id: uuid.UUID | None = None
    offered_fee_plan_id: uuid.UUID | None = None
    offer_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    admission_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    offer_valid_until: date | None = None
    remarks: str | None = None


@router.post("/enquiries/{eid}/offer")
def make_offer(eid: uuid.UUID, body: OfferIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.write"))):
    e = get_tenant_obj(db, p, Enquiry, eid, lock=True, label="Enquiry")
    if e.stage in ("enrolled", "lost"):
        raise Conflict("Enquiry is closed")
    rec = db.scalar(select(AdmissionRecord).where(AdmissionRecord.enquiry_id == e.id))
    if rec is None:
        rec = AdmissionRecord(institute_id=p.institute_id, branch_id=e.branch_id, enquiry_id=e.id, created_by_id=p.user_id)
        db.add(rec)
    for k, v in body.model_dump().items():
        setattr(rec, k, v)
    rec.status = "offered"
    rec.updated_by_id = p.user_id
    e.stage = "admission_offered"
    audit.record(db, p, "enquiries", e.id, "offer", new=body.model_dump())
    db.commit()
    return {"admission_record_id": rec.id}


class ConvertIn(BaseModel):
    batch_id: uuid.UUID
    admission_date: date
    student_code: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    address: str | None = None
    link_existing_student_id: uuid.UUID | None = None
    fee_plan_id: uuid.UUID | None = None
    billing_type: str | None = None
    agreement_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    admission_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    admission_fee_due_date: date | None = None


@router.post("/enquiries/{eid}/convert")
def convert(eid: uuid.UUID, body: ConvertIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.write", "students.write"))):
    p.require("students.write")
    e = get_tenant_obj(db, p, Enquiry, eid, lock=True, label="Enquiry")
    if e.stage == "enrolled" or e.student_id:
        raise Conflict("Enquiry is already converted")
    lead = db.get(Lead, e.lead_id)
    batch = get_tenant_obj(db, p, Batch, body.batch_id, label="Batch")
    active = db.scalar(select(func.count()).where(StudentEnrollment.batch_id == batch.id, StudentEnrollment.status == "active"))
    if batch.capacity and active >= batch.capacity:
        raise Conflict(f"Batch {batch.name} is full")
    if body.link_existing_student_id:
        student = get_tenant_obj(db, p, Student, body.link_existing_student_id, label="Student")
    else:
        conds = []
        if lead.phone:
            conds += [Student.phone == lead.phone, Student.guardian_phone == lead.phone]
        if lead.email:
            conds.append(func.lower(Student.email) == lead.email.lower())
        dups = db.scalars(select(Student).where(Student.institute_id == p.institute_id, or_(*conds))).all() if conds else []
        if dups:
            raise Conflict("Possible duplicate student found. Link the existing record or verify details.", code="duplicate_student",
                           details=[{"id": str(s.id), "full_name": s.full_name, "student_code": s.student_code, "phone": s.phone} for s in dups])
        student = Student(institute_id=p.institute_id, branch_id=batch.branch_id, full_name=lead.full_name, phone=lead.phone, email=lead.email,
                          guardian_name=lead.guardian_name, guardian_phone=lead.guardian_phone, date_of_birth=body.date_of_birth,
                          gender=body.gender, address=body.address, admission_date=body.admission_date, status="active",
                          student_code=body.student_code or numbering.next_code(db, p.institute_id, "student", "STU"),
                          created_by_id=p.user_id, updated_by_id=p.user_id)
        db.add(student)
        db.flush()
    if db.scalar(select(StudentEnrollment.id).where(StudentEnrollment.student_id == student.id, StudentEnrollment.batch_id == batch.id,
                                                    StudentEnrollment.status == "active")):
        raise Conflict("Student is already enrolled in this batch")
    enr = StudentEnrollment(institute_id=p.institute_id, branch_id=batch.branch_id, student_id=student.id, batch_id=batch.id,
                            course_id=batch.course_id, academic_year_id=batch.academic_year_id, start_date=body.admission_date,
                            status="active", remarks="Admission", created_by_id=p.user_id)
    db.add(enr)
    db.flush()
    rec = db.scalar(select(AdmissionRecord).where(AdmissionRecord.enquiry_id == e.id))
    if rec is None:
        rec = AdmissionRecord(institute_id=p.institute_id, branch_id=batch.branch_id, enquiry_id=e.id, offer_date=body.admission_date,
                              offered_batch_id=batch.id, created_by_id=p.user_id)
        db.add(rec)
    plan_id = body.fee_plan_id or rec.offered_fee_plan_id
    if plan_id:
        plan = get_tenant_obj(db, p, FeePlan, plan_id, label="Fee plan")
        db.add(StudentFeeAgreement(institute_id=p.institute_id, branch_id=batch.branch_id, student_id=student.id, fee_plan_id=plan.id,
                                   enrollment_id=enr.id, batch_id=batch.id, subject_id=plan.subject_id,
                                   billing_type=body.billing_type or plan.billing_type,
                                   amount=body.agreement_amount if body.agreement_amount is not None else (rec.offer_amount or plan.amount),
                                   currency=plan.currency, effective_from=body.admission_date, status="active",
                                   approved_by_id=p.user_id, created_by_id=p.user_id))
    adm_fee = body.admission_fee if body.admission_fee is not None else rec.admission_fee
    if adm_fee and adm_fee > 0:
        inv = finance.create_invoice(db, p.institute_id, student, [finance.build_item("Admission fee", adm_fee, item_type="admission")],
                                     body.admission_date, body.admission_fee_due_date or body.admission_date + timedelta(days=7), p.user_id,
                                     source="admission")
        rec.admission_fee_invoice_id = inv.id
    rec.student_id = student.id
    rec.status = "admitted"
    rec.admitted_at = datetime.now(timezone.utc)
    e.stage = "enrolled"
    e.student_id = student.id
    e.converted_at = datetime.now(timezone.utc)
    lead.student_id = student.id
    audit.record(db, p, "enquiries", e.id, "converted", new={"student_id": student.id, "batch_id": batch.id})
    audit.record(db, p, "students", student.id, "admitted", new={"enquiry_id": e.id, "batch_id": batch.id}, branch_id=student.branch_id)
    outbox.emit(db, p.institute_id, "admission.converted", "student", student.id, {"name": student.full_name}, dedupe_key=f"admission:{e.id}")
    db.commit()
    return {"student_id": student.id, "enrollment_id": enr.id, "admission_fee_invoice_id": rec.admission_fee_invoice_id}


class FollowUpDoneIn(BaseModel):
    outcome: str = Field(min_length=2, max_length=2000)
    next_follow_up_at: datetime | None = None
    status: Literal["done", "missed", "cancelled"] = "done"


@router.post("/follow-ups/{fid}/complete")
def complete_follow_up(fid: uuid.UUID, body: FollowUpDoneIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.write"))):
    f = get_tenant_obj(db, p, FollowUp, fid, lock=True, label="Follow-up")
    if f.status != "pending":
        raise Conflict("Follow-up already closed")
    f.status = body.status
    f.outcome = body.outcome
    f.completed_at = datetime.now(timezone.utc)
    e = db.get(Enquiry, f.enquiry_id)
    e.last_contacted_at = f.completed_at
    e.next_follow_up_at = body.next_follow_up_at
    if e.stage == "new" and body.status == "done":
        e.stage = "contacted"
    if body.next_follow_up_at:
        db.add(FollowUp(institute_id=p.institute_id, enquiry_id=e.id, due_at=body.next_follow_up_at, mode=f.mode,
                        assigned_to_id=f.assigned_to_id, created_by_id=p.user_id))
    audit.record(db, p, "follow_ups", f.id, "complete", new=body.model_dump())
    db.commit()
    return {"ok": True}


@router.get("/conversion")
def conversion(start: date | None = None, end: date | None = None, db: Session = Depends(get_db), p: Principal = Depends(require_perm("admissions.read"))):
    q = select(Lead.source, func.count(Enquiry.id), func.sum(case((Enquiry.stage == "enrolled", 1), else_=0)),
               func.sum(case((Enquiry.stage == "lost", 1), else_=0))).join(Lead, Lead.id == Enquiry.lead_id).where(Enquiry.institute_id == p.institute_id)
    if start:
        q = q.where(func.date(Enquiry.created_at) >= start)
    if end:
        q = q.where(func.date(Enquiry.created_at) <= end)
    if p.branch_ids is not None:
        q = q.where(Enquiry.branch_id.in_(p.branch_ids))
    by_source = [{"source": s, "enquiries": t, "enrolled": int(en or 0), "lost": int(lo or 0),
                  "conversion_percent": round((en or 0) * 100 / t, 1) if t else None} for s, t, en, lo in db.execute(q.group_by(Lead.source)).all()]
    cq = select(Campaign.name, func.count(Enquiry.id), func.sum(case((Enquiry.stage == "enrolled", 1), else_=0))).join(
        Lead, Lead.campaign_id == Campaign.id).join(Enquiry, Enquiry.lead_id == Lead.id).where(Campaign.institute_id == p.institute_id).group_by(Campaign.name)
    by_campaign = [{"campaign": n, "enquiries": t, "enrolled": int(en or 0), "conversion_percent": round((en or 0) * 100 / t, 1) if t else None}
                   for n, t, en in db.execute(cq).all()]
    lost = [{"reason": r or "Unspecified", "count": c} for r, c in db.execute(
        select(Enquiry.lost_reason, func.count()).where(Enquiry.institute_id == p.institute_id, Enquiry.stage == "lost").group_by(Enquiry.lost_reason)).all()]
    referrals = db.scalar(select(func.count()).where(Lead.institute_id == p.institute_id, Lead.source == "referral"))
    return {"by_source": by_source, "by_campaign": by_campaign, "lost_reasons": lost, "referral_leads": referrals}
