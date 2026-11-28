"""CSV/Excel import: template → preview (row-level validation) → commit."""

import csv
import io
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.models import (
    AcademicYear,
    Batch,
    Branch,
    ClassSession,
    Classroom,
    Course,
    Student,
    StudentAttendance,
    StudentEnrollment,
    Subject,
    Teacher,
)
from app.services import numbering

TEMPLATES: dict[str, list[str]] = {
    "students": ["full_name*", "student_code", "phone", "email", "date_of_birth", "gender", "address", "city", "state", "postal_code",
                 "admission_date", "guardian_name", "guardian_phone", "guardian_email", "guardian_relation", "branch_code*", "batch_code"],
    "teachers": ["full_name*", "teacher_code", "phone", "email", "qualifications", "specialization", "joining_date*", "employment_type",
                 "compensation_type", "compensation_amount", "branch_code*"],
    "courses": ["name*", "code*", "description", "duration_months", "branch_code"],
    "subjects": ["name*", "code*", "course_code", "description"],
    "batches": ["name*", "code*", "course_code*", "academic_year*", "branch_code*", "start_date*", "end_date", "capacity", "classroom_code"],
    "enrollments": ["student_code*", "batch_code*", "start_date*"],
    "attendance": ["student_code*", "batch_code*", "subject_code*", "session_date*", "status*", "remarks"],
}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ROWS = 5000


def template_csv(entity: str) -> bytes:
    if entity not in TEMPLATES:
        raise ValidationFailed("Unknown import type")
    buf = io.StringIO()
    csv.writer(buf).writerow([h.rstrip("*") for h in TEMPLATES[entity]])
    return buf.getvalue().encode()


def parse_file(filename: str, data: bytes) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if filename.lower().endswith(".xlsx"):
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower().rstrip("*") for h in next(it, [])]
        for r in it:
            if r is None or all(v in (None, "") for v in r):
                continue
            rows.append({headers[i]: ("" if v is None else (v.strftime("%Y-%m-%d") if isinstance(v, (datetime, date)) else str(v)).strip())
                         for i, v in enumerate(r) if i < len(headers)})
    else:
        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for r in reader:
            rows.append({(k or "").strip().lower().rstrip("*"): (v or "").strip() for k, v in r.items()})
    if len(rows) > MAX_ROWS:
        raise ValidationFailed(f"Imports are limited to {MAX_ROWS} rows per file")
    return rows


def _date(v: str, field: str, errors: list[str], required: bool = False) -> date | None:
    if not v:
        if required:
            errors.append(f"{field} is required")
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v[:10], fmt).date()
        except ValueError:
            continue
    errors.append(f"{field} must be a date (DD-MM-YYYY)")
    return None


def _req(row: dict, field: str, errors: list[str]) -> str:
    v = row.get(field, "")
    if not v:
        errors.append(f"{field} is required")
    return v


class Resolver:
    def __init__(self, db: Session, institute_id: uuid.UUID):
        self.db, self.inst = db, institute_id
        self.cache: dict[tuple[str, str], Any] = {}

    def by_code(self, model, code: str, field: str = "code"):
        if not code:
            return None
        key = (model.__tablename__, code.lower())
        if key not in self.cache:
            col = getattr(model, field)
            self.cache[key] = self.db.scalar(select(model).where(model.institute_id == self.inst, func.lower(col) == code.lower()))
        return self.cache[key]


