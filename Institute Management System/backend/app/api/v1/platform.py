import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.common import file_response, get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.api.v1.files import download_url
from app.core.errors import Conflict, Forbidden, IntegrationUnavailable, NotFound, ValidationFailed
from app.crud.engine import REGISTRY, base_query, read_mode
from app.db.session import get_db
from app.integrations import providers, registry
from app.models import AiRequest, BackgroundJob, Material, MaterialVersion, Question, Student, UsageRecord
from app.services import app_settings, audit, imports, storage
from app.services.audit import jsonable
from app.services.jobs import job_owner_ok

router = APIRouter(tags=["Platform"])
health_router = APIRouter(tags=["Health"])


@health_router.get("/health")
def health():
    return {"status": "ok"}


@health_router.get("/ready")
def ready(db: Session = Depends(get_db)):
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"
    try:
        from app.core.ratelimit import redis_client

        redis_client().ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "error"
    checks["object_storage"] = "ok" if storage.ping() else "error"
    ok = all(v == "ok" for v in checks.values())
    from fastapi.responses import JSONResponse

    return JSONResponse({"status": "ready" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)


# ----------------------------------------------------------------------------- global search

SEARCH_TARGETS = ["students", "teachers", "parents", "courses", "subjects", "batches", "class-sessions", "materials", "assignments",
                  "invoices", "payments", "leads", "enquiries"]


@router.get("/search")
def global_search(q: str = Query(min_length=2, max_length=100), db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    from app.crud.engine import apply_filters, check_feature

    results = []
    term = q.strip()
    for name in SEARCH_TARGETS:
        res = REGISTRY.get(name)
        if res is None:
            continue
        mode = read_mode(p, res)
        if mode is None:
            continue
        try:
            check_feature(db, p, res)
        except Exception:  # noqa: BLE001
            continue
        query = base_query(p, res, mode)
        if res.search:
            from sqlalchemy import or_

            query = query.where(or_(*[getattr(res.model, f).ilike(f"%{term}%") for f in res.search]))
        elif name == "class-sessions":
            try:
                d = datetime.strptime(term, "%d-%m-%Y").date()
            except ValueError:
                continue
            query = query.where(res.model.session_date == d)
        else:
            continue
        for row in db.scalars(query.limit(5)):
            title = getattr(row, res.title_field, None)
            results.append({"type": name, "label": res.label, "id": row.id, "title": str(title) if title is not None else str(row.id),
                            "subtitle": getattr(row, "student_code", None) or getattr(row, "code", None) or getattr(row, "status", None)})
    return {"query": term, "results": results}


# ----------------------------------------------------------------------------- import / export


@router.get("/imports/templates/{entity}")
def import_template(entity: str, p: Principal = Depends(require_perm("imports.read"))):
    return file_response(imports.template_csv(entity), f"{entity}-template.csv", "text/csv")


@router.post("/imports/{entity}/preview")
def import_preview(entity: str, file: UploadFile = File(...), db: Session = Depends(get_db), p: Principal = Depends(require_perm("imports.write"))):
    perm_module = {"students": "students", "teachers": "teachers", "courses": "courses", "subjects": "subjects", "batches": "batches",
                   "enrollments": "enrollments", "attendance": "attendance"}.get(entity)
    if not perm_module:
        raise ValidationFailed("Unknown import type")
    p.require(f"{perm_module}.write")
    data, filename, _ = storage.validate_and_read(file, allowed={"csv", "xlsx"}, max_mb=10)
    rows = imports.parse_file(filename, data)
    checked = imports.validate_rows(db, p, entity, rows)
    valid = sum(1 for r in checked if not r["errors"])
    job = BackgroundJob(institute_id=p.institute_id, job_type=f"import:{entity}", status="queued", created_by_id=p.user_id,
                        params={"entity": entity, "filename": filename}, result={"raw_rows": rows, "valid": valid, "invalid": len(checked) - valid})
    db.add(job)
    db.commit()
    return {"job_id": job.id, "entity": entity, "total": len(checked), "valid": valid, "invalid": len(checked) - valid,
            "rows": [{"row": r["row"], "errors": r["errors"], "data": jsonable({k: v for k, v in r["data"].items() if not k.startswith("_")})}
                     for r in checked[:500]]}


@router.post("/imports/{job_id}/commit")
def import_commit(job_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("imports.write"))):
    job = db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id, BackgroundJob.institute_id == p.institute_id).with_for_update())
    if job is None or not job.job_type.startswith("import:"):
        raise NotFound("Import not found")
    if job.status != "queued":
        raise Conflict("This import was already processed")
    entity = job.params["entity"]
    p.require(f"{entity}.write" if entity != "attendance" else "attendance.write")
    checked = imports.validate_rows(db, p, entity, job.result.get("raw_rows", []))
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    created = imports.commit_rows(db, p, entity, checked)
    skipped = sum(1 for r in checked if r["errors"])
    job.status = "succeeded"
    job.finished_at = datetime.now(timezone.utc)
    job.progress = 100
    job.result = {"created": created, "skipped": skipped, "errors": [{"row": r["row"], "errors": r["errors"]} for r in checked if r["errors"]][:500]}
    audit.record(db, p, "imports", job.id, "commit", new={"entity": entity, "created": created, "skipped": skipped})
    db.commit()
    return job.result


