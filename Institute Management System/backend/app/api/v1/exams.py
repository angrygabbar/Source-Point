import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.common import ensure_student_access, file_response, get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.db.session import get_db
from app.models import (
    ExamAttempt,
    ExamQuestion,
    ExamResponse,
    ExamResult,
    Examination,
    GradeScale,
    Institute,
    Question,
    ReEvaluationRequest,
    Student,
    StudentEnrollment,
    Subject,
)
from app.services import audit, notifications, outbox, pdf
from app.services.finance import q2

router = APIRouter(tags=["Examinations"])


def _exam(db: Session, p: Principal, eid: uuid.UUID, write: bool = False, lock: bool = False) -> Examination:
    e = get_tenant_obj(db, p, Examination, eid, lock=lock, label="Examination")
    if write:
        if not (p.can("exams.write") or (p.can("exams.write_own") and e.batch_id in p.batch_ids)):
            raise Forbidden("You cannot manage this examination")
    else:
        if not (p.can("exams.read") or e.batch_id in p.batch_ids):
            raise Forbidden("You cannot view this examination")
        if not (p.is_staff or p.teacher_id) and e.status == "draft":
            raise NotFound("Examination not found")
    return e


def _roster(db: Session, e: Examination) -> list[Student]:
    on = (e.scheduled_start.date() if e.scheduled_start else datetime.now(timezone.utc).date())
    return list(db.scalars(
        select(Student).join(StudentEnrollment, StudentEnrollment.student_id == Student.id).where(
            StudentEnrollment.batch_id == e.batch_id, StudentEnrollment.start_date <= on,
            or_(StudentEnrollment.end_date.is_(None), StudentEnrollment.end_date >= on)).order_by(Student.full_name).distinct()
    ).all())


# ----------------------------------------------------------------------------- composition


class AddQuestionsIn(BaseModel):
    question_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


@router.post("/examinations/{eid}/questions")
def add_questions(eid: uuid.UUID, body: AddQuestionsIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, write=True)
    if e.status not in ("draft", "scheduled"):
        raise Conflict("Questions can only be changed before the exam goes live")
    seq = (db.scalar(select(func.max(ExamQuestion.sequence)).where(ExamQuestion.examination_id == e.id)) or 0)
    added = 0
    for qid in body.question_ids:
        q = get_tenant_obj(db, p, Question, qid, label="Question")
        if not q.is_approved:
            raise ValidationFailed("Unapproved (e.g. AI-generated) questions must be approved before use")
        if db.scalar(select(ExamQuestion.id).where(ExamQuestion.examination_id == e.id, ExamQuestion.question_id == q.id)):
            continue
        seq += 1
        db.add(ExamQuestion(institute_id=p.institute_id, examination_id=e.id, question_id=q.id, sequence=seq))
        added += 1
    audit.record(db, p, "examinations", e.id, "questions_added", new={"count": added})
    db.commit()
    return {"added": added}


@router.delete("/examinations/{eid}/questions/{qid}", status_code=204)
def remove_question(eid: uuid.UUID, qid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, write=True)
    if e.status not in ("draft", "scheduled"):
        raise Conflict("Questions can only be changed before the exam goes live")
    db.execute(delete(ExamQuestion).where(ExamQuestion.examination_id == e.id, ExamQuestion.question_id == qid))
    db.commit()


@router.get("/examinations/{eid}/paper")
def exam_paper(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, write=True)
    rows = db.execute(select(ExamQuestion, Question).join(Question, Question.id == ExamQuestion.question_id)
                      .where(ExamQuestion.examination_id == e.id).order_by(ExamQuestion.sequence)).all()
    total = sum((eq.marks or q.marks) for eq, q in rows)
    return {"examination": audit.snapshot(e), "total_marks": total, "questions": [
        {"exam_question_id": eq.id, "question_id": q.id, "sequence": eq.sequence, "question_type": q.question_type, "difficulty": q.difficulty,
         "question_text": q.question_text, "options": q.options, "correct_answer": q.correct_answer, "marks": eq.marks or q.marks,
         "negative_marks": eq.negative_marks if eq.negative_marks is not None else q.negative_marks} for eq, q in rows]}


class ExamStatusIn(BaseModel):
    status: Literal["scheduled", "live", "completed", "cancelled"]


