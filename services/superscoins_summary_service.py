# Source Point/services/superscoins_summary_service.py
"""
Generates a professional SupersCoins transaction history PDF and sends
the daily summary email with the PDF attached.
"""

from datetime import datetime
from fpdf import FPDF

from extensions import db
from models.auth import User
from models.commerce import SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice
from enums import SupersCoinTransactionType


# ═══════════════════════════════════════════════════════════════════════
#  PDF Colour Palette — Dark-gold premium theme to match the email
# ═══════════════════════════════════════════════════════════════════════
C_BG_PAGE       = (248, 250, 252)   # Slate-50
C_BRAND_DARK    = (120, 53, 15)     # Amber-900
C_BRAND_MID     = (180, 83, 9)      # Amber-700
C_BRAND_ACCENT  = (245, 158, 11)    # Amber-500
C_BRAND_PALE    = (254, 243, 199)   # Amber-100
C_TEXT_DARK     = (15, 23, 42)      # Slate-900
C_TEXT_MID      = (71, 85, 105)     # Slate-600
C_TEXT_MUTED    = (148, 163, 184)   # Slate-400
C_WHITE         = (255, 255, 255)
C_CREDIT_GREEN  = (16, 185, 129)    # Emerald-500
C_DEBIT_RED     = (239, 68, 68)     # Red-500
C_ROW_ALT       = (241, 245, 249)   # Slate-100
C_BORDER_LIGHT  = (226, 232, 240)   # Slate-200


class SupersCoinSummaryPDF(FPDF):
    """A branded, professional PDF for SupersCoins transaction history."""

    def __init__(self, user, wallet, transactions, invoices, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        self.wallet = wallet
        self.transactions = transactions
        self.invoices = invoices
        self.balance = float(wallet.balance) if wallet and wallet.balance else 0.0
        self.set_auto_page_break(auto=True, margin=28)

    # ── Header (pages 2+) ──
    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*C_BG_PAGE)
        self.rect(0, 0, 210, 297, 'F')
        self.set_fill_color(*C_BRAND_DARK)
        self.rect(0, 0, 210, 12, 'F')
        self.set_font('helvetica', 'B', 9)
        self.set_text_color(*C_BRAND_PALE)
        self.set_xy(10, 2)
        self.cell(80, 8, 'Source Point', 0, 0, 'L')
        self.set_font('helvetica', '', 8)
        self.set_xy(100, 2)
        self.cell(100, 8, f'SupersCoins Statement - {_safe_text(self.user.username)}', 0, 0, 'R')
        self.set_y(16)

    # ── Footer ──
    def footer(self):
        self.set_fill_color(*C_WHITE)
        self.set_draw_color(*C_BORDER_LIGHT)
        self.set_line_width(0.2)
        self.rect(0, 269, 210, 28, 'FD')
        self.set_fill_color(*C_BRAND_MID)
        self.rect(0, 269, 210, 2, 'F')

        self.set_font('helvetica', 'B', 8.5)
        self.set_text_color(*C_BRAND_DARK)
        self.set_xy(10, 273)
        self.cell(0, 5, 'Source Point - SupersCoins Wallet Statement', 0, 1, 'C')

        self.set_font('helvetica', '', 7.5)
        self.set_text_color(*C_TEXT_MUTED)
        self.set_xy(10, 279)
        self.cell(0, 4, 'admin@sourcepoint.in  |  1 SuperCoin = Rs.1.00', 0, 1, 'C')

        self.set_font('helvetica', 'I', 7)
        self.set_text_color(*C_TEXT_MUTED)
        self.set_xy(10, 284)
        self.cell(0, 4, f'(c) {datetime.utcnow().year} Source Point. All rights reserved.   |   Page {self.page_no()}', 0, 0, 'C')


def _safe_text(val, fallback='—'):
    """Return text that the PDF's built-in Latin-1 fonts can render safely."""
    if val is None:
        text = fallback
    else:
        text = str(val).strip() or fallback

    # Keep common punctuation readable and replace the few remaining glyphs
    # that FPDF's built-in Helvetica font cannot encode.
    text = (text.replace('—', '-')
                .replace('–', '-')
                .replace('…', '...')
                .replace('₹', 'INR ')
                .replace('’', "'")
                .replace('‘', "'")
                .replace('“', '"')
                .replace('”', '"'))
    return text.encode('latin-1', 'replace').decode('latin-1')