@router.get("/jobs/{job_id}/status")
def job_status(job_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    job = db.get(BackgroundJob, job_id)
    if job is None or not job_owner_ok(job, p):
        raise NotFound("Job not found")
    res = job.result or {}
    res = {k: v for k, v in res.items() if k != "raw_rows"}
    return {"id": job.id, "job_type": job.job_type, "status": job.status, "progress": job.progress, "error": job.error,
            "result": res, "has_file": bool(job.result_object_key), "created_at": job.created_at, "finished_at": job.finished_at}


@router.get("/jobs/{job_id}/download-link")
def job_download(job_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    job = db.get(BackgroundJob, job_id)
    if job is None or not job_owner_ok(job, p) or not job.result_object_key:
        raise NotFound("File not available")
    mime = {"csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}.get(
        (job.result_filename or "").rsplit(".", 1)[-1], "application/octet-stream")
    return {"url": download_url(p, job.result_object_key, job.result_filename or "export", mime, "job", job.id)}


# ----------------------------------------------------------------------------- AI (optional, disabled by default)

AI_SYSTEM = (
    "You are an assistant for an Indian coaching institute. Be accurate and concise. "
    "Never invent marks, attendance or records. If information is missing, say so."
)
STUDENT_DATA_FEATURES = {"progress_summary"}


class AiIn(BaseModel):
    feature: Literal["question_generation", "assignment_draft", "material_summary", "document_extraction", "progress_summary",
                     "learning_assistant", "knowledge_qa", "report_draft"]
    prompt: str = Field(min_length=3, max_length=8000)
    subject_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    count: int = Field(default=5, ge=1, le=20)


def _ai_cfg(db: Session, p: Principal):
    cfg = registry.get_active(db, p.institute_id, "ai")
    if cfg is None:
        raise IntegrationUnavailable("No AI provider is configured")
    limit = app_settings.get(db, p.institute_id, "ai.monthly_request_limit")
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(select(func.count()).where(AiRequest.institute_id == p.institute_id, AiRequest.created_at >= month_start))
    if limit and used >= limit:
        raise Conflict("Monthly AI request limit reached")
    return cfg


@router.post("/ai/generate", dependencies=[Depends(require_feature("ai"))])
def ai_generate(body: AiIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if not (p.can("ai.write") or p.can("ai.write_own")):
        raise Forbidden("AI assistant is not available for your role")
    if body.feature in ("question_generation", "assignment_draft", "report_draft", "document_extraction") and not (p.is_staff or p.teacher_id):
        raise Forbidden("This AI feature is for staff")
    cfg = _ai_cfg(db, p)
    context = ""
    if body.feature in ("material_summary", "document_extraction", "knowledge_qa") and body.material_id:
        res = REGISTRY["materials"]
        mode = read_mode(p, res)
        m = db.scalar(base_query(p, res, mode).where(Material.id == body.material_id)) if mode else None
        if m is None:
            raise NotFound("Material not found")
        v = db.scalars(select(MaterialVersion).where(MaterialVersion.material_id == m.id).order_by(MaterialVersion.version_number.desc()).limit(1)).first()
        if v is None or not v.mime_type.startswith("text/"):
            raise ValidationFailed("Only plain-text/CSV materials can be processed; other formats are not extracted by this deployment")
        context = storage.get_bytes(v.object_key)[:60000].decode("utf-8", errors="replace")
    if body.feature == "knowledge_qa" and not body.material_id:
        res = REGISTRY["materials"]
        mode = read_mode(p, res)
        titles = [f"- {m.title}: {m.description or ''}" for m in db.scalars(base_query(p, res, mode).limit(100))] if mode else []
        context = "Authorised institute materials:\n" + "\n".join(titles)
    if body.feature in STUDENT_DATA_FEATURES:
        if not app_settings.get(db, p.institute_id, "ai.allow_student_data"):
            raise Forbidden("Sharing student data with the AI provider is disabled by the administrator")
        if not body.student_id:
            raise ValidationFailed("student_id is required")
        from app.api.v1.people import student_profile

        prof = student_profile(body.student_id, db, p)
        context = (f"Attendance: {prof['attendance']['summary']}\nResults: "
                   f"{[{k: r[k] for k in ('exam', 'subject', 'percentage', 'grade')} for r in prof['results']][:20]}\n"
                   f"Homework: {[{k: h[k] for k in ('title', 'status', 'marks')} for h in prof['homework']][:20]}")
    instructions = {
        "question_generation": f"Generate {body.count} exam questions as a JSON array of objects with keys question_type (mcq_single|numerical|descriptive), "
                               "question_text, options [{key,text}], correct_answer (array), marks, difficulty, explanation. Output JSON only.",
        "assignment_draft": "Draft homework with title, instructions and marking guidance.",
        "material_summary": "Summarise the material for students in bullet points.",
        "document_extraction": "Extract the key structured facts as a table.",
        "progress_summary": "Write a factual academic progress summary based ONLY on the data provided, with suggestions for the teacher to review.",
        "learning_assistant": "Explain step by step for a student.",
        "knowledge_qa": "Answer using only the authorised materials listed; if not covered, say so.",
        "report_draft": "Draft an administrative report from the given notes.",
    }[body.feature]
    req = AiRequest(institute_id=p.institute_id, user_id=p.user_id, feature=body.feature, provider=cfg.provider, model=cfg.config.get("model"),
                    prompt=body.prompt[:8000], status="pending")
    db.add(req)
    db.flush()
    try:
        out = providers.ai_complete(cfg, AI_SYSTEM + " " + instructions, f"{context}\n\nRequest:\n{body.prompt}".strip())
    except providers.ProviderError as e:
        req.status, req.error = "failed", str(e)
        db.commit()
        raise IntegrationUnavailable(str(e))
    req.output = out["text"]
    req.prompt_tokens, req.completion_tokens = out["prompt_tokens"], out["completion_tokens"]
    cin = Decimal(str(cfg.config.get("input_cost_per_1k") or 0))
    cout = Decimal(str(cfg.config.get("output_cost_per_1k") or 0))
    req.cost = (Decimal(req.prompt_tokens) * cin + Decimal(req.completion_tokens) * cout) / 1000
    req.status = "completed"
    period = date.today().strftime("%Y-%m")
    usage = db.scalar(select(UsageRecord).where(UsageRecord.institute_id == p.institute_id, UsageRecord.metric == "ai_tokens", UsageRecord.period == period))
    if usage is None:
        usage = UsageRecord(institute_id=p.institute_id, metric="ai_tokens", period=period, quantity=0, cost=0)
        db.add(usage)
    usage.quantity = Decimal(usage.quantity or 0) + req.prompt_tokens + req.completion_tokens
    usage.cost = Decimal(usage.cost or 0) + req.cost
    created_questions = 0
    if body.feature == "question_generation" and body.subject_id:
        import json

        try:
            items = json.loads(req.output.strip().removeprefix("```json").removesuffix("```").strip())
            for it in items[: body.count]:
                qt = it.get("question_type") if it.get("question_type") in ("mcq_single", "numerical", "descriptive", "mcq_multi", "true_false", "fill_blank") else "descriptive"
                db.add(Question(institute_id=p.institute_id, subject_id=body.subject_id, question_type=qt,
                                difficulty=it.get("difficulty") if it.get("difficulty") in ("easy", "medium", "hard") else "medium",
                                question_text=str(it.get("question_text", ""))[:5000], options=it.get("options") or [],
                                correct_answer=it.get("correct_answer") or [], marks=Decimal(str(it.get("marks") or 1)),
                                explanation=it.get("explanation"), is_ai_generated=True, is_approved=False, created_by_id=p.user_id))
                created_questions += 1
        except (ValueError, TypeError, AttributeError):
            pass
    audit.record(db, p, "ai_requests", req.id, "generate", new={"feature": body.feature, "tokens": req.prompt_tokens + req.completion_tokens})
    db.commit()
    return {"id": req.id, "ai_generated": True, "output": req.output, "draft_questions_created": created_questions,
            "notice": "AI-generated content. Review before use; it is not an official record."}


class AiReviewIn(BaseModel):
    status: Literal["approved", "rejected"]


@router.post("/ai/requests/{rid}/review", dependencies=[Depends(require_feature("ai"))])
def ai_review(rid: uuid.UUID, body: AiReviewIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    r = get_tenant_obj(db, p, AiRequest, rid, lock=True, label="AI request")
    if not (p.is_staff or p.teacher_id):
        raise Forbidden("Only staff can review AI output")
    r.status = body.status
    r.reviewed_by_id = p.user_id
    r.reviewed_at = datetime.now(timezone.utc)
    audit.record(db, p, "ai_requests", r.id, f"ai_{body.status}")
    db.commit()
    return {"status": r.status}


@router.post("/questions/{qid}/approve", dependencies=[Depends(require_feature("examinations"))])
def approve_question(qid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    q = get_tenant_obj(db, p, Question, qid, lock=True, label="Question")
    if not (p.can("questions.write") or (p.can("questions.write_own") and q.created_by_id == p.user_id)):
        raise Forbidden("You cannot approve this question")
    q.is_approved = True
    audit.record(db, p, "questions", q.id, "approve")
    db.commit()
    return {"ok": True}