@router.post("/examinations/{eid}/status")
def exam_status(eid: uuid.UUID, body: ExamStatusIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, write=True, lock=True)
    allowed = {"draft": {"scheduled", "cancelled"}, "scheduled": {"live", "completed", "cancelled", "draft"},
               "live": {"completed"}, "completed": set(), "results_published": set(), "cancelled": set()}
    if body.status not in allowed.get(e.status, set()):
        raise Conflict(f"Cannot move from {e.status} to {body.status}")
    if body.status in ("scheduled", "live") and e.mode == "online":
        if not db.scalar(select(ExamQuestion.id).where(ExamQuestion.examination_id == e.id)):
            raise ValidationFailed("Add questions before scheduling an online exam")
        if not e.duration_minutes:
            raise ValidationFailed("Online exams require a duration")
    old = e.status
    e.status = body.status
    if body.status == "completed":
        _finalise_expired(db, e, force=True)
    audit.record(db, p, "examinations", e.id, "status_change", {"status": old}, {"status": body.status})
    db.commit()
    return {"status": e.status}


# ----------------------------------------------------------------------------- online attempts

OBJECTIVE = {"mcq_single", "mcq_multi", "true_false", "numerical", "fill_blank"}


def grade_answer(q: Question, answer: list[Any] | None) -> bool | None:
    if q.question_type == "descriptive":
        return None
    if not answer:
        return False
    correct = q.correct_answer or []
    try:
        if q.question_type in ("mcq_single", "true_false"):
            return len(answer) == 1 and str(answer[0]) in {str(c) for c in correct}
        if q.question_type == "mcq_multi":
            return {str(a) for a in answer} == {str(c) for c in correct}
        if q.question_type == "numerical":
            tol = float(q.numeric_tolerance or 0)
            return any(abs(float(answer[0]) - float(c)) <= tol for c in correct)
        if q.question_type == "fill_blank":
            return str(answer[0]).strip().lower() in {str(c).strip().lower() for c in correct}
    except (TypeError, ValueError):
        return False
    return False


def _attempt_payload(db: Session, e: Examination, att: ExamAttempt) -> dict:
    eqs = {eq.question_id: eq for eq in db.scalars(select(ExamQuestion).where(ExamQuestion.examination_id == e.id))}
    qs = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_(list(eqs) or [uuid.uuid4()])))}
    answers = {r.question_id: r for r in db.scalars(select(ExamResponse).where(ExamResponse.attempt_id == att.id))}
    out = []
    for qid in att.question_order:
        q = qs.get(uuid.UUID(qid))
        if q is None:
            continue
        opts = q.options or []
        order = (att.option_order or {}).get(qid)
        if order:
            by_key = {o.get("key"): o for o in opts}
            opts = [by_key[k] for k in order if k in by_key]
        resp = answers.get(q.id)
        out.append({"question_id": q.id, "question_type": q.question_type, "question_text": q.question_text, "options": opts,
                    "marks": eqs[q.id].marks or q.marks, "answer": resp.answer if resp else None,
                    **({"is_correct": resp.is_correct, "marks_awarded": resp.marks_awarded, "feedback": resp.feedback}
                       if resp and att.status == "graded" and e.status == "results_published" else {})})
    remaining = max(0, int((att.deadline_at - datetime.now(timezone.utc)).total_seconds())) if att.status == "in_progress" else 0
    return {"attempt_id": att.id, "status": att.status, "started_at": att.started_at, "deadline_at": att.deadline_at,
            "remaining_seconds": remaining, "questions": out, "exam": {"id": e.id, "name": e.name, "instructions": e.instructions,
                                                                     "negative_marking": e.negative_marking, "max_marks": e.max_marks}}