def _wrap_pdf_text(pdf, text, width):
    """Wrap text using the active PDF font, including unbroken long values."""
    words = text.split()
    if not words:
        return ['-']

    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if pdf.get_string_width(candidate) <= width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ''

        # Split a long identifier or URL that has no whitespace.
        fragment = ''
        for char in word:
            candidate = fragment + char
            if fragment and pdf.get_string_width(candidate) > width:
                lines.append(fragment)
                fragment = char
            else:
                fragment = candidate
        current = fragment

    if current:
        lines.append(current)
    return lines or ['-']


def generate_superscoins_summary_pdf(user, wallet, transactions, invoices):
    """
    Build a premium SupersCoins transaction history PDF.
    Returns raw bytes of the PDF file.
    """
    pdf = SupersCoinSummaryPDF(user=user, wallet=wallet, transactions=transactions, invoices=invoices)
    pdf.add_page()
    now = datetime.utcnow()
    balance = float(wallet.balance) if wallet and wallet.balance else 0.0

    # ── Page background ──
    pdf.set_fill_color(*C_BG_PAGE)
    pdf.rect(0, 0, 210, 297, 'F')

    # ═══════════════════════════════════════════════════════════════
    #  Hero Header — Full-width gradient band
    # ═══════════════════════════════════════════════════════════════
    pdf.set_fill_color(*C_BRAND_DARK)
    pdf.rect(0, 0, 210, 52, 'F')
    # Accent stripe
    pdf.set_fill_color(*C_BRAND_ACCENT)
    pdf.rect(0, 52, 210, 3, 'F')

    # Company name
    pdf.set_font('helvetica', 'B', 22)
    pdf.set_text_color(*C_WHITE)
    pdf.set_xy(14, 10)
    pdf.cell(120, 10, 'Source Point', 0, 0, 'L')

    # Document type
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(*C_BRAND_PALE)
    pdf.set_xy(14, 22)
    pdf.cell(120, 6, 'SupersCoins Wallet Statement', 0, 0, 'L')

    # Date
    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(*C_BRAND_PALE)
    pdf.set_xy(14, 30)
    pdf.cell(120, 6, f'Generated: {now.strftime("%d %B %Y, %I:%M %p")} UTC', 0, 0, 'L')

    # Balance badge (right side)
    pdf.set_fill_color(*C_WHITE)
    pdf.set_draw_color(*C_BRAND_ACCENT)
    pdf.set_line_width(0.8)
    pdf.rect(130, 10, 68, 34, 'FD')

    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(*C_TEXT_MID)
    pdf.set_xy(130, 13)
    pdf.cell(68, 5, 'CURRENT BALANCE', 0, 0, 'C')

    pdf.set_font('helvetica', 'B', 20)
    pdf.set_text_color(*C_BRAND_DARK)
    pdf.set_xy(130, 20)
    pdf.cell(68, 12, f'SC {balance:,.2f}', 0, 0, 'C')

    pdf.set_font('helvetica', '', 7)
    pdf.set_text_color(*C_TEXT_MUTED)
    pdf.set_xy(130, 34)
    pdf.cell(68, 5, f'= Rs.{balance:,.2f}', 0, 0, 'C')

    # ═══════════════════════════════════════════════════════════════
    #  Account Information Card
    # ═══════════════════════════════════════════════════════════════
    y = 62
    pdf.set_fill_color(*C_WHITE)
    pdf.set_draw_color(*C_BORDER_LIGHT)
    pdf.set_line_width(0.3)
    pdf.rect(14, y, 182, 28, 'FD')

    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(*C_BRAND_DARK)
    pdf.set_xy(18, y + 3)
    pdf.cell(80, 5, 'ACCOUNT HOLDER', 0, 0, 'L')

    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(*C_TEXT_DARK)
    pdf.set_xy(18, y + 10)
    pdf.cell(80, 6, _safe_text(user.username), 0, 0, 'L')

    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(*C_TEXT_MID)
    pdf.set_xy(18, y + 18)
    pdf.cell(80, 5, _safe_text(user.email, 'No email'), 0, 0, 'L')

    # Right side info
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(*C_BRAND_DARK)
    pdf.set_xy(120, y + 3)
    pdf.cell(72, 5, 'STATEMENT PERIOD', 0, 0, 'R')

    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(*C_TEXT_DARK)
    pdf.set_xy(120, y + 10)
    pdf.cell(72, 6, 'All Time (Complete History)', 0, 0, 'R')

    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(*C_TEXT_MID)
    pdf.set_xy(120, y + 18)
    pdf.cell(72, 5, f'{len(transactions)} transaction(s)', 0, 0, 'R')

    # ═══════════════════════════════════════════════════════════════
    #  Summary Stats Row
    # ═══════════════════════════════════════════════════════════════
    y = 96
    total_credits = sum(float(t.amount) for t in transactions if t.transaction_type == SupersCoinTransactionType.CREDIT.value)
    total_debits = sum(float(t.amount) for t in transactions if t.transaction_type == SupersCoinTransactionType.DEBIT.value)

    # Credits card
    pdf.set_fill_color(236, 253, 245)  # Emerald-50
    pdf.set_draw_color(*C_CREDIT_GREEN)
    pdf.set_line_width(0.4)
    pdf.rect(14, y, 58, 22, 'FD')
    pdf.set_font('helvetica', '', 7)
    pdf.set_text_color(*C_CREDIT_GREEN)
    pdf.set_xy(14, y + 3)
    pdf.cell(58, 4, 'TOTAL CREDITED', 0, 0, 'C')
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_xy(14, y + 9)
    pdf.cell(58, 8, f'SC {total_credits:,.2f}', 0, 0, 'C')

    # Debits card
    pdf.set_fill_color(254, 242, 242)  # Red-50
    pdf.set_draw_color(*C_DEBIT_RED)
    pdf.rect(76, y, 58, 22, 'FD')
    pdf.set_font('helvetica', '', 7)
    pdf.set_text_color(*C_DEBIT_RED)
    pdf.set_xy(76, y + 3)
    pdf.cell(58, 4, 'TOTAL DEBITED', 0, 0, 'C')
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_xy(76, y + 9)
    pdf.cell(58, 8, f'SC {total_debits:,.2f}', 0, 0, 'C')

    # Net balance card
    pdf.set_fill_color(*C_BRAND_PALE)
    pdf.set_draw_color(*C_BRAND_ACCENT)
    pdf.rect(138, y, 58, 22, 'FD')
    pdf.set_font('helvetica', '', 7)
    pdf.set_text_color(*C_BRAND_DARK)
    pdf.set_xy(138, y + 3)
    pdf.cell(58, 4, 'CURRENT BALANCE', 0, 0, 'C')
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_xy(138, y + 9)
    pdf.cell(58, 8, f'SC {balance:,.2f}', 0, 0, 'C')

    # ═══════════════════════════════════════════════════════════════
    #  Transaction History Table
    # ═══════════════════════════════════════════════════════════════
    y = 126
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(*C_BRAND_DARK)
    pdf.set_xy(14, y)
    pdf.cell(182, 8, 'Transaction History', 0, 1, 'L')
    y += 10

    if not transactions:
        pdf.set_font('helvetica', 'I', 10)
        pdf.set_text_color(*C_TEXT_MUTED)
        pdf.set_xy(14, y)
        pdf.cell(182, 10, 'No transactions found.', 0, 0, 'C')
    else:
        col_widths = [29, 18, 27, 27, 27, 54]
        headers = ['Date / Time (UTC)', 'Type', 'Amount', 'Before', 'After', 'Details']

        def draw_transaction_header():
            pdf.set_fill_color(*C_BRAND_DARK)
            pdf.set_text_color(*C_WHITE)
            pdf.set_font('helvetica', 'B', 7)
            pdf.set_xy(14, pdf.get_y())
            for width, heading in zip(col_widths, headers):
                pdf.cell(width, 8, heading, 0, 0, 'C', fill=True)
            pdf.set_y(pdf.get_y() + 8)

        pdf.set_xy(14, y)
        draw_transaction_header()

        for idx, txn in enumerate(transactions):
            is_credit = txn.transaction_type == SupersCoinTransactionType.CREDIT.value
            note = _safe_text(txn.note, 'No note')
            reference_type = _safe_text(txn.reference_type, '')
            reference_id = _safe_text(txn.reference_id, '')
            admin_name = _safe_text(
                txn.admin.username if txn.admin else None,
                f'Admin ID {txn.admin_id}',
            )
            reference = ''
            if reference_type or reference_id:
                reference = 'Reference: ' + ' '.join(
                    part for part in (reference_type, f'#{reference_id}' if reference_id else '')
                    if part
                )
            details = ' | '.join(part for part in (
                f'Transaction ID: {txn.id}',
                f'Processed by: {admin_name}',
                f'Note: {note}',
                reference,
            ) if part)
            pdf.set_font('helvetica', '', 7)
            wrapped_details = _wrap_pdf_text(pdf, details, 176)
            detail_height = max(5, len(wrapped_details) * 4 + 1)
            row_height = 7

            # Keep a transaction and its complete detail block together.
            if pdf.get_y() + row_height + detail_height > 263:
                pdf.add_page()
                draw_transaction_header()

            row_fill = C_WHITE if idx % 2 == 0 else C_ROW_ALT
            row_y = pdf.get_y()
            pdf.set_fill_color(*row_fill)
            pdf.rect(14, row_y, 182, row_height, 'F')

            date_text = txn.created_at.strftime('%Y-%m-%d %H:%M') if txn.created_at else '-'
            values = [
                date_text,
                'Credit' if is_credit else 'Debit',
                f"{'+' if is_credit else '-'} {float(txn.amount):,.2f}",
                f'{float(txn.balance_before):,.2f}',
                f'{float(txn.balance_after):,.2f}',
                'See details below',
            ]
            x_pos = 14
            for col_idx, (width, value) in enumerate(zip(col_widths, values)):
                pdf.set_xy(x_pos, row_y)
                pdf.set_fill_color(*row_fill)
                if col_idx == 1:
                    pdf.set_text_color(*(C_CREDIT_GREEN if is_credit else C_DEBIT_RED))
                    pdf.set_font('helvetica', 'B', 7)
                elif col_idx == 2:
                    pdf.set_text_color(*(C_CREDIT_GREEN if is_credit else C_DEBIT_RED))
                    pdf.set_font('helvetica', 'B', 7)
                else:
                    pdf.set_text_color(*C_TEXT_DARK)
                    pdf.set_font('helvetica', '', 7)
                pdf.cell(width, row_height, value, 0, 0, 'C', fill=True)
                x_pos += width

            detail_y = row_y + row_height
            pdf.set_fill_color(*row_fill)
            pdf.rect(14, detail_y, 182, detail_height, 'F')
            pdf.set_draw_color(*C_BORDER_LIGHT)
            pdf.line(14, detail_y, 196, detail_y)
            pdf.set_font('helvetica', '', 7)
            pdf.set_text_color(*C_TEXT_MID)
            pdf.set_xy(16, detail_y + 0.5)
            pdf.multi_cell(178, 4, '\n'.join(wrapped_details), 0, 'L')
            pdf.set_y(detail_y + detail_height)

    # ═══════════════════════════════════════════════════════════════
    #  Invoice History Table (if any)
    # ═══════════════════════════════════════════════════════════════
    if invoices:
        if pdf.get_y() + 20 > 263:
            pdf.add_page()

        pdf.ln(8)
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_text_color(*C_BRAND_DARK)
        pdf.set_xy(14, pdf.get_y())
        pdf.cell(182, 8, 'Invoice History', 0, 1, 'L')
        pdf.set_y(pdf.get_y() + 2)

        inv_cols = [38, 30, 27, 44, 43]
        inv_headers = ['Invoice #', 'Amount', 'Status', 'Created (UTC)', 'Due Date']

        def draw_invoice_header():
            pdf.set_fill_color(*C_BRAND_DARK)
            pdf.set_text_color(*C_WHITE)
            pdf.set_font('helvetica', 'B', 7)
            pdf.set_xy(14, pdf.get_y())
            for width, heading in zip(inv_cols, inv_headers):
                pdf.cell(width, 8, heading, 0, 0, 'C', fill=True)
            pdf.set_y(pdf.get_y() + 8)

        draw_invoice_header()

        for idx, inv in enumerate(invoices):
            row_fill = C_WHITE if idx % 2 == 0 else C_ROW_ALT
            detail_parts = [
                f"Description: {_safe_text(inv.description, 'No description')}",
                f"Spending category: {_safe_text(inv.spending_category, 'Not specified')}",
                f"Booking details: {_safe_text(inv.booking_details, 'Not specified')}",
                f"Notes: {_safe_text(inv.notes, 'None')}",
                f"Paid at (UTC): {inv.paid_at.strftime('%Y-%m-%d %H:%M') if inv.paid_at else 'Not paid'}",
            ]
            if inv.transaction_id is not None:
                detail_parts.append(f'Transaction ID: {inv.transaction_id}')
            detail_text = ' | '.join(detail_parts)
            pdf.set_font('helvetica', '', 7)
            wrapped_details = _wrap_pdf_text(pdf, detail_text, 176)
            detail_height = max(5, len(wrapped_details) * 4 + 1)
            row_height = 7

            if pdf.get_y() + row_height + detail_height > 263:
                pdf.add_page()
                draw_invoice_header()

            row_y = pdf.get_y()
            pdf.set_fill_color(*row_fill)
            status_text = _safe_text(inv.status)
            if status_text == 'Paid':
                status_color = C_CREDIT_GREEN
            elif status_text == 'Cancelled':
                status_color = C_DEBIT_RED
            else:
                status_color = C_BRAND_ACCENT

            values = [
                _safe_text(inv.invoice_number),
                f'SC {float(inv.amount):,.2f}',
                status_text,
                inv.created_at.strftime('%Y-%m-%d %H:%M') if inv.created_at else '-',
                inv.due_date.strftime('%Y-%m-%d') if inv.due_date else 'Not set',
            ]
            x_pos = 14
            for col_idx, (width, value) in enumerate(zip(inv_cols, values)):
                pdf.set_xy(x_pos, row_y)
                pdf.set_fill_color(*row_fill)
                pdf.set_font('helvetica', 'B' if col_idx in (1, 2) else '', 7)
                if col_idx == 1:
                    pdf.set_text_color(*C_BRAND_DARK)
                elif col_idx == 2:
                    pdf.set_text_color(*status_color)
                else:
                    pdf.set_text_color(*C_TEXT_DARK)
                pdf.cell(width, row_height, value, 0, 0, 'C', fill=True)
                x_pos += width

            detail_y = row_y + row_height
            pdf.set_fill_color(*row_fill)
            pdf.rect(14, detail_y, 182, detail_height, 'F')
            pdf.set_draw_color(*C_BORDER_LIGHT)
            pdf.line(14, detail_y, 196, detail_y)
            pdf.set_font('helvetica', '', 7)
            pdf.set_text_color(*C_TEXT_MID)
            pdf.set_xy(16, detail_y + 0.5)
            pdf.multi_cell(178, 4, '\n'.join(wrapped_details), 0, 'L')
            pdf.set_y(detail_y + detail_height)

    # ── Disclaimer ──
    if pdf.get_y() > 245:
        pdf.add_page()
    pdf.ln(10)
    pdf.set_font('helvetica', 'I', 7)
    pdf.set_text_color(*C_TEXT_MUTED)
    pdf.set_x(14)
    pdf.multi_cell(182, 4,
                   'This is a computer-generated statement and does not require a signature. '
                   'For any discrepancies, please contact admin@sourcepoint.in. '
                   '1 SuperCoin = Rs.1.00 in booking value.',
                   align='C')

    # Return PDF bytes
    return pdf.output()
