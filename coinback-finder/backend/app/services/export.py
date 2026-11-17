"""CSV / XLSX export with spreadsheet formula-injection protection."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any

from openpyxl import Workbook

from app.services.clock import IST

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


Column = tuple[str, Callable[[Any], Any]]


def export_csv(columns: list[Column], rows: Iterable[Any]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([name for name, _ in columns])
    for row in rows:
        writer.writerow([_cell(getter(row)) for _, getter in columns])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def export_xlsx(columns: list[Column], rows: Iterable[Any], sheet: str = "Export") -> bytes:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet[:31])
    ws.append([name for name, _ in columns])
    for row in rows:
        ws.append([_cell(getter(row)) for _, getter in columns])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
