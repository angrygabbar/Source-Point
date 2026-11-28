import csv
import io
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MIME = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return str(v)
    return v


def _formula_safe(v: Any) -> Any:
    # Prevent CSV/Excel formula injection.
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") and not v[1:2].isdigit():
        return "'" + v
    return v


def to_csv(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([_formula_safe(_cell(v)) for v in r])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def to_xlsx(headers: Sequence[str], rows: Sequence[Sequence[Any]], title: str = "Export") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] or "Export"
    ws.append(list(headers))
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E2A78")
    for r in rows:
        ws.append([_formula_safe(_cell(v)) if not isinstance(v, (int, float)) else v for v in r])
    for i, h in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(max(len(str(h)) + 4, 12), 40)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def to_pdf(headers: Sequence[str], rows: Sequence[Sequence[Any]], title: str, subtitle: str | None = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small", fontSize=7, leading=9)
    story: list[Any] = [Paragraph(title, styles["Title"])]
    story.append(Paragraph(subtitle or f"Generated {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 6))
    data = [[Paragraph(f"<b>{h}</b>", small) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(_cell(v)).replace("&", "&amp;").replace("<", "&lt;")[:300], small) for v in r])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E2A78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buf.getvalue()


def render(fmt: str, headers: Sequence[str], rows: Sequence[Sequence[Any]], title: str) -> bytes:
    if fmt == "xlsx":
        return to_xlsx(headers, rows, title)
    if fmt == "pdf":
        return to_pdf(headers, rows, title)
    return to_csv(headers, rows)
