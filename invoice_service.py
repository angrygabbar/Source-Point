# Source Point/invoice_service.py

from fpdf import FPDF
from bs4 import BeautifulSoup
from datetime import datetime
import re


class PDF(FPDF):
    """
    Base PDF class with a compact branded header and footer on every page.
    Colours are passed in from InvoiceGenerator so the PDF class can render
    them without depending on the generator instance.
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

        # Compact brand header bar for continuation pages.
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

        # Brand accent stripe on footer
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
        self.cell(0, 4, 'admin@sourcepoint.in', 0, 1, 'C')

        # Page number + copyright
        self.set_font('helvetica', 'I', 7)
        self.set_text_color(*self.c_text_light)
        self.set_xy(10, 284)
        self.cell(0, 4,
                  f'(c) {datetime.utcnow().year} Source Point. All rights reserved.   |   Page {self.page_no()}',
                  0, 0, 'C')



class InvoiceGenerator:
    """
    Premium e-commerce invoice PDF generator.
    Aesthetic: professional ink, teal, amber, and light neutral surfaces.
    """

    def __init__(self, invoice):
        self.invoice = invoice

        # ── Brand Colour Palette ────────────────────────────────────────────
        self.c_brand_dark    = (30,  41,  59)    # Ink header
        self.c_brand_mid     = (13,  148, 136)   # Teal primary
        self.c_brand_violet  = (245, 158, 11)    # Amber accent block
        self.c_brand_pale    = (204, 251, 241)   # Teal-100
        self.c_brand_xpale   = (240, 253, 250)   # Teal-50
        self.c_brand_border  = (153, 246, 228)   # Teal-200
        self.c_brand_accent  = (15,  118, 110)   # Teal-700
        self.c_brand_gold    = (217, 119, 6)     # Amber-600

        self.c_bg_page       = (246, 247, 251)   # Neutral page bg
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
        Branded header bar:
          LEFT  - Source Point identity
          RIGHT - invoice title, number, and total due
        """
        hh = 42  # header height mm

        # Main ink background
        self._set_fill(self.c_brand_dark)
        self.pdf.rect(0, 0, 210, hh, 'F')

        # Warm accent block creates a premium editorial invoice header.
        self._set_fill(self.c_brand_violet)
        self.pdf.rect(146, 0, 64, hh, 'F')

        # Teal stripe at bottom of header
        self._set_fill(self.c_brand_mid)
        self.pdf.rect(0, hh, 210, 2, 'F')

        # Logo badge
        bx, by, bw, bh = 10, 8, 18, 18

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

        # Invoice label
        self.pdf.set_font('helvetica', 'B', 24)
        self._set_text((255, 255, 255))
        self.pdf.set_xy(106, 5)
        self.pdf.cell(94, 12, 'INVOICE', 0, 0, 'R')

        # Invoice number pill
        inv_label = f'# {self._clean_text(self.invoice.invoice_number)}'
        self.pdf.set_font('helvetica', 'B', 9)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(111, 18)
        self.pdf.cell(89, 7, inv_label, 0, 0, 'R')

        # Total due highlight
        self.pdf.set_font('helvetica', '', 7.2)
        self._set_text(self.c_brand_pale)
        self.pdf.set_xy(111, 26)
        self.pdf.cell(89, 4, 'TOTAL DUE', 0, 0, 'R')
        self.pdf.set_font('helvetica', 'B', 12)
        self._set_text((255, 255, 255))
        self.pdf.set_xy(111, 31)
        self.pdf.cell(89, 6, f'Rs.{float(self.invoice.total_amount):,.2f}', 0, 0, 'R')

        self.pdf.set_y(hh + 6)

    def _draw_meta_strip(self):
        """
        5-column meta info bar: Invoice Date | Due Date | Status | Order Ref | Terms
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
        col_w = sw / 5
        for i in range(1, 5):
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
        order_ref = self.invoice.order_id or 'N/A'

        meta_col(0, 'Invoice Date', inv_date)
        meta_col(1, 'Due Date',     due_date)
        meta_col(2, 'Status',       status, self.c_brand_mid)
        meta_col(3, 'Order Ref',    order_ref)
        meta_col(4, 'Payment Terms','Due on Receipt')

        self.pdf.set_y(sy + sh + 6)

    def _draw_address_grid(self):
        """
        Two-column card: Bill To | Ship To
        """
        sx     = 10
        sy     = self.pdf.get_y()
        col_w  = 91
        gap    = 8
        sh     = 38

        for col, (heading, name, detail) in enumerate([
            ('Bill To',
             self._clean_text(self.invoice.recipient_name),
             self._clean_text(
                 f"{self.invoice.recipient_email}\n{self.invoice.bill_to_address or ''}".strip()
             )),
            ('Ship To',
             self._clean_text(self.invoice.recipient_name),
             self._clean_text(self.invoice.ship_to_address or self.invoice.bill_to_address or 'Same as billing address')),
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

            # Contact/address details (multi-cell)
            self.pdf.set_font('helvetica', '', 7.5)
            self._set_text(self.c_text_muted)
            self.pdf.set_xy(cx + 3, sy + 14)
            if detail:
                self.pdf.multi_cell(col_w - 6, 4, detail, 0, 'L')
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

            # Secondary line below description
            self.pdf.set_font('helvetica', '', 6.5)
            self._set_text(self.c_brand_accent)
            self.pdf.set_xy(sx + c_no + 2, sy + (row_h - 5))
            self.pdf.cell(c_desc - 4, 4, 'Line item', 0, 0, 'L')

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
            ('Tax',        f'Rs.{float(self.invoice.tax):,.2f}',           False),
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
        Supplemental invoice details: order reference, payment details,
        shipping address, return policy, and notes.
        """
        sx      = 10
        pw      = 190
        label_x = sx + 6
        value_x = sx + 54
        value_w = pw - 60
        row_pad = 3.5
        divider = 1.2

        policy_text = (
            'Items are eligible for return within 7 days of delivery if unused and in original '
            'packaging. Refunds are processed within 5-7 business days of return receipt. '
            'Digital goods and gift cards are non-refundable.'
        )

        rows = [
            ('Order / Reference',
             self._clean_text(self.invoice.order_id or self.invoice.invoice_number or 'N/A'),
             'B', 8.0, self.c_brand_mid),
            ('Payment Details',
             self._clean_text(self.invoice.payment_details or 'Payment due on receipt unless otherwise agreed.'),
             '', 7.5, self.c_text_mid),
            ('Shipping Address',
             self._clean_text(self.invoice.ship_to_address or self.invoice.bill_to_address or 'Same as billing address.'),
             '', 7.5, self.c_text_mid),
            ('Return Policy',
             self._clean_text(policy_text),
             '', 7.0, self.c_text_muted),
        ]

        def wrap_lines(text, font_style, font_size, avail_w, line_h):
            self.pdf.set_font('helvetica', font_style, font_size)
            n, line_w = 1, 0.0
            for word in text.split(' '):
                ww = self.pdf.get_string_width(word + ' ')
                if line_w + ww > avail_w and line_w > 0:
                    n += 1
                    line_w = ww
                else:
                    line_w += ww
            return n * line_h

        row_specs = []
        for label, value, style, size, color in rows:
            line_h = 4.4 if size >= 7.5 else 3.8
            text_h = max(5.0, wrap_lines(value, style, size, value_w, line_h))
            row_specs.append((label, value, style, size, color, line_h, row_pad + text_h + row_pad))

        ph = sum(spec[-1] for spec in row_specs) + divider * (len(row_specs) - 1)

        # Optional notes height
        notes_h = 0
        if self.invoice.notes:
            notes_h = max(8, wrap_lines(self._clean_text(self.invoice.notes), '', 7.5, pw - 12, 4)) + 10

        # Footer starts at y=269, reserve 3 mm margin
        FOOTER_Y = 269
        sy = self.pdf.get_y()
        if sy + ph + 4 > FOOTER_Y - 3:
            self.pdf.add_page()
            sy = self.pdf.get_y()

        self.pdf.set_auto_page_break(False)

        self._set_fill(self.c_brand_xpale)
        self._set_draw(self.c_brand_border)
        self._thin_line()
        self.pdf.rect(sx, sy, pw, ph, 'FD')
        self._set_fill(self.c_brand_mid)
        self.pdf.rect(sx, sy, 3, ph, 'F')

        ry = sy
        for idx, (label, value, style, size, color, line_h, row_h) in enumerate(row_specs):
            text_y = ry + row_pad
            self.pdf.set_font('helvetica', 'B', 7.6)
            self._set_text(self.c_brand_dark)
            self.pdf.set_xy(label_x, text_y)
            self.pdf.cell(44, 5, label, 0, 0, 'L')

            self.pdf.set_font('helvetica', style, size)
            self._set_text(color)
            self.pdf.set_xy(value_x, text_y)
            self.pdf.multi_cell(value_w, line_h, value, 0, 'L')

            ry += row_h
            if idx < len(row_specs) - 1:
                self._set_draw(self.c_brand_border)
                self.pdf.line(label_x, ry, sx + pw - 4, ry)
                ry += divider

        final_y = sy + ph + 4

        # Optional notes (below the panel, or on the next page if needed)
        if self.invoice.notes:
            note_y = sy + ph + 4
            note_box_h = notes_h - 2
            if note_y + note_box_h > FOOTER_Y - 3:
                self.pdf.add_page()
                note_y = self.pdf.get_y() + 2
            self._set_fill((255, 251, 235))
            self._set_draw((253, 230, 138))
            self.pdf.rect(sx, note_y, pw, note_box_h, 'FD')
            self.pdf.set_font('helvetica', 'B', 7.5)
            self._set_text(self.c_brand_gold)
            self.pdf.set_xy(sx + 5, note_y + 3)
            self.pdf.cell(pw - 10, 4, 'Notes / Terms', 0, 1, 'L')
            self.pdf.set_font('helvetica', '', 7.5)
            self._set_text(self.c_text_mid)
            self.pdf.set_xy(sx + 5, note_y + 8)
            self.pdf.multi_cell(pw - 10, 4, self._clean_text(self.invoice.notes), 0, 'L')
            final_y = note_y + note_box_h + 4

        self.pdf.set_auto_page_break(auto=True, margin=28)
        self.pdf.set_y(final_y)