def validate_rows(db: Session, p, entity: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    if entity not in TEMPLATES:
        raise ValidationFailed("Unknown import type")
    R = Resolver(db, p.institute_id)
    seen: set[str] = set()
    out = []
    for i, row in enumerate(rows, start=2):
        errors: list[str] = []
        data: dict[str, Any] = {}
        if entity == "students":
            data["full_name"] = _req(row, "full_name", errors)
            branch = R.by_code(Branch, _req(row, "branch_code", errors))
            if row.get("branch_code") and branch is None:
                errors.append("branch_code not found")
            data["branch_id"] = branch.id if branch else None
            code = row.get("student_code")
            if code:
                if code.lower() in seen:
                    errors.append("Duplicate student_code in file")
                seen.add(code.lower())
                if R.by_code(Student, code, "student_code"):
                    errors.append("student_code already exists")
            data["student_code"] = code or None
            for f in ("phone", "address", "city", "state", "postal_code", "guardian_name", "guardian_phone", "guardian_relation"):
                data[f] = row.get(f) or None
            for f in ("email", "guardian_email"):
                if row.get(f) and not EMAIL.match(row[f]):
                    errors.append(f"{f} is invalid")
                data[f] = row.get(f) or None
            g = (row.get("gender") or "").lower() or None
            if g and g not in ("male", "female", "other", "prefer_not_to_say"):
                errors.append("gender must be male/female/other/prefer_not_to_say")
            data["gender"] = g
            data["date_of_birth"] = _date(row.get("date_of_birth", ""), "date_of_birth", errors)
            data["admission_date"] = _date(row.get("admission_date", ""), "admission_date", errors) or date.today()
            if row.get("phone") and data["full_name"]:
                dup = db.scalar(select(Student.id).where(Student.institute_id == p.institute_id, Student.phone == row["phone"],
                                                         func.lower(Student.full_name) == data["full_name"].lower()))
                if dup:
                    errors.append("A student with the same name and phone already exists")
            if row.get("batch_code"):
                b = R.by_code(Batch, row["batch_code"])
                if b is None:
                    errors.append("batch_code not found")
                data["_batch_id"] = b.id if b else None
        elif entity == "teachers":
            data["full_name"] = _req(row, "full_name", errors)
            branch = R.by_code(Branch, _req(row, "branch_code", errors))
            if row.get("branch_code") and branch is None:
                errors.append("branch_code not found")
            data["branch_id"] = branch.id if branch else None
            code = row.get("teacher_code")
            if code:
                if code.lower() in seen:
                    errors.append("Duplicate teacher_code in file")
                seen.add(code.lower())
                if R.by_code(Teacher, code, "teacher_code"):
                    errors.append("teacher_code already exists")
            data["teacher_code"] = code or None
            data["joining_date"] = _date(row.get("joining_date", ""), "joining_date", errors, True)
            for f in ("phone", "qualifications", "specialization"):
                data[f] = row.get(f) or None
            if row.get("email") and not EMAIL.match(row["email"]):
                errors.append("email is invalid")
            data["email"] = row.get("email") or None
            et = row.get("employment_type") or "full_time"
            if et not in ("full_time", "part_time", "visiting", "contract"):
                errors.append("employment_type invalid")
            ct = row.get("compensation_type") or "fixed_monthly"
            if ct not in ("fixed_monthly", "per_class", "per_hour", "custom"):
                errors.append("compensation_type invalid")
            data["employment_type"], data["compensation_type"] = et, ct
            try:
                data["compensation_amount"] = Decimal(row.get("compensation_amount") or "0")
            except InvalidOperation:
                errors.append("compensation_amount must be a number")
        elif entity in ("courses", "subjects"):
            model = Course if entity == "courses" else Subject
            data["name"] = _req(row, "name", errors)
            code = _req(row, "code", errors)
            if code:
                if code.lower() in seen:
                    errors.append("Duplicate code in file")
                seen.add(code.lower())
                if R.by_code(model, code):
                    errors.append("code already exists")
            data["code"] = code
            data["description"] = row.get("description") or None
            if entity == "courses":
                if row.get("duration_months"):
                    if not row["duration_months"].isdigit():
                        errors.append("duration_months must be a whole number")
                    else:
                        data["duration_months"] = int(row["duration_months"])
                if row.get("branch_code"):
                    br = R.by_code(Branch, row["branch_code"])
                    if br is None:
                        errors.append("branch_code not found")
                    data["branch_id"] = br.id if br else None
            elif row.get("course_code"):
                c = R.by_code(Course, row["course_code"])
                if c is None:
                    errors.append("course_code not found")
                data["course_id"] = c.id if c else None
        elif entity == "batches":
            data["name"] = _req(row, "name", errors)
            code = _req(row, "code", errors)
            if code and (code.lower() in seen or R.by_code(Batch, code)):
                errors.append("code already exists")
            seen.add(code.lower())
            data["code"] = code
            c = R.by_code(Course, _req(row, "course_code", errors))
            ay = R.by_code(AcademicYear, _req(row, "academic_year", errors), "name")
            br = R.by_code(Branch, _req(row, "branch_code", errors))
            for obj, f in ((c, "course_code"), (ay, "academic_year"), (br, "branch_code")):
                if row.get(f) and obj is None:
                    errors.append(f"{f} not found")
            data.update(course_id=c.id if c else None, academic_year_id=ay.id if ay else None, branch_id=br.id if br else None)
            data["start_date"] = _date(row.get("start_date", ""), "start_date", errors, True)
            data["end_date"] = _date(row.get("end_date", ""), "end_date", errors)
            data["capacity"] = int(row["capacity"]) if (row.get("capacity") or "").isdigit() else 30
            if row.get("classroom_code"):
                room = R.by_code(Classroom, row["classroom_code"])
                if room is None:
                    errors.append("classroom_code not found")
                data["default_classroom_id"] = room.id if room else None
        elif entity == "enrollments":
            st = R.by_code(Student, _req(row, "student_code", errors), "student_code")
            b = R.by_code(Batch, _req(row, "batch_code", errors))
            if row.get("student_code") and st is None:
                errors.append("student_code not found")
            if row.get("batch_code") and b is None:
                errors.append("batch_code not found")
            data["start_date"] = _date(row.get("start_date", ""), "start_date", errors, True)
            if st and b:
                key = f"{st.id}:{b.id}"
                if key in seen or db.scalar(select(StudentEnrollment.id).where(StudentEnrollment.student_id == st.id,
                                                                               StudentEnrollment.batch_id == b.id, StudentEnrollment.status == "active")):
                    errors.append("Student already enrolled in batch")
                seen.add(key)
                data.update(student_id=st.id, batch_id=b.id, course_id=b.course_id, academic_year_id=b.academic_year_id, branch_id=b.branch_id)
        elif entity == "attendance":
            st = R.by_code(Student, _req(row, "student_code", errors), "student_code")
            b = R.by_code(Batch, _req(row, "batch_code", errors))
            sj = R.by_code(Subject, _req(row, "subject_code", errors))
            d = _date(row.get("session_date", ""), "session_date", errors, True)
            status = (row.get("status") or "").lower()
            if status not in ("present", "absent", "late", "excused", "approved_leave"):
                errors.append("status must be present/absent/late/excused/approved_leave")
            if st is None and row.get("student_code"):
                errors.append("student_code not found")
            if b and sj and d:
                sess = db.scalar(select(ClassSession).where(ClassSession.institute_id == p.institute_id, ClassSession.batch_id == b.id,
                                                            ClassSession.subject_id == sj.id, ClassSession.session_date == d,
                                                            ClassSession.status.notin_(("cancelled", "postponed"))).limit(1))
                if sess is None:
                    errors.append("No class session found for batch/subject/date")
                elif st and db.scalar(select(StudentAttendance.id).where(StudentAttendance.session_id == sess.id, StudentAttendance.student_id == st.id)):
                    errors.append("Attendance already recorded")
                else:
                    data.update(session_id=sess.id if sess else None)
            data.update(student_id=st.id if st else None, status=status, remarks=row.get("remarks") or None)
            key = f"{data.get('session_id')}:{data.get('student_id')}"
            if key in seen:
                errors.append("Duplicate row in file")
            seen.add(key)
        if "branch_id" in data and data["branch_id"] and p.branch_ids is not None and data["branch_id"] not in p.branch_ids:
            errors.append("Branch outside your access")
        out.append({"row": i, "data": data, "errors": errors})
    return out


def commit_rows(db: Session, p, entity: str, rows: list[dict[str, Any]]) -> int:
    created = 0
    for r in rows:
        if r["errors"]:
            continue
        d = {k: v for k, v in r["data"].items() if not k.startswith("_")}
        if entity == "students":
            d["student_code"] = d.get("student_code") or numbering.next_code(db, p.institute_id, "student", "STU")
            obj = Student(institute_id=p.institute_id, status="active", created_by_id=p.user_id, updated_by_id=p.user_id, **d)
            db.add(obj)
            db.flush()
            if r["data"].get("_batch_id"):
                b = db.get(Batch, r["data"]["_batch_id"])
                db.add(StudentEnrollment(institute_id=p.institute_id, branch_id=b.branch_id, student_id=obj.id, batch_id=b.id, course_id=b.course_id,
                                         academic_year_id=b.academic_year_id, start_date=obj.admission_date, status="active", created_by_id=p.user_id))
        elif entity == "teachers":
            d["teacher_code"] = d.get("teacher_code") or numbering.next_code(db, p.institute_id, "teacher", "TCH")
            db.add(Teacher(institute_id=p.institute_id, created_by_id=p.user_id, updated_by_id=p.user_id, **d))
        elif entity == "courses":
            db.add(Course(institute_id=p.institute_id, created_by_id=p.user_id, **d))
        elif entity == "subjects":
            db.add(Subject(institute_id=p.institute_id, created_by_id=p.user_id, **d))
        elif entity == "batches":
            db.add(Batch(institute_id=p.institute_id, status="active", created_by_id=p.user_id, **d))
        elif entity == "enrollments":
            db.add(StudentEnrollment(institute_id=p.institute_id, status="active", remarks="Imported", created_by_id=p.user_id, **d))
        elif entity == "attendance":
            db.add(StudentAttendance(institute_id=p.institute_id, session_id=d["session_id"], student_id=d["student_id"], status=d["status"],
                                     remarks=d.get("remarks"), is_locked=True, marked_by_id=p.user_id, marked_at=datetime.now().astimezone()))
        created += 1
    db.flush()
    return created
