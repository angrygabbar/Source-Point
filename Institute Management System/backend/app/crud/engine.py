"""Generic, permission-aware CRUD engine shared by all reference/master-data resources.

Workflow operations with business rules (attendance submission, payments, grading …) live in
dedicated routers; this engine provides consistent list/filter/sort/paginate/export/audit
behaviour and tenant/branch/ownership scoping for every registered resource.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, create_model
from sqlalchemy import Boolean, Date, DateTime, Integer, BigInteger, Numeric, String, Text, Time, Enum as SAEnum, and_, false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.config import settings
from app.core.errors import Conflict, Forbidden, ModuleDisabled, NotFound, ValidationFailed
from app.db.session import get_db
from app.models import Base, StudentEnrollment
from app.services import audit, exporter, feature_flags

SYSTEM_FIELDS = {"id", "institute_id", "created_at", "updated_at", "created_by_id", "updated_by_id", "is_archived", "archived_at"}

# table name -> mapped class
TABLE_MODELS: dict[str, type] = {m.class_.__tablename__: m.class_ for m in Base.registry.mappers}


@dataclass
class Resource:
    name: str
    model: type
    perm: str
    label: str
    group: str = "General"
    feature: str | None = None
    title_field: str = "name"
    search: tuple[str, ...] = ()
    owner: dict[str, str] = field(default_factory=dict)  # keys: student, teacher, batch, user, student_via_batch
    own_filter: Callable[[Principal, type], Any] | None = None
    own_write: bool = False
    readonly: tuple[str, ...] = ()
    create_only: tuple[str, ...] = ()
    allow_create: bool = True
    allow_update: bool = True
    allow_delete: bool = True
    delete_perm: str | None = None
    default_sort: str = "-created_at"
    validate: Callable[[Session, Principal, Any, dict, bool], None] | None = None
    after_save: Callable[[Session, Principal, Any, bool], None] | None = None
    list_columns: tuple[str, ...] = ()
    hidden_fields: tuple[str, ...] = ()
    auto_fields: tuple[str, ...] = ()  # optional on create; filled by validate hook
    scope_filter: Callable[[Principal, type], Any] | None = None  # always-applied row filter

    @property
    def table(self):
        return self.model.__table__

    @property
    def has_archive(self) -> bool:
        return "is_archived" in self.table.c

    @property
    def is_tenant(self) -> bool:
        return "institute_id" in self.table.c

    @property
    def has_branch(self) -> bool:
        return "branch_id" in self.table.c


REGISTRY: dict[str, Resource] = {}
TABLE_TO_RESOURCE: dict[str, Resource] = {}
TITLE_FIELDS: dict[str, str] = {"users": "full_name"}


def register(res: Resource) -> Resource:
    REGISTRY[res.name] = res
    TABLE_TO_RESOURCE.setdefault(res.table.name, res)
    TITLE_FIELDS.setdefault(res.table.name, res.title_field)
    return res


# ----------------------------------------------------------------------------- type mapping


def column_kind(col) -> str:
    t = col.type
    if isinstance(t, SAEnum):
        return "enum"
    if isinstance(t, PGUUID):
        return "ref" if col.foreign_keys else "uuid"
    if isinstance(t, Boolean):
        return "boolean"
    if isinstance(t, DateTime):
        return "datetime"
    if isinstance(t, Date):
        return "date"
    if isinstance(t, Time):
        return "time"
    if isinstance(t, (Integer, BigInteger)):
        return "integer"
    if isinstance(t, Numeric):
        return "money" if col.info.get("widget") == "money" else "decimal"
    if isinstance(t, JSONB):
        return "json"
    if isinstance(t, Text):
        return "text"
    if isinstance(t, String):
        return "string"
    return "string"


def python_type(col) -> Any:
    kind = column_kind(col)
    if kind == "enum":
        return Literal[tuple(col.type.enums)]  # type: ignore[valid-type]
    if kind in ("ref", "uuid"):
        return uuid.UUID
    if kind == "boolean":
        return bool
    if kind == "datetime":
        return datetime
    if kind == "date":
        return date
    if kind == "integer":
        return int
    if kind in ("money", "decimal"):
        return Annotated[Decimal, Field(max_digits=col.type.precision, decimal_places=col.type.scale)]
    if kind == "json":
        return Any
    if kind == "string":
        if col.name.endswith("email"):
            return EmailStr
        return Annotated[str, Field(max_length=col.type.length)] if col.type.length else str
    return str


def coerce(col, raw: str) -> Any:
    kind = column_kind(col)
    try:
        if kind in ("ref", "uuid"):
            return uuid.UUID(raw)
        if kind == "boolean":
            return raw.lower() in ("1", "true", "yes", "on")
        if kind == "date":
            return date.fromisoformat(raw)
        if kind == "datetime":
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if kind == "integer":
            return int(raw)
        if kind in ("money", "decimal"):
            return Decimal(raw)
    except (ValueError, InvalidOperation):
        raise ValidationFailed(f"Invalid value for filter '{col.name}'")
    return raw


def writable_columns(res: Resource, creating: bool):
    for col in res.table.columns:
        if col.name in SYSTEM_FIELDS or col.info.get("hidden") or col.name in res.readonly or col.name in res.hidden_fields:
            continue
        if not creating and col.name in res.create_only:
            continue
        yield col


_schema_cache: dict[tuple[str, str], type[BaseModel]] = {}


def create_schema(res: Resource) -> type[BaseModel]:
    key = (res.name, "create")
    if key not in _schema_cache:
        fields: dict[str, Any] = {}
        for col in writable_columns(res, True):
            py = python_type(col)
            has_default = col.default is not None or col.server_default is not None
            if not col.nullable and not has_default and col.name != "branch_id" and col.name not in res.auto_fields:
                fields[col.name] = (py, ...)
            elif col.nullable:
                fields[col.name] = (Optional[py], None)
            else:
                fields[col.name] = (py, None)
        _schema_cache[key] = create_model(
            f"{res.model.__name__}Create", __config__=ConfigDict(extra="forbid", str_strip_whitespace=True), **fields
        )
    return _schema_cache[key]


def update_schema(res: Resource) -> type[BaseModel]:
    key = (res.name, "update")
    if key not in _schema_cache:
        fields: dict[str, Any] = {}
        for col in writable_columns(res, False):
            py = python_type(col)
            fields[col.name] = (Optional[py], None) if col.nullable else (py, None)
        fields["change_reason"] = (Optional[Annotated[str, Field(max_length=500)]], None)
        _schema_cache[key] = create_model(
            f"{res.model.__name__}Update", __config__=ConfigDict(extra="forbid", str_strip_whitespace=True), **fields
        )
    return _schema_cache[key]


def read_schema(res: Resource) -> type[BaseModel]:
    key = (res.name, "read")
    if key not in _schema_cache:
        fields: dict[str, Any] = {}
        for col in res.table.columns:
            if col.info.get("hidden"):
                continue
            kind = column_kind(col)
            py: Any = str if kind == "enum" else python_type(col)
            if kind == "string" and col.name.endswith("email"):
                py = str
            fields[col.name] = (Optional[py], None)
        fields["display"] = (Optional[dict[str, Optional[str]]], None)
        _schema_cache[key] = create_model(f"{res.model.__name__}Read", __config__=ConfigDict(extra="allow"), **fields)
    return _schema_cache[key]


def page_schema(res: Resource) -> type[BaseModel]:
    key = (res.name, "page")
    if key not in _schema_cache:
        _schema_cache[key] = create_model(
            f"{res.model.__name__}Page",
            items=(list[read_schema(res)], ...),  # type: ignore[valid-type]
            total=(int, ...),
            page=(int, ...),
            page_size=(int, ...),
        )
    return _schema_cache[key]


# ----------------------------------------------------------------------------- scoping


def read_mode(p: Principal, res: Resource) -> str | None:
    if p.can(f"{res.perm}.read"):
        return "all"
    if p.can(f"{res.perm}.read_own") and (res.owner or res.own_filter):
        return "own"
    return None


def write_mode(p: Principal, res: Resource) -> str | None:
    if p.can(f"{res.perm}.write"):
        return "all"
    if res.own_write and p.can(f"{res.perm}.write_own"):
        return "own"
    return None


def enrolled_students_subquery(batch_ids):
    return select(StudentEnrollment.student_id).where(
        StudentEnrollment.batch_id.in_(batch_ids), StudentEnrollment.status == "active"
    )


def owner_condition(p: Principal, res: Resource):
    M = res.model
    if res.own_filter is not None:
        return res.own_filter(p, M)
    o = res.owner
    conds = []
    if p.teacher_id:
        if "teacher" in o:
            conds.append(getattr(M, o["teacher"]) == p.teacher_id)
        if "batch" in o and p.batch_ids:
            conds.append(getattr(M, o["batch"]).in_(p.batch_ids))
        if "student" in o and p.batch_ids and o.get("student_via_batch", "yes") != "no":
            conds.append(getattr(M, o["student"]).in_(enrolled_students_subquery(p.batch_ids)))
    if p.linked_student_ids:
        if "student" in o:
            conds.append(getattr(M, o["student"]).in_(p.linked_student_ids))
        if "batch" in o and p.batch_ids and "student" not in o:
            conds.append(getattr(M, o["batch"]).in_(p.batch_ids))
    if "user" in o and p.user_id:
        conds.append(getattr(M, o["user"]) == p.user_id)
    return or_(*conds) if conds else false()


def base_query(p: Principal, res: Resource, mode: str, include_archived: bool = False):
    M = res.model
    q = select(M)
    if res.is_tenant:
        q = q.where(M.institute_id == p.institute_id)
    if res.has_branch:
        nullable = M.__table__.c.branch_id.nullable
        if p.branch_ids is not None:
            cond = M.branch_id.in_(p.branch_ids)
            q = q.where(or_(cond, M.branch_id.is_(None)) if nullable else cond)
        if p.selected_branch_id:
            cond = M.branch_id == p.selected_branch_id
            q = q.where(or_(cond, M.branch_id.is_(None)) if nullable else cond)
    if res.has_archive and not include_archived:
        q = q.where(M.is_archived.is_(False))
    if res.scope_filter is not None:
        cond = res.scope_filter(p, M)
        if cond is not None:
            q = q.where(cond)
    if mode == "own":
        q = q.where(owner_condition(p, res))
    return q


def is_owned(db: Session, p: Principal, res: Resource, obj: Any) -> bool:
    q = base_query(p, res, "own", include_archived=True).where(res.model.id == obj.id)
    return db.scalar(select(func.count()).select_from(q.subquery())) > 0


def owned_values_ok(p: Principal, res: Resource, values: dict) -> bool:
    """Ownership check for a not-yet-persisted object (write_own create)."""
    o = res.owner
    if p.teacher_id:
        if "teacher" in o and values.get(o["teacher"]) == p.teacher_id:
            return "batch" not in o or values.get(o["batch"]) in p.batch_ids or values.get(o["batch"]) is None
        if "batch" in o and values.get(o["batch"]) in p.batch_ids:
            return True
    if p.linked_student_ids and "student" in o and values.get(o["student"]) in p.linked_student_ids:
        return True
    if "user" in o and values.get(o["user"]) == p.user_id:
        return True
    return False


def check_feature(db: Session, p: Principal, res: Resource) -> None:
    if res.feature and not feature_flags.is_enabled(db, p.institute_id, res.feature):
        raise ModuleDisabled(f"The {res.label} module is disabled")


def infer_branch(db: Session, values: dict) -> uuid.UUID | None:
    """Derive branch from the primary parent record (batch → student → teacher)."""
    for key, table in (("batch_id", "batches"), ("student_id", "students"), ("teacher_id", "teachers"), ("classroom_id", "classrooms")):
        if values.get(key):
            t = Base.metadata.tables[table]
            row = db.execute(select(t.c.branch_id).where(t.c.id == values[key])).first()
            if row and row[0]:
                return row[0]
    return None


def validate_references(db: Session, p: Principal, res: Resource, values: dict) -> None:
    """Reject foreign keys that point to another tenant's records (cross-tenant safeguard)."""
    for name, value in values.items():
        if value is None or name not in res.table.c:
            continue
        col = res.table.c[name]
        for fkey in col.foreign_keys:
            target_table = fkey.column.table
            if "institute_id" not in target_table.c:
                continue
            owner = db.execute(select(target_table.c.institute_id).where(fkey.column == value)).first()
            if owner is None:
                raise ValidationFailed(f"Referenced record for '{name}' does not exist")
            if owner[0] is not None and owner[0] != p.institute_id:
                raise Forbidden(f"Referenced record for '{name}' belongs to another institute")
            if target_table.name == "branches":
                p.check_branch(value)