class SupersCoinInvoiceGenerator:
    """PDF generator for SupersCoins invoices using Super Coins as currency."""

    def __init__(self, invoice):
        self.invoice = invoice
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=18)

    def _clean_text(self, text):
        if text is None:
            return ""
        text = str(text)
        replacements = {
            '\u200b': '', '\xa0': ' ',
            '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-',
            '\u2022': '-',
        }
        for char, rep in replacements.items():
            text = text.replace(char, rep)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def generate_pdf(self):
        invoice = self.invoice
        seller = invoice.seller
        admin = invoice.admin

        self.pdf.add_page()
        self.pdf.set_fill_color(15, 23, 42)
        self.pdf.rect(0, 0, 210, 44, 'F')
        self.pdf.set_fill_color(245, 158, 11)
        self.pdf.rect(152, 0, 58, 44, 'F')
        self.pdf.set_fill_color(20, 184, 166)
        self.pdf.rect(0, 44, 210, 2, 'F')

        self.pdf.set_font('helvetica', 'B', 18)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_xy(12, 10)
        self.pdf.cell(110, 8, 'Source Point', 0, 1, 'L')
        self.pdf.set_font('helvetica', '', 8)
        self.pdf.set_text_color(204, 251, 241)
        self.pdf.set_x(12)
        self.pdf.cell(110, 5, 'SupersCoins Wallet Ledger', 0, 1, 'L')

        self.pdf.set_font('helvetica', 'B', 20)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_xy(100, 9)
        self.pdf.cell(98, 10, 'COIN INVOICE', 0, 1, 'R')
        self.pdf.set_font('helvetica', 'B', 9)
        self.pdf.set_text_color(255, 248, 220)
        self.pdf.set_x(100)
        self.pdf.cell(98, 6, self._clean_text(invoice.invoice_number), 0, 1, 'R')
        self.pdf.set_font('helvetica', 'B', 12)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_x(100)
        self.pdf.cell(98, 7, f"SC {float(invoice.amount):,.2f}", 0, 1, 'R')

        self.pdf.set_y(56)
        self.pdf.set_text_color(17, 24, 39)
        self.pdf.set_font('helvetica', 'B', 11)
        self.pdf.cell(0, 7, 'Invoice Details', 0, 1, 'L')

        self.pdf.set_fill_color(249, 250, 251)
        self.pdf.set_draw_color(229, 231, 235)
        self.pdf.rect(10, 66, 190, 32, 'FD')

        meta = [
            ('Seller', seller.username if seller else 'Seller'),
            ('Email', seller.email if seller else ''),
            ('Status', invoice.status),
            ('Issued By', admin.username if admin else 'Admin'),
            ('Invoice Date', invoice.created_at.strftime('%d %b %Y') if invoice.created_at else 'N/A'),
            ('Due Date', invoice.due_date.strftime('%d %b %Y') if invoice.due_date else 'On Receipt'),
        ]
        x_positions = [14, 75, 138]
        y_positions = [71, 84]
        idx = 0
        for row_y in y_positions:
            for col_x in x_positions:
                label, value = meta[idx]
                self.pdf.set_xy(col_x, row_y)
                self.pdf.set_font('helvetica', 'B', 6.5)
                self.pdf.set_text_color(20, 184, 166)
                self.pdf.cell(56, 4, label.upper(), 0, 1, 'L')
                self.pdf.set_x(col_x)
                self.pdf.set_font('helvetica', 'B', 8.5)
                self.pdf.set_text_color(31, 41, 55)
                self.pdf.cell(56, 5, self._clean_text(value), 0, 0, 'L')
                idx += 1

        self.pdf.set_y(110)
        self.pdf.set_fill_color(15, 23, 42)
        self.pdf.set_text_color(204, 251, 241)
        self.pdf.set_font('helvetica', 'B', 8)
        self.pdf.cell(120, 10, 'Description', 0, 0, 'L', True)
        self.pdf.cell(35, 10, 'Currency', 0, 0, 'C', True)
        self.pdf.cell(35, 10, 'Amount', 0, 1, 'R', True)

        self.pdf.set_fill_color(255, 255, 255)
        self.pdf.set_draw_color(229, 231, 235)
        self.pdf.set_text_color(17, 24, 39)
        self.pdf.set_font('helvetica', '', 9)
        self.pdf.cell(120, 14, self._clean_text(invoice.description), 1, 0, 'L', True)
        self.pdf.set_font('helvetica', 'B', 9)
        self.pdf.cell(35, 14, 'Super Coins', 1, 0, 'C', True)
        self.pdf.cell(35, 14, f"SC {float(invoice.amount):,.2f}", 1, 1, 'R', True)

        self.pdf.set_x(130)
        self.pdf.set_fill_color(240, 253, 250)
        self.pdf.set_text_color(15, 118, 110)
        self.pdf.set_font('helvetica', 'B', 11)
        self.pdf.cell(35, 14, 'Total Due', 1, 0, 'R', True)
        self.pdf.cell(35, 14, f"SC {float(invoice.amount):,.2f}", 1, 1, 'R', True)

        if invoice.notes:
            self.pdf.set_y(155)
            self.pdf.set_font('helvetica', 'B', 9)
            self.pdf.set_text_color(17, 24, 39)
            self.pdf.cell(0, 6, 'Notes', 0, 1, 'L')
            self.pdf.set_font('helvetica', '', 8.5)
            self.pdf.set_text_color(75, 85, 99)
            self.pdf.multi_cell(0, 5, self._clean_text(invoice.notes), 0, 'L')

        self.pdf.set_y(265)
        self.pdf.set_fill_color(15, 23, 42)
        self.pdf.rect(0, 267, 210, 30, 'F')
        self.pdf.set_text_color(203, 213, 225)
        self.pdf.set_font('helvetica', '', 8)
        self.pdf.set_xy(10, 273)
        self.pdf.cell(190, 5, 'This SupersCoins invoice is separate from order invoices and uses Super Coins as currency.', 0, 1, 'C')
        self.pdf.set_text_color(148, 163, 184)
        self.pdf.cell(190, 5, 'Source Point SupersCoins Ledger', 0, 1, 'C')

        return bytes(self.pdf.output())


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