@router.post("/examinations/{eid}/attempt/start")
def start_attempt(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    if not p.student_id:
        raise Forbidden("Only students can attempt online exams")
    e = _exam(db, p, eid)
    if e.mode != "online" or e.status not in ("scheduled", "live"):
        raise Conflict("This exam is not open for online attempts")
    now = datetime.now(timezone.utc)
    if e.scheduled_start and now < e.scheduled_start:
        raise Conflict("The exam has not started yet")
    if e.scheduled_end and now > e.scheduled_end:
        raise Conflict("The exam window has closed")
    if p.student_id not in {s.id for s in _roster(db, e)}:
        raise Forbidden("You are not enrolled for this exam")
    att = db.scalar(select(ExamAttempt).where(ExamAttempt.examination_id == e.id, ExamAttempt.student_id == p.student_id))
    if att is None:
        qids = [str(x) for x in db.scalars(select(ExamQuestion.question_id).where(ExamQuestion.examination_id == e.id).order_by(ExamQuestion.sequence))]
        rng = random.SystemRandom()
        if e.randomize_questions:
            rng.shuffle(qids)
        option_order = {}
        if e.randomize_options:
            for q in db.scalars(select(Question).where(Question.id.in_([uuid.UUID(x) for x in qids] or [uuid.uuid4()]))):
                keys = [o.get("key") for o in (q.options or []) if isinstance(o, dict)]
                if keys:
                    rng.shuffle(keys)
                    option_order[str(q.id)] = keys
        deadline = now + timedelta(minutes=e.duration_minutes or 60)
        if e.scheduled_end:
            deadline = min(deadline, e.scheduled_end)
        att = ExamAttempt(institute_id=p.institute_id, examination_id=e.id, student_id=p.student_id, started_at=now, deadline_at=deadline,
                          status="in_progress", question_order=qids, option_order=option_order)
        db.add(att)
        if e.status == "scheduled":
            e.status = "live"
        db.commit()
    return _attempt_payload(db, e, att)


@router.get("/examinations/{eid}/attempt")
def get_attempt(eid: uuid.UUID, student_id: uuid.UUID | None = None, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid)
    sid = student_id if student_id and (p.is_staff or p.teacher_id or student_id in p.linked_student_ids) else p.student_id
    att = db.scalar(select(ExamAttempt).where(ExamAttempt.examination_id == e.id, ExamAttempt.student_id == sid))
    if att is None:
        raise NotFound("No attempt found")
    return _attempt_payload(db, e, att)


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    answer: list[Any] = Field(max_length=20)


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(max_length=500)


@router.put("/examinations/{eid}/attempt/answers")
def save_answers(eid: uuid.UUID, body: AnswersIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    if not p.student_id:
        raise Forbidden("Only students can answer")
    att = db.scalar(select(ExamAttempt).where(ExamAttempt.examination_id == eid, ExamAttempt.student_id == p.student_id,
                                              ExamAttempt.institute_id == p.institute_id).with_for_update())
    if att is None or att.status != "in_progress":
        raise Conflict("No active attempt")
    if datetime.now(timezone.utc) > att.deadline_at + timedelta(seconds=15):
        raise Conflict("Time is over; the attempt will be submitted automatically")
    allowed = set(att.question_order)
    for a in body.answers:
        if str(a.question_id) not in allowed:
            raise ValidationFailed("Question is not part of this exam")
        r = db.scalar(select(ExamResponse).where(ExamResponse.attempt_id == att.id, ExamResponse.question_id == a.question_id))
        if r is None:
            r = ExamResponse(institute_id=p.institute_id, attempt_id=att.id, question_id=a.question_id)
            db.add(r)
        r.answer = [str(x)[:2000] for x in a.answer]
    db.commit()
    return {"saved": len(body.answers)}


def _grade_attempt(db: Session, e: Examination, att: ExamAttempt, auto: bool) -> None:
    eqs = {eq.question_id: eq for eq in db.scalars(select(ExamQuestion).where(ExamQuestion.examination_id == e.id))}
    qs = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_(list(eqs) or [uuid.uuid4()])))}
    responses = {r.question_id: r for r in db.scalars(select(ExamResponse).where(ExamResponse.attempt_id == att.id))}
    score = Decimal("0")
    manual = False
    for qid, eq in eqs.items():
        q = qs[qid]
        r = responses.get(qid)
        if r is None:
            r = ExamResponse(institute_id=att.institute_id, attempt_id=att.id, question_id=qid, answer=[])
            db.add(r)
        result = grade_answer(q, r.answer)
        marks = Decimal(eq.marks or q.marks)
        neg = Decimal(eq.negative_marks if eq.negative_marks is not None else q.negative_marks or 0)
        if result is None:
            r.needs_manual_grading = bool(r.answer)
            r.marks_awarded = None if r.answer else Decimal("0")
            manual = manual or bool(r.answer)
        else:
            r.is_correct = result
            r.marks_awarded = marks if result else (-neg if (e.negative_marking and r.answer) else Decimal("0"))
            score += r.marks_awarded
    att.objective_score = q2(score)
    att.submitted_at = att.submitted_at or datetime.now(timezone.utc)
    att.status = "submitted" if manual else "graded"
    if auto and manual:
        att.status = "auto_submitted"
    _sync_result_from_attempt(db, e, att)


