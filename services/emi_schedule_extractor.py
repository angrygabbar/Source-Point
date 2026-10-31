"""Local extraction helpers for CSV and credit-card EMI schedule PDFs."""

import csv
import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

import pypdf


class ScheduleExtractionError(ValueError):
    """Raised when an uploaded file does not contain usable installment rows."""


@dataclass
class ExtractedInstallment:
    due_date: date
    amount: Decimal
    description: str


_DATE_RE = re.compile(
    r"(?<!\d)(?:"
    r"\d{4}[./-]\d{1,2}[./-]\d{1,2}|"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}[\s/-]+[A-Za-z]{3,9}[\s/-]+\d{2,4}|"
    r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}"
    r")(?!\d)",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"(?<![\w/])(?:(?:₹|Rs\.?|INR)\s*)?"
    r"(?P<value>\(?-?\d[\d,]*(?:\.\d{1,2})?\)?)(?![\w/])",
    re.IGNORECASE,
)
_SCHEDULE_TERMS = (
    "amortization schedule", "amortisation schedule", "repayment schedule",
    "emi schedule", "installment schedule", "instalment schedule",
    "installment summary", "instalment summary", "mra billing date",
    "monthly repayment amount", "emi amount", "installment amount",
    "instalment amount",
)
_IGNORED_ROW_TERMS = (
    "transaction date", "txn date", "purchase date", "booking date",
    "conversion date", "disbursement date", "request id", "principal amount",
    "loan amount", "total amount", "processing fee", "statement date",
    "first billing date", "first payment due date", "payment due date:",
)


