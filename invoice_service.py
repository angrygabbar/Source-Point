# Source Point/invoice_service.py

from fpdf import FPDF
from bs4 import BeautifulSoup
from datetime import datetime
import re


class PDF(FPDF):
    """
    Base PDF class with branded emerald header + footer on every page.
    Colours are passed in from InvoiceGenerator so the PDF class
    can render them without depending on the generator instance.
    """

    def __init__(self, title="Document",
                 c_brand_dark=(65, 56, 190),
                 c_brand_mid=(79, 70, 229),
                 c_brand_pale=(224, 231, 255),
                 c_bg_page=(240, 242, 245),
                 c_text_muted=(107, 114, 128),
                 c_text_light=(156, 163, 175),
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title       = title
        self.c_brand_dark    = c_brand_dark
        self.c_brand_mid     = c_brand_mid
        self.c_brand_pale    = c_brand_pale
        self.c_bg_page       = c_bg_page
        self.c_text_muted    = c_text_muted
        self.c_text_light    = c_text_light
        # Reserve 28 mm at page bottom for the footer bar
        self.set_auto_page_break(auto=True, margin=28)

    def header(self):
        """Compact branded header bar shown on pages 2+."""
        if self.page_no() == 1:
            return  # page 1 has its own full header drawn manually

        # Grey background for the whole page (carry over from page 1)
        self.set_fill_color(*self.c_bg_page)
        self.rect(0, 0, 210, 297, 'F')

        # Compact indigo header bar (12 mm tall) — matches website nav
        self.set_fill_color(*self.c_brand_dark)
        self.rect(0, 0, 210, 12, 'F')

        # Brand name left
        self.set_font('helvetica', 'B', 9)
        self.set_text_color(*self.c_brand_pale)
        self.set_xy(10, 2)
        self.cell(80, 8, 'Source Point', 0, 0, 'L')

        # Invoice title right
        self.set_font('helvetica', '', 8)
        self.set_text_color(*self.c_brand_pale)
        self.set_xy(100, 2)
        self.cell(100, 8, self.doc_title, 0, 0, 'R')

        # Advance cursor past the header bar
        self.set_y(16)

    def footer(self):
        """Branded footer bar on every page."""
        # White footer card
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(229, 231, 235)
        self.set_line_width(0.2)
        self.rect(0, 269, 210, 28, 'FD')

        # Indigo/Violet top accent stripe on footer
        self.set_fill_color(*self.c_brand_mid)
        self.rect(0, 269, 210, 2, 'F')

        # Thank-you text
        self.set_font('helvetica', 'B', 8.5)
        self.set_text_color(*self.c_brand_dark)
        self.set_xy(10, 273)
        self.cell(0, 5, 'Thank you for shopping with Source Point!', 0, 1, 'C')

        # Support email
        self.set_font('helvetica', '', 7.5)
        self.set_text_color(*self.c_text_muted)
        self.set_xy(10, 279)
        self.cell(0, 4, 'support@sourcepoint.in', 0, 1, 'C')

        # Page number + copyright
        self.set_font('helvetica', 'I', 7)
        self.set_text_color(*self.c_text_light)
        self.set_xy(10, 284)
        self.cell(0, 4,
                  f'(c) 2025 Source Point. All rights reserved.   |   Page {self.page_no()}',
                  0, 0, 'C')



class InvoiceGenerator:
    """
    Premium e-commerce invoice PDF generator.
    Aesthetic: Emerald Green (#059669) + Light Grey — matching the ecommerce_invoice_email.html template.
    """

    def __init__(self, invoice):
        self.invoice = invoice

        # ── Brand Colour Palette — matches Source Point website ──────────────
        # Primary:  Indigo-600  #4F46E5  → RGB(79, 70, 229)
        # Gradient: Violet-600  #7C3AED  → RGB(124, 58, 237)
        # Dark bg:  Indigo-900  #312E81  → RGB(49, 46, 129)
        self.c_brand_dark    = (49,  46, 129)    # Indigo-900  header bg
        self.c_brand_mid     = (79,  70, 229)    # Indigo-600  primary
        self.c_brand_violet  = (124, 58, 237)    # Violet-600  gradient end
        self.c_brand_pale    = (224, 231, 255)   # Indigo-100  light tint
        self.c_brand_xpale   = (238, 242, 255)   # Indigo-50   very pale
        self.c_brand_border  = (199, 210, 254)   # Indigo-200  border
        self.c_brand_accent  = (99,  102, 241)   # Indigo-500  table header

        self.c_bg_page       = (240, 241, 247)   # Neutral page bg
        self.c_bg_card       = (255, 255, 255)
        self.c_bg_row_alt    = (249, 250, 251)
        self.c_text_dark     = (17,  24,  39)
        self.c_text_mid      = (55,  65,  81)
        self.c_text_muted    = (107, 114, 128)
        self.c_text_light    = (156, 163, 175)
        self.c_border        = (229, 231, 235)
        self.c_border_dark   = (209, 213, 219)

        # Pass colours into PDF so header() / footer() can use them
        self.pdf = PDF(
            title=f"Invoice #{invoice.invoice_number}",
            c_brand_dark  = self.c_brand_dark,
            c_brand_mid   = self.c_brand_mid,
            c_brand_pale  = self.c_brand_pale,
            c_bg_page     = self.c_bg_page,
            c_text_muted  = self.c_text_muted,
            c_text_light  = self.c_text_light,
        )
        self.pdf.add_page()

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    def generate_pdf(self):
        self._draw_page_background()
        self._draw_header()
        self._draw_meta_strip()
        self._draw_address_grid()
        self._draw_items_table()
        self._draw_totals()
        self._draw_info_panel()
        # Footer is handled by PDF.footer() on every page — no manual call needed
        return bytes(self.pdf.output())

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _clean_text(self, text):
        """Sanitises text for Helvetica (Latin-1) rendering."""
        if text is None:
            return ""
        text = str(text)
        replacements = {
            '\u200b': '', '\xa0': ' ',
            '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-',
            '\u20b9': 'Rs. ', '\u2022': '-', '\u2026': '...',
        }
        for char, rep in replacements.items():
            text = text.replace(char, rep)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def _set_fill(self, rgb):
        self.pdf.set_fill_color(*rgb)

    def _set_text(self, rgb):
        self.pdf.set_text_color(*rgb)

    def _set_draw(self, rgb):
        self.pdf.set_draw_color(*rgb)

    def _thin_line(self):
        self.pdf.set_line_width(0.2)

    def _thick_line(self):
        self.pdf.set_line_width(0.4)

    # ──────────────────────────────────────────────────────────────────────────
    # Sections
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_page_background(self):
        """Light grey page background."""
        self._set_fill(self.c_bg_page)
        self.pdf.rect(0, 0, 210, 297, 'F')

    def _draw_header(self):
        """
        Branded header bar matching the Source Point website nav:
          LEFT  — Indigo-to-Violet gradient badge with stacked-layers icon + 'Source Point'
          RIGHT — 'INVOICE' label + invoice number
        """
        hh = 40  # header height mm

        # ── Deep indigo background ────────────────────────────────────────────
        self._set_fill(self.c_brand_dark)
        self.pdf.rect(0, 0, 210, hh, 'F')

        # Violet gradient accent (right 1/3 fades darker)
        self._set_fill(self.c_brand_violet)
        self.pdf.rect(130, 0, 80, hh, 'F')

        # Bright indigo stripe at bottom of header
        self._set_fill(self.c_brand_mid)
        self.pdf.rect(0, hh, 210, 2, 'F')

        # ── Logo badge — mimics fa-layer-group on indigo-violet badge ─────────
        bx, by, bw, bh = 10, 8, 18, 18

        # Outer badge: indigo-600 fill, rounded by drawing overlapping rect
        self._set_fill(self.c_brand_mid)
        self.pdf.rect(bx, by, bw, bh, 'F')

        # Draw 3 stacked horizontal bars inside badge (fa-layer-group concept)
        bar_w   = 12
        bar_h   = 2.2
        bar_x   = bx + (bw - bar_w) / 2
        bar_gap = 3.5
        self._set_fill((255, 255, 255))
        for i in range(3):
            bar_y = by + 3.5 + i * bar_gap
            self.pdf.rect(bar_x, bar_y, bar_w, bar_h, 'F')
            # Taper inner two bars slightly for stacked-layers effect
            if i > 0:
                self.pdf.rect(bar_x + 1.5, bar_y, bar_w - 3, bar_h, 'F')

        # ── Brand name ────────────────────────────────────────────────────────
        self.pdf.set_font('helvetica', 'B', 17)
        self._set_text((255, 255, 255))
        self.pdf.set_xy(bx + bw + 4, by + 1)
        self.pdf.cell(85, 9, 'Source Point', 0, 0, 'L')

        # Tagline
        self.pdf.set_font('helvetica', '', 7.5)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(bx + bw + 4, by + 11)
        self.pdf.cell(85, 5, 'Your Trusted Online Store', 0, 0, 'L')

        # ── INVOICE label (right side) ────────────────────────────────────────
        self.pdf.set_font('helvetica', 'B', 26)
        self._set_text((255, 255, 255))
        self.pdf.set_xy(120, 5)
        self.pdf.cell(80, 12, 'INVOICE', 0, 0, 'R')

        # Invoice number pill
        inv_label = f'# {self._clean_text(self.invoice.invoice_number)}'
        self.pdf.set_font('helvetica', 'B', 9)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(130, 20)
        self.pdf.cell(70, 8, inv_label, 0, 0, 'R')

        # TAX INVOICE sub-label
        self.pdf.set_font('helvetica', '', 7)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(130, 29)
        self.pdf.cell(70, 5, 'TAX INVOICE', 0, 0, 'R')

        self.pdf.set_y(hh + 6)

    def _draw_meta_strip(self):
        """
        4-column meta info bar: Invoice Date | Due Date | Status | Terms
        """
        sx = 10
        sy = self.pdf.get_y()
        sw = 190
        sh = 18

        # White card background + subtle border
        self._set_fill(self.c_bg_card)
        self._set_draw(self.c_border)
        self._thin_line()
        self.pdf.rect(sx, sy, sw, sh, 'FD')

        # Vertical dividers
        col_w = sw / 4
        for i in range(1, 4):
            self._set_draw(self.c_border)
            self.pdf.line(sx + col_w * i, sy, sx + col_w * i, sy + sh)

        def meta_col(col_idx, label, value, value_color=None):
            cx = sx + col_w * col_idx + 3
            self.pdf.set_font('helvetica', 'B', 6.5)
            self._set_text(self.c_brand_mid)
            self.pdf.set_xy(cx, sy + 3)
            self.pdf.cell(col_w - 6, 4, label.upper(), 0, 1, 'L')
            self.pdf.set_font('helvetica', 'B', 9)
            self._set_text(value_color or self.c_text_dark)
            self.pdf.set_xy(cx, sy + 7)
            self.pdf.cell(col_w - 6, 6, self._clean_text(value), 0, 0, 'L')

        inv_date = self.invoice.created_at.strftime('%d %b %Y') if self.invoice.created_at else 'N/A'
        due_date = self.invoice.due_date.strftime('%d %b %Y') if self.invoice.due_date else 'On Receipt'
        status   = str(self.invoice.status).title() if self.invoice.status else 'Processing'

        meta_col(0, 'Invoice Date', inv_date)
        meta_col(1, 'Due Date',     due_date)
        meta_col(2, 'Status',       status, self.c_brand_mid)
        meta_col(3, 'Payment Terms','Due on Receipt')

        self.pdf.set_y(sy + sh + 6)

    def _draw_address_grid(self):
        """
        Two-column card: Bill To | Ship To
        """
        sx     = 10
        sy     = self.pdf.get_y()
        col_w  = 91
        gap    = 8
        sh     = 32

        for col, (heading, name, address) in enumerate([
            ('Bill To',
             self._clean_text(self.invoice.recipient_name),
             self._clean_text(self.invoice.bill_to_address or '')),
            ('Ship To',
             self._clean_text(self.invoice.recipient_name),
             self._clean_text(self.invoice.ship_to_address or self.invoice.bill_to_address or '')),
        ]):
            cx = sx + col * (col_w + gap)

            # Card background
            self._set_fill(self.c_bg_card)
            self._set_draw(self.c_border)
            self._thin_line()
            self.pdf.rect(cx, sy, col_w, sh, 'FD')

            # Emerald top accent bar
            self._set_fill(self.c_brand_mid)
            self.pdf.rect(cx, sy, col_w, 2.5, 'F')

            # Heading
            self.pdf.set_font('helvetica', 'B', 7)
            self._set_text(self.c_brand_dark)
            self.pdf.set_xy(cx + 3, sy + 4)
            self.pdf.cell(col_w - 6, 4, heading.upper(), 0, 1, 'L')

            # Name
            self.pdf.set_font('helvetica', 'B', 9)
            self._set_text(self.c_text_dark)
            self.pdf.set_xy(cx + 3, sy + 9)
            self.pdf.cell(col_w - 6, 5, name, 0, 1, 'L')

            # Address (multi-cell)
            self.pdf.set_font('helvetica', '', 7.5)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(cx + 3, sy + 14)
            if address:
                self.pdf.multi_cell(col_w - 6, 4, address, 0, 'L')
            else:
                self.pdf.cell(col_w - 6, 4, '—', 0, 0, 'L')

        self.pdf.set_y(sy + sh + 6)

    def _draw_items_table(self):
        """
        Product items table with columns: # | Description & SKU | Qty | Unit Price | Subtotal
        """
        sx   = 10
        sy   = self.pdf.get_y()
        tw   = 190  # total width
        rh   = 10   # row height

        # Column widths
        c_no    = 10
        c_desc  = 88
        c_sku   = 28
        c_qty   = 16
        c_price = 24
        c_sub   = tw - c_no - c_desc - c_sku - c_qty - c_price  # 24

        # ── Header row ────────────────────────────────────────────────────────
        self._set_fill(self.c_brand_dark)
        self._set_draw(self.c_brand_dark)
        self._thin_line()
        self.pdf.set_xy(sx, sy)
        self.pdf.rect(sx, sy, tw, rh, 'F')

        headers = [
            ('#',           c_no,    'C'),
            ('Item & Description', c_desc, 'L'),
            ('SKU / Ref',   c_sku,   'L'),
            ('Qty',         c_qty,   'C'),
            ('Unit Price',  c_price, 'R'),
            ('Subtotal',    c_sub,   'R'),
        ]
        self.pdf.set_font('helvetica', 'B', 7.5)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(sx, sy)
        x = sx
        for label, w, align in headers:
            pad_x = 3 if align == 'L' else 0
            self.pdf.set_xy(x + pad_x, sy + 1.5)
            self.pdf.cell(w - pad_x, rh - 2, label, 0, 0, align)
            x += w

        sy += rh

        # ── Data rows ─────────────────────────────────────────────────────────
        LINE_H   = 4.5   # must match multi_cell line height below
        DESC_PAD = 4     # horizontal padding inside desc cell
        IN_STOCK_H = 5   # height of the "In Stock" label row

        for idx, item in enumerate(self.invoice.items):
            desc     = self._clean_text(item.description)
            sku      = f'SP-{item.id:04d}'
            qty      = str(item.quantity)
            price    = f'Rs.{float(item.price):,.2f}'
            subtotal = f'Rs.{float(item.quantity * item.price):,.2f}'

            # ── Accurate row-height using font metrics ─────────────────────
            # Set EXACTLY the same font used to render the description
            self.pdf.set_font('helvetica', 'B', 8.5)
            avail_w = c_desc - DESC_PAD  # usable width inside desc cell

            # Word-wrap simulation: walk words and count line breaks
            num_lines = 1
            line_w    = 0.0
            for word in desc.split(' '):
                word_w = self.pdf.get_string_width(word + ' ')
                if line_w + word_w > avail_w and line_w > 0:
                    num_lines += 1
                    line_w = word_w
                else:
                    line_w += word_w

            # row_h = top-pad(2) + text lines + gap before "In Stock" + In Stock label + bottom-pad(2)
            row_h = max(14, 2 + num_lines * LINE_H + 2 + IN_STOCK_H + 2)

            # ── Draw row background ────────────────────────────────────────
            row_bg = self.c_bg_card if idx % 2 == 0 else self.c_bg_row_alt
            self._set_fill(row_bg)
            self._set_draw(self.c_border)
            self._thin_line()
            self.pdf.rect(sx, sy, tw, row_h, 'FD')

            # Vertical column dividers
            self._set_draw(self.c_border)
            x = sx
            for w in [c_no, c_desc, c_sku, c_qty, c_price]:
                x += w
                self.pdf.line(x, sy, x, sy + row_h)

            # Row number
            self.pdf.set_font('helvetica', '', 8)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(sx, sy + (row_h - 8) / 2)
            self.pdf.cell(c_no, 8, str(idx + 1), 0, 0, 'C')

            # Description (multi-line)
            self.pdf.set_font('helvetica', 'B', 8.5)
            self._set_text(self.c_text_dark)
            self.pdf.set_xy(sx + c_no + 2, sy + 2)
            self.pdf.multi_cell(c_desc - 4, 4.5, desc, 0, 'L')

            # In-stock label below description
            self.pdf.set_font('helvetica', '', 6.5)
            self._set_text(self.c_brand_accent)
            self.pdf.set_xy(sx + c_no + 2, sy + (row_h - 5))
            self.pdf.cell(c_desc - 4, 4, 'In Stock', 0, 0, 'L')

            # SKU
            self.pdf.set_font('helvetica', '', 7.5)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(sx + c_no + c_desc + 2, sy + (row_h - 8) / 2)
            self.pdf.cell(c_sku - 4, 8, sku, 0, 0, 'L')

            # Qty  (centred)
            self.pdf.set_font('helvetica', 'B', 9)
            self._set_text(self.c_text_mid)
            self.pdf.set_xy(sx + c_no + c_desc + c_sku, sy + (row_h - 8) / 2)
            self.pdf.cell(c_qty, 8, qty, 0, 0, 'C')

            # Unit price
            self.pdf.set_font('helvetica', '', 8.5)
            self._set_text(self.c_text_mid)
            self.pdf.set_xy(sx + c_no + c_desc + c_sku + c_qty, sy + (row_h - 8) / 2)
            self.pdf.cell(c_price - 2, 8, price, 0, 0, 'R')

            # Subtotal (emerald)
            self.pdf.set_font('helvetica', 'B', 9)
            self._set_text(self.c_brand_mid)
            self.pdf.set_xy(sx + c_no + c_desc + c_sku + c_qty + c_price, sy + (row_h - 8) / 2)
            self.pdf.cell(c_sub - 2, 8, subtotal, 0, 0, 'R')

            sy += row_h

        self.pdf.set_y(sy + 5)

    def _draw_totals(self):
        """
        Right-aligned totals block: Subtotal | Tax | Total.
        """
        sx = 10
        sy = self.pdf.get_y()
        bw = 80   # block width
        bx = 210 - 10 - bw  # aligned right

        rows = [
            ('Subtotal',   f'Rs.{float(self.invoice.subtotal):,.2f}',      False),
            ('Tax & Fees', f'Rs.{float(self.invoice.tax):,.2f}',           False),
        ]

        rh = 8
        # Light rows
        self._set_draw(self.c_border)
        self._thin_line()
        for i, (label, value, _) in enumerate(rows):
            row_bg = self.c_bg_card if i % 2 == 0 else self.c_bg_row_alt
            self._set_fill(row_bg)
            self.pdf.rect(bx, sy, bw, rh, 'FD')
            self.pdf.set_font('helvetica', '', 8)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(bx + 4, sy + 1)
            self.pdf.cell(bw / 2, rh - 2, label, 0, 0, 'L')
            self.pdf.set_font('helvetica', 'B', 8)
            self._set_text(self.c_text_dark)
            self.pdf.set_xy(bx + bw / 2, sy + 1)
            self.pdf.cell(bw / 2 - 4, rh - 2, value, 0, 0, 'R')
            sy += rh

        # Dark emerald total row
        th = 12
        self._set_fill(self.c_brand_dark)
        self._set_draw(self.c_brand_dark)
        self.pdf.rect(bx, sy, bw, th, 'F')
        self.pdf.set_font('helvetica', '', 9)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(bx + 4, sy + 2)
        self.pdf.cell(bw / 2, th - 4, 'Total (INR)', 0, 0, 'L')
        self.pdf.set_font('helvetica', 'B', 12)
        self._set_text((255, 255, 255))
        self.pdf.set_xy(bx + bw / 2, sy + 1)
        self.pdf.cell(bw / 2 - 4, th - 2, f'Rs.{float(self.invoice.total_amount):,.2f}', 0, 0, 'R')

        self.pdf.set_y(self.pdf.get_y() + th + 8)

    def _draw_info_panel(self):
        """
        Pale emerald panel: Tracking | Shipping Address | Return Policy
        Mirrors the tracking/info box in the email template.
        """
        sx       = 10
        pw       = 190
        LABEL_X  = sx + 6        # Left edge of label column
        VALUE_X  = sx + 50       # Left edge of value column
        VALUE_W  = pw - 54       # Available width for values
        PAD_TOP  = 4             # Padding above first row
        DIVIDER  = 1.5           # Height of divider line
        ROW_GAP  = 3             # Gap between divider and next row label

        # ── Content strings ────────────────────────────────────────────────────
        track_text  = self._clean_text(self.invoice.payment_details or 'IN TRANSIT — Processing')
        ship_text   = self._clean_text(self.invoice.ship_to_address or self.invoice.bill_to_address or 'Same as billing address.')
        policy_text = ('Items eligible for return within 7 days of delivery if unused and '
                       'in original packaging. Refunds processed within 5-7 business days '
                       'of return receipt. Digital goods and gift cards are non-refundable.')

        # ── Helper: measure how many lines a string needs ────────────────────
        def wrap_lines(text, font_style, font_size, avail_w, line_h):
            self.pdf.set_font('helvetica', font_style, font_size)
            n, line_w = 1, 0.0
            for word in text.split(' '):
                ww = self.pdf.get_string_width(word + ' ')
                if line_w + ww > avail_w and line_w > 0:
                    n += 1; line_w = ww
                else:
                    line_w += ww
            return n * line_h

        # ── Pre-calculate each row's text height ─────────────────────────────
        TRACK_LH   = 4.5
        SHIP_LH    = 4.0
        POLICY_LH  = 3.8
        LABEL_H    = 5.0          # fixed height for the label cell

        track_h  = max(LABEL_H, wrap_lines(track_text,  'B',  8,   VALUE_W, TRACK_LH))
        ship_h   = max(LABEL_H, wrap_lines(ship_text,   '',   7.5, VALUE_W, SHIP_LH))
        policy_h = max(LABEL_H, wrap_lines(policy_text, '',   7,   VALUE_W, POLICY_LH))

        # Row heights (label top-pad + text + bottom-pad)
        ROW1_H = PAD_TOP    + track_h  + 2
        ROW2_H = ROW_GAP    + ship_h   + 2
        ROW3_H = ROW_GAP    + policy_h + 3
        ph     = ROW1_H + DIVIDER + ROW2_H + DIVIDER + ROW3_H

        # Optional notes height
        notes_h = 0
        if self.invoice.notes:
            notes_h = max(6, wrap_lines(self._clean_text(self.invoice.notes), 'I', 7.5, pw - 4, 4)) + 6

        # ── Make sure there is enough room on the current page ───────────────
        # Footer starts at y=269, reserve 3 mm margin
        FOOTER_Y = 269
        sy = self.pdf.get_y()
        if sy + ph + notes_h + 4 > FOOTER_Y - 3:
            self.pdf.add_page()
            sy = self.pdf.get_y()

        # ── Disable auto page break for the duration of the panel draw ───────
        self.pdf.set_auto_page_break(False)

        # ── Panel background + left bar ───────────────────────────────────────
        self._set_fill(self.c_brand_xpale)
        self._set_draw(self.c_brand_border)
        self._thin_line()
        self.pdf.rect(sx, sy, pw, ph, 'FD')
        self._set_fill(self.c_brand_mid)
        self.pdf.rect(sx, sy, 3, ph, 'F')

        # ── Row 1: Tracking ──────────────────────────────────────────────────
        ry = sy + PAD_TOP
        self.pdf.set_font('helvetica', 'B', 8)
        self._set_text(self.c_brand_dark)
        self.pdf.set_xy(LABEL_X, ry)
        self.pdf.cell(40, LABEL_H, 'Tracking Number', 0, 0, 'L')
        self.pdf.set_font('helvetica', 'B', 8)
        self._set_text(self.c_brand_mid)
        self.pdf.set_xy(VALUE_X, ry)
        self.pdf.multi_cell(VALUE_W, TRACK_LH, track_text, 0, 'L')
        ry += track_h + 2

        # Divider 1
        self._set_draw(self.c_brand_border)
        self.pdf.line(LABEL_X, ry, sx + pw - 4, ry)
        ry += DIVIDER

        # ── Row 2: Shipping Address ───────────────────────────────────────────
        ry += ROW_GAP
        self.pdf.set_font('helvetica', 'B', 8)
        self._set_text(self.c_brand_dark)
        self.pdf.set_xy(LABEL_X, ry)
        self.pdf.cell(40, LABEL_H, 'Shipping Address', 0, 0, 'L')
        self.pdf.set_font('helvetica', '', 7.5)
        self._set_text(self.c_text_muted)
        self.pdf.set_xy(VALUE_X, ry)
        self.pdf.multi_cell(VALUE_W, SHIP_LH, ship_text, 0, 'L')
        ry += ship_h + 2

        # Divider 2
        self._set_draw(self.c_brand_border)
        self.pdf.line(LABEL_X, ry, sx + pw - 4, ry)
        ry += DIVIDER

        # ── Row 3: Return & Refund Policy ────────────────────────────────────
        ry += ROW_GAP
        self.pdf.set_font('helvetica', 'B', 8)
        self._set_text(self.c_brand_dark)
        self.pdf.set_xy(LABEL_X, ry)
        self.pdf.cell(45, LABEL_H, 'Return & Refund Policy', 0, 0, 'L')
        self.pdf.set_font('helvetica', '', 7)
        self._set_text(self.c_text_muted)
        self.pdf.set_xy(VALUE_X, ry)
        self.pdf.multi_cell(VALUE_W, POLICY_LH, policy_text, 0, 'L')

        # ── Optional notes (below the panel) ─────────────────────────────────
        if self.invoice.notes:
            note_y = sy + ph + 4
            self.pdf.set_font('helvetica', 'I', 7.5)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(sx, note_y)
            self.pdf.multi_cell(pw, 4, f'Note: {self._clean_text(self.invoice.notes)}', 0, 'L')

        # ── Re-enable auto page break and advance cursor ──────────────────────
        self.pdf.set_auto_page_break(auto=True, margin=28)
        self.pdf.set_y(sy + ph + notes_h + 4)


class BrdGenerator:
    def __init__(self, project):
        self.project = project
        self.pdf = PDF(title=f"BRD: {project.name}")
        self.pdf.add_page()
        self.pdf.set_font("helvetica", size=12)
        
        # Enhanced Professional Color Palette
        self.primary_color = (37, 99, 235)      # Blue-600
        self.secondary_color = (79, 70, 229)    # Indigo-600
        self.accent_color = (16, 185, 129)      # Emerald-500
        self.header_bg = (239, 246, 255)        # Blue-50
        self.section_bg = (248, 250, 252)       # Slate-50
        self.table_header_bg = (219, 234, 254)  # Blue-100
        self.table_alt_row = (248, 250, 252)    # Slate-50
        self.text_color = (30, 41, 59)          # Slate-800
        self.text_secondary = (71, 85, 105)     # Slate-600
        self.border_color = (203, 213, 225)     # Slate-300

    def generate_pdf(self):
        self._add_cover_page()
        self.pdf.add_page()  # Start content on new page
        self._add_table_of_contents()
        self.pdf.add_page()  # Start sections on new page
        self._add_brd_content()
        return bytes(self.pdf.output())

    def _clean_text(self, text):
        """Sanitizes text to be compatible with Helvetica (Latin-1) font."""
        if text is None:
            return ""
        text = str(text)
        replacements = {
            '\u200b': '',  # Zero-width space
            '\xa0': ' ',   # Non-breaking space
            '’': "'",      # Smart quotes
            '‘': "'",
            '”': '"',
            '“': '"',
            '–': '-',      # En-dash
            '—': '-',      # Em-dash
            '₹': 'Rs. ',
            '•': '-',
            '…': '...',
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def _sanitize_html(self, html_content):
        """Enhanced HTML sanitization with better table and list support."""
        if not html_content:
            return ""
        
        # Pre-processing: Standardize Characters
        html_content = self._clean_text(html_content)
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Enhanced Table Processing
        for table in soup.find_all("table"):
            table['border'] = '1'
            table['width'] = '100%'
            table['cellpadding'] = '8'
            table['cellspacing'] = '0'
            table['style'] = 'border-collapse: collapse;'
            
            # Style table headers
            for th in table.find_all(['th']):
                th['bgcolor'] = '#dbeafe'  # Light blue background
                th['style'] = 'font-weight: bold; padding: 8px; text-align: left;'
            
            # Add alternating row colors
            rows = table.find_all('tr')
            for idx, row in enumerate(rows):
                if idx > 0 and idx % 2 == 0:  # Skip header, alternate others
                    row['bgcolor'] = '#f8fafc'
                # Style cells
                for td in row.find_all('td'):
                    td['style'] = 'padding: 8px; border: 1px solid #cbd5e1;'

        # Enhanced List Processing
        for ul in soup.find_all("ul"):
            ul['style'] = 'margin-left: 20px; margin-bottom: 10px;'
            for li in ul.find_all('li'):
                li.insert(0, '• ')
        
        for ol in soup.find_all("ol"):
            ol['style'] = 'margin-left: 20px; margin-bottom: 10px;'
        
        # Preserve text formatting
        for strong in soup.find_all(['strong', 'b']):
            strong.name = 'b'
        
        for em in soup.find_all(['em', 'i']):
            em.name = 'i'
        
        # Better paragraph handling
        for p in soup.find_all("p"):
            if p.get_text(strip=True):
                p['style'] = 'margin-bottom: 8px; line-height: 1.5;'
            else:
                p.decompose()

        # Convert headings to bold text with proper spacing
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading.name = 'b'
            heading.insert_after(soup.new_tag("br"))
            heading.insert_after(soup.new_tag("br"))
        
        html_str = str(soup)
        # Clean up excessive breaks
        html_str = re.sub(r'(<br\s*/?>\s*){3,}', '<br/><br/>', html_str)
        
        return html_str

    def _add_section_divider(self):
        """Adds a visual divider between sections."""
        self.pdf.ln(3)
        self.pdf.set_draw_color(*self.border_color)
        self.pdf.set_line_width(0.5)
        y = self.pdf.get_y()
        self.pdf.line(10, y, 200, y)
        self.pdf.ln(5)

    def _add_cover_page(self):
        """Creates an enhanced professional cover page."""
        # Gradient-like header with multiple color bands
        self.pdf.set_fill_color(*self.primary_color)
        self.pdf.rect(0, 0, 210, 80, 'F')
        
        # Accent stripe
        self.pdf.set_fill_color(*self.accent_color)
        self.pdf.rect(0, 80, 210, 5, 'F')
        
        # Main title
        self.pdf.set_y(30)
        self.pdf.set_font('helvetica', 'B', 36)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.cell(0, 12, "Business Requirement", 0, 1, 'C')
        self.pdf.cell(0, 12, "Document", 0, 1, 'C')
        
        # Decorative line
        self.pdf.set_y(95)
        self.pdf.set_draw_color(*self.secondary_color)
        self.pdf.set_line_width(1)
        self.pdf.line(60, 95, 150, 95)
        
        # Project information box
        self.pdf.set_y(110)
        self.pdf.set_font('helvetica', '', 12)
        self.pdf.set_text_color(*self.text_secondary)
        self.pdf.cell(0, 8, "PROJECT NAME:", 0, 1, 'C')
        
        self.pdf.set_font('helvetica', 'B', 26)
        self.pdf.set_text_color(*self.primary_color)
        self.pdf.multi_cell(0, 12, self._clean_text(self.project.name), 0, 'C')
        
        # Metadata section with box
        self.pdf.set_y(160)
        self.pdf.set_fill_color(*self.section_bg)
        self.pdf.set_draw_color(*self.border_color)
        self.pdf.rect(40, 160, 130, 45, 'FD')
        
        self.pdf.set_y(165)
        self.pdf.set_font('helvetica', '', 11)
        self.pdf.set_text_color(*self.text_color)
        
        # Date
        self.pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}", 0, 1, 'C')
        
        # Status with color indicator
        self.pdf.set_font('helvetica', 'B', 11)
        status_text = f"Status: {self.project.status}"
        self.pdf.cell(0, 8, self._clean_text(status_text), 0, 1, 'C')
        
        # Budget if available
        if hasattr(self.project, 'budget') and self.project.budget:
            self.pdf.set_font('helvetica', '', 11)
            self.pdf.cell(0, 8, f"Budget: Rs. {self.project.budget:,.2f}", 0, 1, 'C')
        
        # Footer
        self.pdf.set_y(270)
        self.pdf.set_font('helvetica', 'I', 9)
        self.pdf.set_text_color(*self.text_secondary)
        self.pdf.cell(0, 5, "Generated by Source Point Platform", 0, 1, 'C')
        self.pdf.set_font('helvetica', '', 8)
        self.pdf.cell(0, 5, "Confidential - For Internal Use Only", 0, 1, 'C')

    def _add_table_of_contents(self):
        """Adds a table of contents page."""
        self.pdf.set_font('helvetica', 'B', 20)
        self.pdf.set_text_color(*self.primary_color)
        self.pdf.cell(0, 15, "Table of Contents", 0, 1, 'L')
        
        self.pdf.ln(5)
        
        sections = [
            "1. Executive Summary",
            "2. Project Objectives",
            "3. Project Scope",
            "4. Business Requirements",
            "5. Key Stakeholders",
            "6. Project Constraints",
            "7. Cost-Benefit Analysis"
        ]
        
        self.pdf.set_font('helvetica', '', 12)
        self.pdf.set_text_color(*self.text_color)
        
        for section in sections:
            self.pdf.cell(10, 8, "", 0, 0)  # Indent
            self.pdf.cell(0, 8, section, 0, 1, 'L')
            self.pdf.ln(2)

    def _add_brd_content(self):
        """Adds the content sections with enhanced formatting."""
        brd_sections = {
            "1. Executive Summary": self.project.brd.executive_summary,
            "2. Project Objectives": self.project.brd.project_objectives,
            "3. Project Scope": self.project.brd.project_scope,
            "4. Business Requirements": self.project.brd.business_requirements,
            "5. Key Stakeholders": self.project.brd.key_stakeholders,
            "6. Project Constraints": self.project.brd.project_constraints,
            "7. Cost-Benefit Analysis": self.project.brd.cost_benefit_analysis
        }

        for idx, (title, content) in enumerate(brd_sections.items()):
            # Add page break before each major section (except first)
            if idx > 0 and idx % 2 == 0:
                self.pdf.add_page()
            
            # Section Header with enhanced styling
            self.pdf.set_font('helvetica', 'B', 16)
            self.pdf.set_text_color(*self.primary_color)
            self.pdf.set_fill_color(*self.header_bg)
            self.pdf.set_draw_color(*self.border_color)
            
            # Header box with border
            self.pdf.cell(0, 12, self._clean_text(title), 1, 1, 'L', 1)
            self.pdf.ln(4)
            
            if content:
                self.pdf.set_font('helvetica', '', 11)
                self.pdf.set_text_color(*self.text_color)
                
                html_data = self._sanitize_html(content)
                
                try:
                    self.pdf.write_html(html_data)
                except Exception as e:
                    # Enhanced fallback with better formatting
                    print(f"HTML rendering error for {title}: {e}")
                    clean_text = BeautifulSoup(content, "html.parser").get_text()
                    clean_text = self._clean_text(clean_text)
                    self.pdf.set_font('helvetica', '', 11)
                    self.pdf.multi_cell(0, 6, clean_text, 0, 'L')
                
                self.pdf.ln(8)
            else:
                # Enhanced "not provided" message
                self.pdf.set_fill_color(*self.section_bg)
                self.pdf.set_font('helvetica', 'I', 11)
                self.pdf.set_text_color(*self.text_secondary)
                self.pdf.cell(0, 10, "Not provided", 0, 1, 'L', 1)
                self.pdf.ln(8)
            
            # Add divider between sections
            if idx < len(brd_sections) - 1:
                self._add_section_divider()