def _sync_result_from_attempt(db: Session, e: Examination, att: ExamAttempt) -> None:
    total = db.scalar(select(func.coalesce(func.sum(ExamResponse.marks_awarded), 0)).where(ExamResponse.attempt_id == att.id))
    pending = db.scalar(select(func.count()).where(ExamResponse.attempt_id == att.id, ExamResponse.needs_manual_grading.is_(True),
                                                   ExamResponse.marks_awarded.is_(None)))
    res = db.scalar(select(ExamResult).where(ExamResult.examination_id == e.id, ExamResult.student_id == att.student_id))
    if res is None:
        res = ExamResult(institute_id=e.institute_id, examination_id=e.id, student_id=att.student_id, max_marks=e.max_marks, status="draft")
        db.add(res)
    if res.status != "draft":
        return
    res.marks_obtained = max(q2(total), Decimal("0"))
    res.remarks = "Awaiting manual grading of descriptive answers" if pending else None
    if pending == 0 and att.status in ("submitted", "auto_submitted"):
        att.status = "graded"


def _finalise_expired(db: Session, e: Examination, force: bool = False) -> int:
    now = datetime.now(timezone.utc)
    q = select(ExamAttempt).where(ExamAttempt.examination_id == e.id, ExamAttempt.status == "in_progress")
    if not force:
        q = q.where(ExamAttempt.deadline_at < now)
    n = 0
    for att in db.scalars(q.with_for_update()):
        att.submitted_at = min(now, att.deadline_at)
        _grade_attempt(db, e, att, auto=True)
        n += 1
    return n


def finalise_all_expired(db: Session) -> int:
    n = 0
    for e in db.scalars(select(Examination).where(Examination.mode == "online", Examination.status.in_(("scheduled", "live")))):
        n += _finalise_expired(db, e)
    return n