# ----------------------------------------------------------------------------- serialization


def mask_fields(p: Principal, res: Resource) -> set[str]:
    out = set(res.hidden_fields)
    for col in res.table.columns:
        if col.info.get("hidden"):
            out.add(col.name)
        perm = col.info.get("sensitive")
        if perm and not p.can(perm):
            out.add(col.name)
        if col.info.get("staff_only") and not (p.is_staff or p.teacher_id):
            out.add(col.name)
    return out


def serialize(obj: Any, masked: set[str]) -> dict[str, Any]:
    return {c.name: getattr(obj, c.key) for c in obj.__table__.columns if c.name not in masked}


def attach_display(db: Session, table, items: list[dict]) -> None:
    """Resolve foreign keys to human-readable titles in one query per referenced table."""
    for col in table.columns:
        if not col.foreign_keys or col.name in ("institute_id", "created_by_id", "updated_by_id"):
            continue
        target = next(iter(col.foreign_keys)).column.table
        title = TITLE_FIELDS.get(target.name)
        if not title or title not in target.c:
            continue
        ids = {it.get(col.name) for it in items if it.get(col.name)}
        if not ids:
            continue
        rows = db.execute(select(target.c.id, target.c[title]).where(target.c.id.in_(ids))).all()
        labels = {r[0]: (str(r[1]) if r[1] is not None else None) for r in rows}
        for it in items:
            v = it.get(col.name)
            if v:
                it.setdefault("display", {})[col.name] = labels.get(v)


