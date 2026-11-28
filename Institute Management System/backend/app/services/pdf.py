"""PDF generation for invoices, receipts, payslips, marksheets, report cards, ID cards and certificates."""

import io
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1E2A78")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#CBD5E1")

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_styles["Title"], fontSize=18, textColor=NAVY, alignment=0, spaceAfter=2)
SMALL = ParagraphStyle("small", parent=_styles["BodyText"], fontSize=8, textColor=MUTED, leading=10)
BODY = ParagraphStyle("body", parent=_styles["BodyText"], fontSize=9, leading=12)


def esc(v: Any) -> str:
    return str("" if v is None else v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_date(d: date | datetime | None) -> str:
    return d.strftime("%d-%m-%Y") if d else "—"


def money(v: Decimal | None, currency: str = "INR") -> str:
    symbol = "₹" if currency == "INR" else f"{currency} "
    return f"{symbol}{Decimal(v or 0):,.2f}".replace("₹", "Rs. ")


def _header(inst, title: str, subtitle: str = "") -> list:
    lines = [esc(inst.name)]
    addr = ", ".join(x for x in [inst.address, inst.city, inst.state, inst.postal_code] if x)
    meta = " · ".join(x for x in [addr, inst.phone, inst.email] if x)
    out = [Paragraph(f"<b>{esc(inst.name)}</b>", H1), Paragraph(esc(meta), SMALL)]
    if inst.tax_enabled and inst.tax_registration_number:
        out.append(Paragraph(f"{esc(inst.tax_label or 'GST')}IN: {esc(inst.tax_registration_number)}", SMALL))
    out += [Spacer(1, 6), Paragraph(f"<b>{esc(title)}</b>", ParagraphStyle("t", parent=BODY, fontSize=13, textColor=NAVY))]
    if subtitle:
        out.append(Paragraph(esc(subtitle), SMALL))
    out.append(Spacer(1, 8))
    return out + ([] if lines else [])


def _table(data: Sequence[Sequence[Any]], widths: Sequence[float] | None = None, header: bool = True) -> Table:
    rows = [[Paragraph(esc(c) if not isinstance(c, Paragraph) else c, BODY) if not isinstance(c, Paragraph) else c for c in r] for r in data]
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.25, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF"))]
    t.setStyle(TableStyle(style))
    return t


def _build(story: list, pagesize=A4) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    doc.build(story)
    return buf.getvalue()


def invoice_pdf(inst, inv, student, items, allocations) -> bytes:
    title = "TAX INVOICE" if inst.tax_enabled and inv.tax_total and inv.tax_total > 0 else "INVOICE"
    if inv.status == "draft":
        title += " (DRAFT)"
    if inv.status == "cancelled":
        title += " (CANCELLED)"
    story = _header(inst, title, f"No. {inv.invoice_number or 'DRAFT'} · Issued {fmt_date(inv.issue_date)} · Due {fmt_date(inv.due_date)}")
    story.append(_table([["Billed to", "Student code", "Period"],
                         [student.full_name, student.student_code, f"{fmt_date(inv.period_start)} – {fmt_date(inv.period_end)}"]],
                        [80 * mm, 40 * mm, 60 * mm]))
    story.append(Spacer(1, 8))
    rows = [["#", "Description", "Qty", "Rate", "Discount", "Tax", "Amount"]]
    for i, it in enumerate(items, 1):
        rows.append([i, it.description, f"{it.quantity:g}", money(it.unit_price, inv.currency), money(it.discount, inv.currency),
                     f"{it.tax_rate:g}% ({money(it.tax_amount, inv.currency)})", money(it.amount, inv.currency)])
    story.append(_table(rows, [8 * mm, 62 * mm, 12 * mm, 24 * mm, 22 * mm, 28 * mm, 26 * mm]))
    story.append(Spacer(1, 8))
    summary = [["Subtotal", money(inv.subtotal, inv.currency)], ["Discounts", money(inv.discount_total, inv.currency)],
               ["Tax", money(inv.tax_total, inv.currency)], ["Total", money(inv.total, inv.currency)],
               ["Paid", money(inv.amount_paid, inv.currency)], ["Credits", money(inv.credit_applied, inv.currency)],
               ["Balance due", money(inv.balance_due, inv.currency)]]
    t = _table(summary, [40 * mm, 35 * mm], header=False)
    t.hAlign = "RIGHT"
    story.append(t)
    if allocations:
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Payments applied</b>", BODY))
        story.append(_table([["Receipt", "Date", "Amount"]] + [[a[0], fmt_date(a[1]), money(a[2], inv.currency)] for a in allocations],
                            [50 * mm, 40 * mm, 40 * mm]))
    if inv.notes:
        story += [Spacer(1, 8), Paragraph(f"Notes: {esc(inv.notes)}", SMALL)]
    story += [Spacer(1, 16), Paragraph("This is a computer-generated document.", SMALL)]
    return _build(story)


def receipt_pdf(inst, pay, student, allocations) -> bytes:
    title = "PAYMENT RECEIPT" + (" (REVERSED)" if pay.status in ("reversed", "bounced") else "")
    story = _header(inst, title, f"Receipt {pay.receipt_number} · {fmt_date(pay.paid_at)}")
    story.append(_table([["Received from", "Student code", "Method", "Reference"],
                         [student.full_name, student.student_code, pay.method.replace("_", " ").title(), pay.reference_number or "—"]],
                        [60 * mm, 35 * mm, 35 * mm, 50 * mm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Amount received: {money(pay.amount, pay.currency)}</b>", BODY))
    if allocations:
        story.append(Spacer(1, 6))
        story.append(_table([["Invoice", "Amount applied"]] + [[a[0], money(a[1], pay.currency)] for a in allocations], [80 * mm, 50 * mm]))
    if pay.unallocated_amount and pay.unallocated_amount > 0:
        story.append(Paragraph(f"Advance / unallocated: {money(pay.unallocated_amount, pay.currency)}", BODY))
    story += [Spacer(1, 16), Paragraph("This is a computer-generated receipt.", SMALL)]
    return _build(story)


def payslip_pdf(inst, slip, teacher, period, entries) -> bytes:
    story = _header(inst, "PAYSLIP", f"{slip.payslip_number} · {esc(period.name)} ({fmt_date(period.start_date)} – {fmt_date(period.end_date)})")
    story.append(_table([["Employee", "Code", "Status"], [teacher.full_name, teacher.teacher_code, slip.status.title()]], [80 * mm, 40 * mm, 40 * mm]))
    story.append(Spacer(1, 8))
    rows = [["Date", "Type", "Description", "Qty", "Rate", "Amount"]]
    for e in entries:
        sign = "-" if e.entry_type == "deduction" else ""
        rows.append([fmt_date(e.entry_date), e.entry_type.replace("_", " "), e.description, f"{e.quantity:g}", money(e.rate), f"{sign}{money(e.amount)}"])
    story.append(_table(rows, [22 * mm, 22 * mm, 70 * mm, 14 * mm, 24 * mm, 28 * mm]))
    story.append(Spacer(1, 8))
    t = _table([["Gross", money(slip.gross_amount)], ["Deductions", money(slip.deductions)], ["Net pay", money(slip.net_amount)]],
               [40 * mm, 35 * mm], header=False)
    t.hAlign = "RIGHT"
    story.append(t)
    return _build(story)


def marksheet_pdf(inst, student, rows: list[list[Any]], title: str = "MARKSHEET", remarks: str | None = None) -> bytes:
    story = _header(inst, title, f"{student.full_name} · {student.student_code}")
    story.append(_table([["Examination", "Subject", "Date", "Marks", "Max", "%", "Grade", "Rank"]] + rows,
                        [42 * mm, 30 * mm, 20 * mm, 16 * mm, 14 * mm, 14 * mm, 14 * mm, 14 * mm]))
    if remarks:
        story += [Spacer(1, 8), Paragraph(esc(remarks), BODY)]
    story += [Spacer(1, 24), Paragraph("Authorised signatory: ____________________", BODY)]
    return _build(story)


def id_card_pdf(inst, student, batch_names: list[str], valid_until: str) -> bytes:
    buf = io.BytesIO()
    w, h = 86 * mm, 54 * mm
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFillColor(NAVY)
    c.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4 * mm, h - 9 * mm, inst.name[:40])
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(4 * mm, h - 21 * mm, student.full_name[:36])
    c.setFont("Helvetica", 8)
    c.drawString(4 * mm, h - 27 * mm, f"Student ID: {student.student_code}")
    c.drawString(4 * mm, h - 32 * mm, f"Batch: {', '.join(batch_names)[:48]}")
    c.drawString(4 * mm, h - 37 * mm, f"Guardian: {(student.guardian_name or '—')[:30]}  {student.guardian_phone or ''}")
    c.drawString(4 * mm, h - 42 * mm, f"Emergency: {student.emergency_contact_phone or student.guardian_phone or '—'}")
    c.setFillColor(MUTED)
    c.drawString(4 * mm, 4 * mm, f"Valid until {valid_until}")
    c.showPage()
    c.save()
    return buf.getvalue()


def certificate_pdf(inst, student, title: str, body: str, number: str) -> bytes:
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setStrokeColor(NAVY)
    c.setLineWidth(4)
    c.rect(12 * mm, 12 * mm, w - 24 * mm, h - 24 * mm)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(w / 2, h - 45 * mm, inst.name)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, h - 70 * mm, title)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 13)
    c.drawCentredString(w / 2, h - 90 * mm, "This is to certify that")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 105 * mm, student.full_name)
    c.setFont("Helvetica", 12)
    for i, line in enumerate(body.split("\n")[:4]):
        c.drawCentredString(w / 2, h - (122 + i * 8) * mm, line)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, 20 * mm, f"Certificate no. {number} · Issued {fmt_date(date.today())}")
    c.drawRightString(w - 20 * mm, 20 * mm, "Authorised signatory")
    c.showPage()
    c.save()
    return buf.getvalue()