@router.post("/examinations/{eid}/attempt/submit")
def submit_attempt(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    if not p.student_id:
        raise Forbidden("Only students can submit")
    e = _exam(db, p, eid)
    att = db.scalar(select(ExamAttempt).where(ExamAttempt.examination_id == e.id, ExamAttempt.student_id == p.student_id).with_for_update())
    if att is None or att.status != "in_progress":
        raise Conflict("No active attempt")
    _grade_attempt(db, e, att, auto=False)
    audit.record(db, p, "exam_attempts", att.id, "submit")
    db.commit()
    return {"status": att.status, "message": "Submitted. Results will be visible after teacher review and publication."}


@router.get("/examinations/{eid}/manual-grading")
def manual_queue(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, write=True)
    rows = db.execute(
        select(ExamResponse, Question, Student.full_name).join(ExamAttempt, ExamAttempt.id == ExamResponse.attempt_id)
        .join(Question, Question.id == ExamResponse.question_id).join(Student, Student.id == ExamAttempt.student_id)
        .where(ExamAttempt.examination_id == e.id, ExamResponse.needs_manual_grading.is_(True)).order_by(Student.full_name)
    ).all()
    return [{"response_id": r.id, "student": n, "question_text": q.question_text, "answer": r.answer, "max_marks": q.marks,
             "marks_awarded": r.marks_awarded, "feedback": r.feedback} for r, q, n in rows]


class ResponseGradeIn(BaseModel):
    marks: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    feedback: str | None = Field(default=None, max_length=5000)


@router.post("/exam-responses/{rid}/grade")
def grade_response(rid: uuid.UUID, body: ResponseGradeIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    r = get_tenant_obj(db, p, ExamResponse, rid, lock=True, label="Response")
    att = db.get(ExamAttempt, r.attempt_id)
    e = _exam(db, p, att.examination_id, write=True)
    q = db.get(Question, r.question_id)
    eq = db.scalar(select(ExamQuestion).where(ExamQuestion.examination_id == e.id, ExamQuestion.question_id == q.id))
    limit = Decimal(eq.marks or q.marks) if eq else Decimal(q.marks)
    if body.marks > limit:
        raise ValidationFailed(f"Marks cannot exceed {limit}")
    res = db.scalar(select(ExamResult).where(ExamResult.examination_id == e.id, ExamResult.student_id == att.student_id))
    if res and res.status != "draft" and not p.can("grades.modify"):
        raise Forbidden("Results are approved; modification requires grade-modification permission")
    old = r.marks_awarded
    r.marks_awarded = body.marks
    r.feedback = body.feedback
    r.graded_by_id = p.user_id
    if res and res.status != "draft":
        res.status = "draft"
    _sync_result_from_attempt(db, e, att)
    audit.record(db, p, "exam_responses", r.id, "manual_grade", {"marks": old}, {"marks": body.marks})
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- results


@router.get("/examinations/{eid}/results")
def exam_results(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid)
    staff = p.can("results.read") or (p.teacher_id and e.batch_id in p.batch_ids)
    results = {r.student_id: r for r in db.scalars(select(ExamResult).where(ExamResult.examination_id == e.id))}
    rows = []
    for st in _roster(db, e):
        if not staff and st.id not in p.linked_student_ids:
            continue
        r = results.get(st.id)
        if r and not staff and r.status != "published":
            r = None
        rows.append({"student_id": st.id, "student_code": st.student_code, "full_name": st.full_name,
                     **({k: getattr(r, k) for k in ("id", "marks_obtained", "percentage", "grade", "rank", "is_absent", "remarks",
                                                    "remedial_recommendation", "status")} if r else {"status": None})})
    return {"examination": {"id": e.id, "name": e.name, "max_marks": e.max_marks, "pass_marks": e.pass_marks, "status": e.status,
                            "mode": e.mode}, "rows": rows, "can_edit": bool(staff and (p.can("results.write") or p.can("results.write_own")))}


class MarkRow(BaseModel):
    student_id: uuid.UUID
    marks_obtained: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=2)
    is_absent: bool = False
    remarks: str | None = Field(default=None, max_length=1000)
    remedial_recommendation: str | None = Field(default=None, max_length=1000)


class MarksIn(BaseModel):
    rows: list[MarkRow] = Field(max_length=1000)
    reason: str | None = Field(default=None, max_length=1000)


@router.put("/examinations/{eid}/marks")
def enter_marks(eid: uuid.UUID, body: MarksIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, lock=True)
    if not (p.can("results.write") or (p.can("results.write_own") and e.batch_id in p.batch_ids)):
        raise Forbidden("You cannot enter marks for this examination")
    if e.status in ("draft", "cancelled"):
        raise Conflict("Schedule the examination before entering marks")
    roster = {s.id for s in _roster(db, e)}
    for row in body.rows:
        if row.student_id not in roster:
            raise ValidationFailed("Student is not part of this examination's batch")
        if row.marks_obtained is not None and row.marks_obtained > e.max_marks:
            raise ValidationFailed(f"Marks cannot exceed {e.max_marks}")
        r = db.scalar(select(ExamResult).where(ExamResult.examination_id == e.id, ExamResult.student_id == row.student_id).with_for_update())
        if r is None:
            r = ExamResult(institute_id=p.institute_id, examination_id=e.id, student_id=row.student_id, max_marks=e.max_marks, status="draft",
                           created_by_id=p.user_id)
            db.add(r)
        elif r.status != "draft":
            if not p.can("grades.modify"):
                raise Forbidden("Results are approved/published; modification requires grade-modification permission")
            if not body.reason:
                raise ValidationFailed("A reason is required to modify approved results")
            audit.record(db, p, "exam_results", r.id, "modify_after_approval", {"marks": r.marks_obtained}, {"marks": row.marks_obtained}, body.reason)
            r.status = "draft"
        r.marks_obtained = None if row.is_absent else row.marks_obtained
        r.is_absent = row.is_absent
        r.remarks = row.remarks
        r.remedial_recommendation = row.remedial_recommendation
        r.updated_by_id = p.user_id
    audit.record(db, p, "examinations", e.id, "marks_entered", new={"rows": len(body.rows)})
    db.commit()
    return {"ok": True}


def _grade_for(bands: list[dict], pct: Decimal) -> str | None:
    for b in bands or []:
        try:
            if Decimal(str(b["min"])) <= pct <= Decimal(str(b["max"])):
                return str(b["grade"])
        except (KeyError, ValueError, ArithmeticError):
            continue
    return None


def compute_results(db: Session, e: Examination) -> int:
    scale = db.get(GradeScale, e.grade_scale_id) if e.grade_scale_id else db.scalar(
        select(GradeScale).where(GradeScale.institute_id == e.institute_id, GradeScale.is_default.is_(True)))
    results = db.scalars(select(ExamResult).where(ExamResult.examination_id == e.id)).all()
    for r in results:
        if r.is_absent or r.marks_obtained is None:
            r.percentage, r.grade = None, ("AB" if r.is_absent else None)
            continue
        r.max_marks = e.max_marks
        r.percentage = q2(Decimal(r.marks_obtained) * 100 / Decimal(e.max_marks))
        r.grade = _grade_for(scale.bands if scale else [], r.percentage)
        if e.pass_marks is not None and r.marks_obtained < e.pass_marks and not r.remedial_recommendation:
            r.remedial_recommendation = "Suggested: remedial support (below pass marks) — pending teacher review"
    ranked = sorted([r for r in results if r.marks_obtained is not None and not r.is_absent], key=lambda r: r.marks_obtained, reverse=True)
    prev, rank = None, 0
    for i, r in enumerate(ranked, start=1):
        if r.marks_obtained != prev:
            rank = i
            prev = r.marks_obtained
        r.rank = rank
    return len(results)


@router.post("/examinations/{eid}/compute")
def compute(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    e = _exam(db, p, eid, lock=True)
    if not (p.can("results.write") or (p.can("results.write_own") and e.batch_id in p.batch_ids)):
        raise Forbidden("You cannot compute results")
    n = compute_results(db, e)
    db.commit()
    return {"computed": n}


@router.post("/examinations/{eid}/approve")
def approve_results(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("results.approve"))):
    e = _exam(db, p, eid, lock=True)
    pending = db.scalar(select(func.count()).select_from(ExamResponse).join(ExamAttempt, ExamAttempt.id == ExamResponse.attempt_id)
                        .where(ExamAttempt.examination_id == e.id, ExamResponse.needs_manual_grading.is_(True), ExamResponse.marks_awarded.is_(None)))
    if pending:
        raise Conflict(f"{pending} descriptive answer(s) still need manual grading")
    compute_results(db, e)
    n = 0
    for r in db.scalars(select(ExamResult).where(ExamResult.examination_id == e.id, ExamResult.status == "draft")):
        r.status = "approved"
        r.approved_by_id = p.user_id
        n += 1
    e.results_approved_by_id = p.user_id
    e.results_approved_at = datetime.now(timezone.utc)
    audit.record(db, p, "examinations", e.id, "results_approved", new={"results": n})
    db.commit()
    return {"approved": n}


@router.post("/examinations/{eid}/publish")
def publish_results(eid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("results.approve"))):
    e = _exam(db, p, eid, lock=True)
    if db.scalar(select(func.count()).where(ExamResult.examination_id == e.id, ExamResult.status == "draft")):
        raise Conflict("Approve all results before publishing")
    n = 0
    for r in db.scalars(select(ExamResult).where(ExamResult.examination_id == e.id, ExamResult.status == "approved")):
        r.status = "published"
        n += 1
    e.status = "results_published"
    audit.record(db, p, "examinations", e.id, "results_published", new={"results": n})
    outbox.emit(db, p.institute_id, "exam.results_published", "examination", e.id, {"name": e.name}, dedupe_key=f"exam.results:{e.id}")
    db.commit()
    return {"published": n}