# ----------------------------------------------------------------------------- list helpers

RESERVED_PARAMS = {"page", "page_size", "sort", "q", "include_archived", "format"}


def apply_filters(q, res: Resource, params) -> Any:
    M = res.model
    for key, raw in params.multi_items():
        if key in RESERVED_PARAMS or raw == "":
            continue
        name, op = (key.split("__", 1) + ["eq"])[:2]
        if name not in res.table.c or res.table.c[name].info.get("hidden"):
            continue
        col = res.table.c[name]
        attr = getattr(M, col.key)
        if op == "eq":
            q = q.where(attr == coerce(col, raw))
        elif op == "ne":
            q = q.where(attr != coerce(col, raw))
        elif op == "in":
            q = q.where(attr.in_([coerce(col, v) for v in raw.split(",") if v]))
        elif op == "gte":
            q = q.where(attr >= coerce(col, raw))
        elif op == "lte":
            q = q.where(attr <= coerce(col, raw))
        elif op == "gt":
            q = q.where(attr > coerce(col, raw))
        elif op == "lt":
            q = q.where(attr < coerce(col, raw))
        elif op == "isnull":
            q = q.where(attr.is_(None) if raw.lower() in ("1", "true") else attr.isnot(None))
        elif op == "ilike" and column_kind(col) in ("string", "text"):
            q = q.where(attr.ilike(f"%{raw}%"))
    term = params.get("q")
    if term and res.search:
        like = f"%{term.strip()}%"
        q = q.where(or_(*[getattr(M, f).ilike(like) for f in res.search]))
    return q