def _parse_date(value):
    value = re.sub(r"\s+", " ", value.strip().replace(",", ""))
    short_year = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2})", value)
    if short_year:
        day, month, year = map(int, short_year.groups())
        try:
            return date(2000 + year, month, day)
        except ValueError:
            return None
    formats = (
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%d-%b-%Y", "%d %b %Y", "%d %B %Y",
        "%d/%b/%Y", "%d/%B/%Y", "%b %d %Y", "%B %d %Y",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(value, date_format).date()
            if parsed.year < 100:
                parsed = parsed.replace(year=2000 + parsed.year)
            return parsed
        except ValueError:
            continue
    return None


def _parse_amount(value):
    cleaned = re.sub(r"(?:₹|Rs\.?|INR)", "", value, flags=re.IGNORECASE).strip().replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def _amounts(text):
    values = []
    for match in _AMOUNT_RE.finditer(text):
        if text[match.end():].lstrip().startswith("%"):
            continue
        value = _parse_amount(match.group("value"))
        if value is not None:
            values.append(value)
    return values


def _detect_bank(text):
    normalized = text.lower()
    if "icici" in normalized:
        return "ICICI Bank"
    if "axis bank" in normalized or re.search(r"\baxis\b", normalized):
        return "Axis Bank"
    if "sbi card" in normalized or "sbicard" in normalized or "state bank of india" in normalized:
        return "SBI Card"
    return "Bank schedule"


def _date_rows(lines, full_text, title):
    normalized_document = re.sub(r"\s+", " ", full_text.lower())
    uses_statement_billing_dates = "mra billing date" in normalized_document
    has_schedule_context = any(term in normalized_document for term in _SCHEDULE_TERMS)
    has_emi_context = "emi" in normalized_document and any(
        term in normalized_document for term in ("due date", "billing date", "tenure", "installment", "instalment")
    )
    if not has_schedule_context and not has_emi_context:
        raise ScheduleExtractionError(
            "This PDF does not look like an EMI or repayment schedule. Upload the bank's amortization schedule or a CSV with Date and Amount columns."
        )

    installments = []
    seen = set()
    lower_lines = [line.lower() for line in lines]
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        # PDF table extraction can place a date on one line and its amount on
        # the next. Join that continuation only when it contains no second date.
        search_line = line
        current_dates = list(_DATE_RE.finditer(line))
        trailing_text = line[current_dates[-1].end():] if current_dates else line
        if not _amounts(trailing_text) and index + 1 < len(lines) and not _DATE_RE.search(lines[index + 1]):
            search_line = f"{line} {lines[index + 1]}"

        dates = list(_DATE_RE.finditer(search_line))
        for date_index, date_match in enumerate(dates):
            row_context = search_line.lower()
            context_start = max(0, index - 5)
            nearby = " ".join(lower_lines[context_start:index + 1])
            if any(term in row_context for term in _IGNORED_ROW_TERMS):
                continue

            parsed_date = _parse_date(date_match.group(0))
            if not parsed_date:
                continue

            end = dates[date_index + 1].start() if date_index + 1 < len(dates) else len(search_line)
            row_values = search_line[date_match.end():end]
            values = _amounts(row_values)
            if not values:
                values = _amounts(search_line[:date_match.start()])
            if not values:
                continue

            # EMI/MRA is normally the first amount after the installment date
            # in Axis, SBI Card, and ICICI amortization tables. SBI's published
            # MRA examples explicitly exclude the listed tax column, so include
            # that final column when the table identifies it.
            amount = values[0]
            if "sbi" in full_text.lower() and re.search(r"applicable taxes?", nearby) and len(values) >= 4:
                amount += values[-1]

            # A one-off metadata date is not an installment. Requiring table
            # context or a row-like date/amount entry avoids importing headers.
            if not any(term in nearby for term in _SCHEDULE_TERMS) and not has_emi_context:
                continue
            key = (parsed_date, amount)
            if key in seen:
                continue
            seen.add(key)
            suffix = " (incl. listed tax)" if amount != values[0] else ""
            if uses_statement_billing_dates:
                suffix += " (billing date; check statement for payment due date)"
            description_prefix = "Installment for "
            max_title_length = max(0, 200 - len(description_prefix) - len(suffix))
            installments.append(ExtractedInstallment(
                due_date=parsed_date,
                amount=amount,
                description=f"{description_prefix}{title[:max_title_length]}{suffix}",
            ))

    installments.sort(key=lambda item: item.due_date)
    if not installments:
        raise ScheduleExtractionError(
            "No installment rows could be read from this PDF. If it is a scanned or password-protected PDF, export an unlocked, text-searchable copy or upload a CSV."
        )
    return installments


def _period_rows(lines):
    """Read date-free amortization tables with Period and EMI Amount columns."""
    compact_text = re.sub(r"[^a-z]", "", " ".join(lines).lower())
    amount_heading = any(term in compact_text for term in (
        "emiamount", "installmentamount", "instalmentamount", "monthlyrepaymentamount",
    ))
    if "period" not in compact_text or not amount_heading:
        return []

    periods = {}
    for line in lines:
        row_match = re.match(r"^\s*(?:period\s+)?(\d{1,3})\s+(.+)$", line, re.IGNORECASE)
        if not row_match:
            continue
        period_number = int(row_match.group(1))
        if not 1 <= period_number <= 360:
            continue
        values = _amounts(row_match.group(2))
        if not values:
            continue
        # Amortization tables commonly list outstanding balance, principal,
        # interest, then EMI amount. The EMI column is identified by the table
        # heading and is the final amount in those rows.
        periods[period_number] = values[-1] if len(values) > 1 else values[0]
    return sorted(periods.items())


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _extract_from_pdf_text(text, title, first_due_date):
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    try:
        return _detect_bank(text), _date_rows(lines, text, title)
    except ScheduleExtractionError as date_error:
        periods = _period_rows(lines)
        if not periods:
            raise date_error
        if not first_due_date:
            raise ScheduleExtractionError(
                "This schedule has EMI periods and amounts but no payment dates. Enter the first installment due date to generate the monthly schedule."
            )
        installments = [
            ExtractedInstallment(
                due_date=_add_months(first_due_date, period_number - 1),
                amount=amount,
                description=f"Installment for {title[:100]} (period {period_number}; monthly date generated)",
            )
            for period_number, amount in periods
        ]
        return _detect_bank(text), installments


def _ocr_pdf(pdf_bytes, page_count):
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except ImportError as exc:
        raise ScheduleExtractionError(
            "This PDF is image-based and OCR is unavailable on the server. Upload a text-searchable PDF or CSV."
        ) from exc

    try:
        last_page = min(page_count, 25)
        images = convert_from_bytes(
            pdf_bytes,
            dpi=250,
            first_page=1,
            last_page=last_page,
            fmt="png",
            thread_count=1,
            timeout=90,
        )
        text_pages = []
        for image in images:
            try:
                grid_text = _ocr_grid_table(image, pytesseract)
                if grid_text:
                    text_pages.append(grid_text)
                else:
                    text_pages.append(pytesseract.image_to_string(image, lang="eng", config="--psm 6"))
            finally:
                image.close()
        return "\n".join(text_pages)
    except Exception as exc:
        raise ScheduleExtractionError(
            "The scanned PDF could not be read. Try a clearer scan or upload the bank's CSV/text PDF."
        ) from exc


def _ocr_grid_table(image, pytesseract):
    """OCR ruled schedule tables cell-by-cell to avoid gridline noise."""
    from PIL import Image, ImageOps

    gray = ImageOps.grayscale(image)
    pixels = gray.load()
    width, height = gray.size

    def group_lines(indices, minimum=2):
        groups = []
        for coordinate in indices:
            if not groups or coordinate > groups[-1][-1] + 3:
                groups.append([coordinate])
            else:
                groups[-1].append(coordinate)
        return [round(sum(group) / len(group)) for group in groups if len(group) >= minimum]

    horizontal = group_lines(
        y for y in range(height)
        if sum(1 for x in range(width) if pixels[x, y] < 100) > width * 0.5
    )
    sections = []
    for y in horizontal:
        if not sections or y - sections[-1][-1] > 220:
            sections.append([y])
        else:
            sections[-1].append(y)

    def read_cell(x0, x1, y0, y1):
        inset_x = max(4, round((x1 - x0) * 0.012))
        inset_y = max(3, round((y1 - y0) * 0.06))
        if x1 - x0 <= inset_x * 2 or y1 - y0 <= inset_y * 2:
            return ""
        cell = gray.crop((x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y))
        cell = cell.resize((cell.width * 3, cell.height * 3), Image.Resampling.LANCZOS)
        try:
            return pytesseract.image_to_string(cell, lang="eng", config="--psm 7 --oem 1").strip()
        finally:
            cell.close()

    for boundaries in sections:
        if len(boundaries) < 5 or boundaries[-1] - boundaries[0] > height * 0.65:
            continue
        data_top, data_bottom = boundaries[1], boundaries[-1]
        vertical = group_lines(
            x for x in range(width)
            if sum(1 for y in range(data_top, data_bottom) if pixels[x, y] < 100)
            > (data_bottom - data_top) * 0.65
        )
        if len(vertical) < 3:
            continue

        headers = [
            read_cell(x0, x1, boundaries[0], boundaries[1])
            for x0, x1 in zip(vertical, vertical[1:])
        ]
        normalized_headers = [re.sub(r"[^a-z]", "", header.lower()) for header in headers]
        amount_column = next((
            index for index, header in enumerate(normalized_headers)
            if "mra" in header
            or ("amount" in header and any(word in header for word in ("emi", "installment", "instalment", "repayment")))
        ), None)
        if amount_column is None:
            continue

        date_column = next((
            index for index, header in enumerate(normalized_headers)
            if "date" in header and any(word in header for word in ("due", "billing", "emi", "installment", "instalment", "payment"))
        ), None)
        period_column = next((index for index, header in enumerate(normalized_headers) if "period" in header), None)
        rows = []
        row_boundaries = boundaries[1:]
        for row_index, (y0, y1) in enumerate(zip(row_boundaries, row_boundaries[1:]), start=1):
            if date_column is not None:
                date_text = read_cell(vertical[date_column], vertical[date_column + 1], y0, y1)
                amount_text = read_cell(vertical[amount_column], vertical[amount_column + 1], y0, y1)
                if _DATE_RE.search(date_text) and _amounts(amount_text):
                    rows.append(f"{date_text} {amount_text}")
            elif period_column is not None:
                amount_text = read_cell(vertical[amount_column], vertical[amount_column + 1], y0, y1)
                values = _amounts(amount_text)
                if values:
                    rows.append(f"{row_index} {amount_text}")
        if rows:
            result = "\n".join([" ".join(headers), *rows])
            gray.close()
            return result

    gray.close()
    return ""


def _csv_rows(file_storage, title):
    try:
        content = file_storage.stream.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        file_storage.stream.seek(0)
        content = file_storage.stream.read().decode("latin-1")
    if not content.strip():
        raise ScheduleExtractionError("The CSV file is empty.")

    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        raise ScheduleExtractionError("The CSV needs a header row containing Date and Amount columns.")

    def normalize_header(value):
        return re.sub(r"[^a-z]", "", (value or "").lower())

    headers = {normalize_header(name): name for name in reader.fieldnames}

    def find_header(aliases):
        return next((original for normalized, original in headers.items()
                     if any(normalized == alias or normalized.startswith(alias) for alias in aliases)), None)

    date_header = find_header(("date", "duedate", "emidate", "emiduedate", "installmentdate", "instalmentdate", "installmentduedate", "instalmentduedate", "billingdate"))
    amount_header = find_header(("amount", "emiamount", "installmentamount", "instalmentamount", "mra"))
    description_header = find_header(("description", "details", "particulars", "remarks"))
    if not date_header or not amount_header:
        raise ScheduleExtractionError("The CSV needs Date and Amount columns (EMI Amount, Installment Amount, and MRA are also supported).")

    installments = []
    for row in reader:
        parsed_date = _parse_date(row.get(date_header) or "")
        amount = _parse_amount(row.get(amount_header) or "")
        if not parsed_date or not amount:
            continue
        description = ((row.get(description_header) or "") if description_header else "").strip()
        if "processing fee" in description.lower():
            continue
        installments.append(ExtractedInstallment(
            due_date=parsed_date,
            amount=amount,
            description=description or f"Installment for {title}",
        ))
    installments.sort(key=lambda item: item.due_date)
    if not installments:
        raise ScheduleExtractionError("No valid payment rows found. Check that the CSV has valid Date and Amount values.")
    return installments


def extract_emi_schedule(file_storage, filename, title, first_due_date=None):
    """Extract installment rows from a CSV, text PDF, or scanned schedule PDF."""
    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if extension == "csv":
        return "CSV", _csv_rows(file_storage, title)
    if extension != "pdf":
        raise ScheduleExtractionError("Upload a CSV or PDF schedule file.")

    try:
        reader = pypdf.PdfReader(file_storage)
        if reader.is_encrypted:
            raise ScheduleExtractionError("This PDF is password-protected. Upload an unlocked copy.")
        page_count = len(reader.pages)
        page_text = [(page.extract_text() or "") for page in reader.pages]
    except ScheduleExtractionError:
        raise
    except Exception as exc:
        raise ScheduleExtractionError("The PDF could not be opened. Upload a valid, unlocked PDF.") from exc

    file_storage.stream.seek(0)
    pdf_bytes = file_storage.stream.read()
    text = "\n".join(page_text)
    try:
        return _extract_from_pdf_text(text, title, first_due_date)
    except ScheduleExtractionError as text_error:
        try:
            ocr_text = _ocr_pdf(pdf_bytes, page_count)
            return _extract_from_pdf_text(ocr_text, title, first_due_date)
        except ScheduleExtractionError as ocr_error:
            # Preserve the actionable missing-date message when OCR succeeded
            # in reading a period-only schedule.
            if "no payment dates" in str(ocr_error).lower():
                raise ocr_error
            if "no payment dates" in str(text_error).lower():
                raise text_error
            raise ocr_error