class ReEvalIn(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


@router.post("/exam-results/{rid}/re-evaluation", status_code=201)
def request_reevaluation(rid: uuid.UUID, body: ReEvalIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    r = get_tenant_obj(db, p, ExamResult, rid, label="Result")
    if r.student_id not in p.linked_student_ids and not p.can("results.write"):
        raise Forbidden("You can only request re-evaluation for your own results")
    if r.status != "published":
        raise Conflict("Re-evaluation is possible only for published results")
    if db.scalar(select(ReEvaluationRequest.id).where(ReEvaluationRequest.exam_result_id == r.id, ReEvaluationRequest.status.in_(("pending", "accepted")))):
        raise Conflict("A re-evaluation request is already open")
    req = ReEvaluationRequest(institute_id=p.institute_id, exam_result_id=r.id, student_id=r.student_id, reason=body.reason,
                              old_marks=r.marks_obtained, requested_by_id=p.user_id)
    db.add(req)
    db.flush()
    notifications.notify(db, p.institute_id, notifications.staff_user_ids(db, p.institute_id, ("institute_admin", "academic_coordinator")),
                         "system", "Re-evaluation requested", body.reason[:200], link="/r/re-evaluation-requests", dedupe_key=f"reeval:{req.id}")
    db.commit()
    return {"id": req.id}


class ReEvalDecisionIn(BaseModel):
    status: Literal["accepted", "rejected", "completed"]
    new_marks: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=2)
    remarks: str | None = Field(default=None, max_length=2000)


@router.post("/re-evaluation-requests/{rid}/decide")
def decide_reevaluation(rid: uuid.UUID, body: ReEvalDecisionIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("results.approve"))):
    req = get_tenant_obj(db, p, ReEvaluationRequest, rid, lock=True, label="Request")
    if req.status in ("rejected", "completed"):
        raise Conflict("Request already closed")
    req.status = body.status
    req.reviewer_id = p.user_id
    req.reviewed_at = datetime.now(timezone.utc)
    req.remarks = body.remarks
    if body.status == "completed" and body.new_marks is not None:
        r = db.scalar(select(ExamResult).where(ExamResult.id == req.exam_result_id).with_for_update())
        e = db.get(Examination, r.examination_id)
        if body.new_marks > e.max_marks:
            raise ValidationFailed(f"Marks cannot exceed {e.max_marks}")
        req.new_marks = body.new_marks
        audit.record(db, p, "exam_results", r.id, "re_evaluation", {"marks": r.marks_obtained}, {"marks": body.new_marks}, body.remarks)
        r.marks_obtained = body.new_marks
        compute_results(db, e)
    st = db.get(Student, req.student_id)
    notifications.notify(db, p.institute_id, notifications.student_and_parent_user_ids(db, [st.id]), "exam_results",
                         f"Re-evaluation {body.status}", body.remarks or "", dedupe_key=f"reeval:{req.id}:{body.status}")
    db.commit()
    return {"ok": True}