def apply_sort(q, res: Resource, sort: str | None):
    M = res.model
    clauses = []
    for part in (sort or res.default_sort).split(","):
        part = part.strip()
        if not part:
            continue
        desc = part.startswith("-")
        name = part.lstrip("-")
        if name in res.table.c and not res.table.c[name].info.get("hidden"):
            attr = getattr(M, res.table.c[name].key)
            clauses.append(attr.desc().nullslast() if desc else attr.asc().nullsfirst())
    clauses.append(M.id.asc())
    return q.order_by(*clauses)


def get_object(db: Session, p: Principal, res: Resource, obj_id: uuid.UUID, include_archived: bool = True):
    mode = read_mode(p, res)
    if mode is None:
        raise Forbidden(f"You cannot view {res.label}")
    obj = db.scalar(base_query(p, res, mode, include_archived).where(res.model.id == obj_id))
    if obj is None:
        raise NotFound(f"{res.label} record not found")
    return obj, mode


# ----------------------------------------------------------------------------- router factory


def build_router(res: Resource) -> APIRouter:
    router = APIRouter(prefix=f"/{res.name}", tags=[res.group])
    CreateM = create_schema(res)
    UpdateM = update_schema(res)
    ReadM = read_schema(res)
    PageM = page_schema(res)

    def _list_query(db, p, request):
        check_feature(db, p, res)
        mode = read_mode(p, res)
        if mode is None:
            raise Forbidden(f"You cannot view {res.label}")
        include_archived = request.query_params.get("include_archived", "").lower() in ("1", "true")
        q = base_query(p, res, mode, include_archived)
        return apply_filters(q, res, request.query_params)

    @router.get("", response_model=PageM, summary=f"List {res.label}")
    def list_items(
        request: Request,
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=settings.MAX_PAGE_SIZE),
        sort: str | None = None,
        q: str | None = Query(None, max_length=100),
        db: Session = Depends(get_db),
        p: Principal = Depends(get_principal),
    ):
        query = _list_query(db, p, request)
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = db.scalars(apply_sort(query, res, sort).offset((page - 1) * page_size).limit(page_size)).all()
        masked = mask_fields(p, res)
        items = [serialize(r, masked) for r in rows]
        attach_display(db, res.table, items)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @router.get("/export", summary=f"Export {res.label}")
    def export_items(
        request: Request,
        format: Literal["csv", "xlsx", "pdf"] = "csv",
        sort: str | None = None,
        db: Session = Depends(get_db),
        p: Principal = Depends(get_principal),
    ):
        query = _list_query(db, p, request)
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        if total > settings.SYNC_EXPORT_ROW_LIMIT:
            from app.services.jobs import enqueue_export

            job = enqueue_export(db, p, res.name, format, dict(request.query_params))
            return Response(
                content=f'{{"job_id":"{job.id}","status":"queued"}}', media_type="application/json", status_code=202
            )
        rows = db.scalars(apply_sort(query, res, sort)).all()
        data, filename, mime = export_rows(db, p, res, rows, format)
        audit.record(db, p, res.table.name, None, "export", new={"format": format, "rows": len(rows)})
        db.commit()
        return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @router.get("/{obj_id}", response_model=ReadM, summary=f"Get {res.label} record")
    def get_item(obj_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
        check_feature(db, p, res)
        obj, _ = get_object(db, p, res, obj_id)
        item = serialize(obj, mask_fields(p, res))
        attach_display(db, res.table, [item])
        return item

    @router.get("/{obj_id}/history", summary=f"Audit history for a {res.label} record")
    def item_history(obj_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
        from app.models import AuditLog

        obj, mode = get_object(db, p, res, obj_id)
        if mode != "all":
            raise Forbidden("History is available to staff only")
        logs = db.scalars(
            select(AuditLog)
            .where(AuditLog.entity_type == res.table.name, AuditLog.entity_id == obj.id, AuditLog.institute_id == p.institute_id)
            .order_by(AuditLog.created_at.desc())
            .limit(200)
        ).all()
        return [
            {
                "id": l.id,
                "action": l.action,
                "actor_email": l.actor_email,
                "old_values": l.old_values,
                "new_values": l.new_values,
                "reason": l.reason,
                "created_at": l.created_at,
            }
            for l in logs
        ]

    if res.allow_create:

        @router.post("", response_model=ReadM, status_code=201, summary=f"Create {res.label} record")
        def create_item(payload: CreateM, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):  # type: ignore[valid-type]
            check_feature(db, p, res)
            mode = write_mode(p, res)
            if mode is None:
                raise Forbidden(f"You cannot create {res.label}")
            values = payload.model_dump(exclude_unset=True)
            if res.has_branch and not values.get("branch_id"):
                default_branch = p.selected_branch_id or (next(iter(p.branch_ids)) if p.branch_ids and len(p.branch_ids) == 1 else None)
                if default_branch is None:
                    default_branch = infer_branch(db, values)
                if default_branch is not None:
                    values["branch_id"] = default_branch
            if mode == "own" and not owned_values_ok(p, res, values):
                raise Forbidden(f"You can only create {res.label} records for your own classes")
            validate_references(db, p, res, values)
            obj = res.model(**values)
            if res.is_tenant:
                obj.institute_id = p.institute_id
            if hasattr(obj, "created_by_id"):
                obj.created_by_id = p.user_id
                obj.updated_by_id = p.user_id
            if res.validate:
                res.validate(db, p, obj, values, True)
            if res.has_branch:
                if obj.branch_id is None and not res.table.c.branch_id.nullable:
                    raise ValidationFailed("branch_id is required (select a branch)")
                p.check_branch(obj.branch_id)
            db.add(obj)
            try:
                db.flush()
                audit.record(db, p, res.table.name, obj.id, "create", new=audit.snapshot(obj), branch_id=getattr(obj, "branch_id", None))
                if res.after_save:
                    res.after_save(db, p, obj, True)
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise Conflict(integrity_message(exc))
            db.refresh(obj)
            item = serialize(obj, mask_fields(p, res))
            attach_display(db, res.table, [item])
            return item

    if res.allow_update:

        @router.patch("/{obj_id}", response_model=ReadM, summary=f"Update {res.label} record")
        def update_item(obj_id: uuid.UUID, payload: UpdateM, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):  # type: ignore[valid-type]
            check_feature(db, p, res)
            mode = write_mode(p, res)
            if mode is None:
                raise Forbidden(f"You cannot modify {res.label}")
            obj, _ = get_object(db, p, res, obj_id)
            if mode == "own" and not is_owned(db, p, res, obj):
                raise Forbidden("You can only modify your own records")
            values = payload.model_dump(exclude_unset=True)
            reason = values.pop("change_reason", None)
            for k, v in list(values.items()):
                if v is None and not res.table.c[k].nullable:
                    raise ValidationFailed(f"'{k}' cannot be empty")
            validate_references(db, p, res, values)
            before = audit.snapshot(obj)
            for k, v in values.items():
                setattr(obj, k, v)
            if hasattr(obj, "updated_by_id"):
                obj.updated_by_id = p.user_id
            if res.has_branch:
                p.check_branch(obj.branch_id)
            if mode == "own" and not owned_values_ok(p, res, {c.name: getattr(obj, c.key) for c in res.table.columns}):
                raise Forbidden("You can only assign records to your own classes")
            if res.validate:
                res.validate(db, p, obj, values, False)
            try:
                db.flush()
                old, new = audit.diff(before, audit.snapshot(obj))
                if new:
                    audit.record(db, p, res.table.name, obj.id, "update", old, new, reason, branch_id=getattr(obj, "branch_id", None))
                if res.after_save:
                    res.after_save(db, p, obj, False)
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise Conflict(integrity_message(exc))
            db.refresh(obj)
            item = serialize(obj, mask_fields(p, res))
            attach_display(db, res.table, [item])
            return item

    if res.allow_delete:

        @router.delete("/{obj_id}", status_code=204, summary=f"Delete or archive {res.label} record")
        def delete_item(
            obj_id: uuid.UUID,
            reason: str | None = Query(None, max_length=500),
            db: Session = Depends(get_db),
            p: Principal = Depends(get_principal),
        ):
            check_feature(db, p, res)
            p.require(res.delete_perm or f"{res.perm}.delete")
            obj, _ = get_object(db, p, res, obj_id, include_archived=False)
            if res.has_archive:
                obj.is_archived = True
                obj.archived_at = datetime.now(timezone.utc)
                audit.record(db, p, res.table.name, obj.id, "archive", reason=reason, branch_id=getattr(obj, "branch_id", None))
                db.commit()
                return Response(status_code=204)
            snap = audit.snapshot(obj)
            try:
                db.delete(obj)
                db.flush()
                audit.record(db, p, res.table.name, obj_id, "delete", old=snap, reason=reason)
                db.commit()
            except IntegrityError:
                db.rollback()
                raise Conflict(f"This {res.label} record is referenced by other records and cannot be deleted. Deactivate it instead.")
            return Response(status_code=204)

        if res.has_archive:

            @router.post("/{obj_id}/restore", response_model=ReadM, summary=f"Restore archived {res.label} record")
            def restore_item(obj_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
                p.require(res.delete_perm or f"{res.perm}.delete")
                obj, _ = get_object(db, p, res, obj_id, include_archived=True)
                obj.is_archived = False
                obj.archived_at = None
                audit.record(db, p, res.table.name, obj.id, "restore")
                db.commit()
                return serialize(obj, mask_fields(p, res))

    return router


def export_rows(db: Session, p: Principal, res: Resource, rows, fmt: str) -> tuple[bytes, str, str]:
    masked = mask_fields(p, res)
    cols = [c for c in res.table.columns if c.name not in masked and c.name not in ("institute_id",) and column_kind(c) != "json"]
    items = [serialize(r, masked) for r in rows]
    attach_display(db, res.table, items)
    headers = [c.name.replace("_id", "").replace("_", " ").title() for c in cols]
    data_rows = []
    for it in items:
        disp = it.get("display") or {}
        data_rows.append([disp.get(c.name) or it.get(c.name) for c in cols])
    data = exporter.render(fmt, headers, data_rows, res.label)
    filename = f"{res.name}-{date.today().isoformat()}.{fmt}"
    return data, filename, exporter.MIME[fmt]


def integrity_message(exc: IntegrityError) -> str:
    msg = str(getattr(exc, "orig", exc)).lower()
    if "unique" in msg or "duplicate" in msg:
        return "A record with the same unique values already exists"
    if "foreign key" in msg:
        return "A referenced record does not exist or is still in use"
    if "check" in msg:
        return "The values violate a data integrity rule (check dates, amounts and ranges)"
    if "not-null" in msg or "null value" in msg:
        return "A required value is missing"
    return "The change conflicts with existing data"


# ----------------------------------------------------------------------------- metadata for the UI


def resource_meta(db: Session, p: Principal, res: Resource) -> dict[str, Any] | None:
    mode = read_mode(p, res)
    if mode is None:
        return None
    if res.feature and not feature_flags.is_enabled(db, p.institute_id, res.feature):
        return None
    masked = mask_fields(p, res)
    writable = {c.name for c in writable_columns(res, True)}
    updatable = {c.name for c in writable_columns(res, False)}
    fields = []
    for col in res.table.columns:
        if col.name in masked or col.name == "institute_id":
            continue
        kind = column_kind(col)
        ref = None
        if kind == "ref":
            target = next(iter(col.foreign_keys)).column.table.name
            ref_res = TABLE_TO_RESOURCE.get(target)
            ref = ref_res.name if ref_res else None
            if target == "users":
                ref = "users"
        fields.append(
            {
                "name": col.name,
                "label": col.info.get("label") or col.name.removesuffix("_id").replace("_", " ").capitalize(),
                "type": kind,
                "widget": col.info.get("widget"),
                "required": (
                    not col.nullable and col.default is None and col.server_default is None
                    and col.name not in res.auto_fields and col.name != "branch_id"
                ),
                "nullable": bool(col.nullable),
                "enum": list(col.type.enums) if kind == "enum" else None,
                "ref": ref,
                "max_length": getattr(col.type, "length", None) if kind == "string" else None,
                "creatable": col.name in writable,
                "updatable": col.name in updatable,
                "system": col.name in SYSTEM_FIELDS,
            }
        )
    wmode = write_mode(p, res)
    return {
        "name": res.name,
        "label": res.label,
        "group": res.group,
        "perm": res.perm,
        "feature": res.feature,
        "title_field": res.title_field,
        "search": bool(res.search),
        "list_columns": list(res.list_columns),
        "default_sort": res.default_sort,
        "archive": res.has_archive,
        "read_mode": mode,
        "can": {
            "create": res.allow_create and wmode is not None,
            "update": res.allow_update and wmode is not None,
            "delete": res.allow_delete and p.can(res.delete_perm or f"{res.perm}.delete"),
        },
        "fields": fields,
    }