@router.get("/students/{student_id}/marksheet.pdf")
def marksheet(student_id: uuid.UUID, examination_id: uuid.UUID | None = None, academic_year_id: uuid.UUID | None = None,
              db: Session = Depends(get_db), p: Principal = Depends(require_feature("examinations"))):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    ensure_student_access(db, p, s)
    q = (select(ExamResult, Examination, Subject.name).join(Examination, Examination.id == ExamResult.examination_id)
         .join(Subject, Subject.id == Examination.subject_id).where(ExamResult.student_id == s.id))
    if examination_id:
        q = q.where(Examination.id == examination_id)
    if academic_year_id:
        q = q.where(Examination.academic_year_id == academic_year_id)
    if not p.can("results.read"):
        q = q.where(ExamResult.status == "published")
    rows = [[e.name, sn, e.scheduled_start.strftime("%d-%m-%Y") if e.scheduled_start else "—",
             "AB" if r.is_absent else (r.marks_obtained if r.marks_obtained is not None else "—"), r.max_marks, r.percentage or "—",
             r.grade or "—", r.rank or "—"] for r, e, sn in db.execute(q.order_by(Examination.scheduled_start)).all()]
    if not rows:
        raise NotFound("No results available")
    inst = db.get(Institute, p.institute_id)
    return file_response(pdf.marksheet_pdf(inst, s, rows), f"marksheet-{s.student_code}.pdf", "application/pdf", inline=True)


@router.get("/students/{student_id}/report-card.pdf")
def report_card(student_id: uuid.UUID, academic_year_id: uuid.UUID | None = None, db: Session = Depends(get_db),
                p: Principal = Depends(require_feature("examinations"))):
    from app.api.v1.people import attendance_summary

    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    ensure_student_access(db, p, s)
    q = (select(Subject.name, func.avg(ExamResult.percentage), func.count(), func.min(ExamResult.rank))
         .join(Examination, Examination.id == ExamResult.examination_id).join(Subject, Subject.id == Examination.subject_id)
         .where(ExamResult.student_id == s.id, ExamResult.status == "published").group_by(Subject.name))
    if academic_year_id:
        q = q.where(Examination.academic_year_id == academic_year_id)
    rows = [["All exams", n, "—", "—", "—", round(float(avg or 0), 1), "—", best or "—"] for n, avg, cnt, best in db.execute(q).all()]
    if not rows:
        raise NotFound("No published results available")
    att = attendance_summary(db, s.id)
    inst = db.get(Institute, p.institute_id)
    remarks = f"Attendance: {att['percentage'] if att['percentage'] is not None else '—'}% across {att['total_sessions']} sessions."
    return file_response(pdf.marksheet_pdf(inst, s, rows, title="REPORT CARD", remarks=remarks), f"report-card-{s.student_code}.pdf",
                         "application/pdf", inline=True)
