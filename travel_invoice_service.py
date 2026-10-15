"""Shared travel invoice metadata and the bus, hotel, and flight PDF layout."""

from fpdf import FPDF

from datetime import datetime


INVOICE_TYPE_LABELS = {
    'ecommerce': 'E-commerce',
    'bus': 'Bus Booking',
    'hotel': 'Hotel Booking',
    'flight': 'Flight Booking',
}

INVOICE_EMAIL_TEMPLATES = {
    'ecommerce': 'mail/ecommerce_invoice_email.html',
    'bus': 'mail/bus_booking_invoice_email.html',
    'hotel': 'mail/hotel_booking_invoice_email.html',
    'flight': 'mail/flight_booking_invoice_email.html',
}

TRAVEL_BOOKING_FIELDS = {
    'bus': [
        {'name': 'operator', 'label': 'Bus Operator', 'type': 'text'},
        {'name': 'origin', 'label': 'From', 'type': 'text'},
        {'name': 'destination', 'label': 'To', 'type': 'text'},
        {'name': 'travel_date', 'label': 'Travel Date', 'type': 'date'},
        {'name': 'passenger_names', 'label': 'Passenger Name(s)', 'type': 'text'},
        {'name': 'seat_details', 'label': 'Seat(s) / Boarding Point', 'type': 'text'},
    ],
    'hotel': [
        {'name': 'hotel_name', 'label': 'Hotel / Property', 'type': 'text'},
        {'name': 'location', 'label': 'Location', 'type': 'text'},
        {'name': 'check_in', 'label': 'Check-in', 'type': 'date'},
        {'name': 'check_out', 'label': 'Check-out', 'type': 'date'},
        {'name': 'guest_names', 'label': 'Guest Name(s)', 'type': 'text'},
        {'name': 'room_details', 'label': 'Room Type / Rooms', 'type': 'text'},
    ],
    'flight': [
        {'name': 'airline', 'label': 'Airline', 'type': 'text'},
        {'name': 'flight_number', 'label': 'Flight Number(s)', 'type': 'text'},
        {'name': 'origin', 'label': 'From', 'type': 'text'},
        {'name': 'destination', 'label': 'To', 'type': 'text'},
        {'name': 'departure_date', 'label': 'Departure Date', 'type': 'date'},
        {'name': 'return_date', 'label': 'Return Date', 'type': 'date'},
        {'name': 'passenger_names', 'label': 'Passenger Name(s)', 'type': 'text'},
        {'name': 'cabin_class', 'label': 'Cabin Class / Seat(s)', 'type': 'text'},
    ],
}


def normalize_invoice_type(invoice_type):
    value = str(invoice_type or 'ecommerce').strip().lower()
    return value if value in INVOICE_TYPE_LABELS else 'ecommerce'


def invoice_type_label(invoice_type):
    return INVOICE_TYPE_LABELS[normalize_invoice_type(invoice_type)]


def invoice_email_template(invoice_type):
    return INVOICE_EMAIL_TEMPLATES[normalize_invoice_type(invoice_type)]


class BookingPDF(FPDF):
    """Small branded header and footer used by the travel invoice layout."""

    def __init__(self, title, accent, pale, footer_message):
        super().__init__()
        self.title = title
        self.accent = accent
        self.pale = pale
        self.footer_message = footer_message
        self.set_auto_page_break(auto=True, margin=28)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 13, 'F')
        self.set_font('helvetica', 'B', 9)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 2)
        self.cell(80, 8, 'Source Point', 0, 0, 'L')
        self.set_font('helvetica', '', 8)
        self.set_text_color(*self.pale)
        self.set_xy(100, 2)
        self.cell(100, 8, self.title, 0, 0, 'R')
        self.set_y(18)

    def footer(self):
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)
        self.rect(0, 269, 210, 28, 'FD')
        self.set_fill_color(*self.accent)
        self.rect(0, 269, 210, 2, 'F')
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(15, 23, 42)
        self.set_xy(10, 273)
        self.cell(0, 5, self.footer_message, 0, 1, 'C')
        self.set_font('helvetica', '', 7)
        self.set_text_color(100, 116, 139)
        self.set_xy(10, 279)
        self.cell(0, 4, 'admin@sourcepoint.in', 0, 1, 'C')
        self.set_font('helvetica', 'I', 7)
        self.set_xy(10, 284)
        self.cell(0, 4, f'© {datetime.utcnow().year} Source Point · Page {self.page_no()}', 0, 0, 'C')


class TravelInvoiceGenerator:
    """Generate a booking-focused PDF instead of the e-commerce invoice."""

    CONFIG = {
        'bus': {
            'title': 'BUS BOOKING INVOICE',
            'accent': (37, 99, 235),
            'pale': (219, 234, 254),
            'footer': 'Thank you for travelling with Source Point!',
        },
        'hotel': {
            'title': 'HOTEL BOOKING INVOICE',
            'accent': (147, 51, 234),
            'pale': (243, 232, 255),
            'footer': 'Thank you for booking your stay with Source Point!',
        },
        'flight': {
            'title': 'FLIGHT BOOKING INVOICE',
            'accent': (8, 145, 178),
            'pale': (207, 250, 254),
            'footer': 'Thank you for flying with Source Point!',
        },
    }

    def __init__(self, invoice):
        self.invoice = invoice
        self.invoice_type = normalize_invoice_type(getattr(invoice, 'invoice_type', 'ecommerce'))
        self.config = self.CONFIG[self.invoice_type]
        self.field_labels = {
            field['name']: field['label']
            for field in TRAVEL_BOOKING_FIELDS[self.invoice_type]
        }
        self.pdf = BookingPDF(
            self.config['title'], self.config['accent'], self.config['pale'], self.config['footer']
        )
        self.pdf.add_page()

    def _clean(self, value):
        text = str(value or '')
        replacements = {
            '\u200b': '', '\xa0': ' ', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-',
            '\u20b9': 'Rs. ', '\u2022': '-', '\u2026': '...',
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def _wrapped_lines(self, text, width, style='', size=8):
        self.pdf.set_font('helvetica', style, size)
        count = 0
        for paragraph in self._clean(text).splitlines() or ['']:
            if not paragraph:
                count += 1
                continue
            line_width = 0
            count += 1
            for word in paragraph.split():
                word_width = self.pdf.get_string_width(word + ' ')
                if line_width + word_width > width and line_width:
                    count += 1
                    line_width = word_width
                else:
                    line_width += word_width
        return max(count, 1)

    def _page_break_if_needed(self, height, limit=260):
        if self.pdf.get_y() + height > limit:
            self.pdf.add_page()
            self.pdf.set_y(19)

    def generate_pdf(self):
        self._draw_header()
        self._draw_meta()
        self._draw_customer()
        self._draw_booking_details()
        self._draw_charges()
        self._draw_totals()
        self._draw_notes()
        return bytes(self.pdf.output())

    def _draw_header(self):
        pdf = self.pdf
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 46, 'F')
        pdf.set_fill_color(*self.config['accent'])
        pdf.rect(0, 44, 210, 2, 'F')

        pdf.set_font('helvetica', 'B', 17)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 8)
        pdf.cell(90, 9, 'Source Point', 0, 1)
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(*self.config['pale'])
        pdf.set_xy(10, 18)
        pdf.cell(90, 5, 'TRAVEL SERVICES', 0, 1)

        pdf.set_font('helvetica', 'B', 14)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(92, 7)
        pdf.cell(108, 8, self.config['title'], 0, 1, 'R')
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(*self.config['pale'])
        pdf.set_xy(100, 17)
        pdf.cell(100, 5, f"INVOICE  {self._clean(self.invoice.invoice_number)}", 0, 1, 'R')
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(100, 27)
        pdf.cell(100, 7, f"Rs. {float(self.invoice.total_amount or 0):,.2f}", 0, 1, 'R')
        pdf.set_y(51)

    def _draw_meta(self):
        pdf = self.pdf
        x, y, width, height = 10, pdf.get_y(), 190, 19
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, width, height, 'FD')
        values = [
            ('INVOICE DATE', self.invoice.created_at.strftime('%d %b %Y') if self.invoice.created_at else 'N/A'),
            ('BOOKING REF', self.invoice.order_id or 'N/A'),
            ('DUE DATE', self.invoice.due_date.strftime('%d %b %Y') if self.invoice.due_date else 'On Receipt'),
            ('STATUS', str(self.invoice.status or 'Unpaid').title()),
        ]
        col_width = width / len(values)
        for index, (label, value) in enumerate(values):
            cell_x = x + index * col_width
            if index:
                pdf.line(cell_x, y, cell_x, y + height)
            pdf.set_font('helvetica', 'B', 6.5)
            pdf.set_text_color(*self.config['accent'])
            pdf.set_xy(cell_x + 3, y + 3)
            pdf.cell(col_width - 6, 4, label, 0, 1)
            pdf.set_font('helvetica', 'B', 8.5)
            pdf.set_text_color(30, 41, 59)
            pdf.set_xy(cell_x + 3, y + 9)
            pdf.cell(col_width - 6, 6, self._clean(value)[:32], 0, 1)
        pdf.set_y(y + height + 6)

    def _draw_customer(self):
        pdf = self.pdf
        x, y, width, height = 10, pdf.get_y(), 190, 32
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, width, height, 'FD')
        pdf.set_fill_color(*self.config['accent'])
        pdf.rect(x, y, width, 2, 'F')
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_text_color(*self.config['accent'])
        pdf.set_xy(x + 5, y + 5)
        pdf.cell(width - 10, 4, 'BILLED TO', 0, 1)
        pdf.set_font('helvetica', 'B', 10)
        pdf.set_text_color(15, 23, 42)
        pdf.set_xy(x + 5, y + 11)
        pdf.cell(width - 10, 5, self._clean(self.invoice.recipient_name)[:95], 0, 1)
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(71, 85, 105)
        pdf.set_xy(x + 5, y + 18)
        pdf.cell(88, 4, self._clean(self.invoice.recipient_email)[:70], 0, 1)
        address = self._clean(self.invoice.bill_to_address or '')
        if address:
            pdf.set_xy(x + 100, y + 17)
            pdf.multi_cell(85, 4, address[:150], 0, 'R')
        pdf.set_y(y + height + 6)

    def _draw_booking_details(self):
        details = getattr(self.invoice, 'booking_details', None) or {}
        if isinstance(details, str):
            import json
            try:
                details = json.loads(details)
            except (TypeError, ValueError):
                details = {'details': details}
        if not isinstance(details, dict):
            return

        details = [
            (self.field_labels.get(key, key.replace('_', ' ').title()), self._clean(value))
            for key, value in details.items()
            if value not in (None, '')
        ]
        if not details:
            return

        pdf = self.pdf
        x, y, width = 10, pdf.get_y(), 190
        cell_width, gap = 89, 6
        row_heights = []
        for index in range(0, len(details), 2):
            row = details[index:index + 2]
            row_heights.append(max(
                9 + self._wrapped_lines(value, cell_width - 8, size=8) * 4
                for _, value in row
            ))
        panel_height = 12 + sum(row_heights) + 6
        self._page_break_if_needed(panel_height + 4)
        y = pdf.get_y()
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, width, panel_height, 'FD')
        pdf.set_font('helvetica', 'B', 7)
        pdf.set_text_color(*self.config['accent'])
        pdf.set_xy(x + 5, y + 4)
        pdf.cell(width - 10, 4, f"{invoice_type_label(self.invoice_type).upper()} DETAILS", 0, 1)

        cursor_y = y + 11
        for row_index, row_height in enumerate(row_heights):
            row = details[row_index * 2:row_index * 2 + 2]
            for col_index, (label, value) in enumerate(row):
                cell_x = x + 5 + col_index * (cell_width + gap)
                pdf.set_font('helvetica', 'B', 6.5)
                pdf.set_text_color(100, 116, 139)
                pdf.set_xy(cell_x, cursor_y)
                pdf.cell(cell_width, 3.5, self._clean(label).upper()[:55], 0, 1)
                pdf.set_font('helvetica', '', 8)
                pdf.set_text_color(30, 41, 59)
                pdf.set_xy(cell_x, cursor_y + 4)
                pdf.multi_cell(cell_width, 4, value[:240], 0, 'L')
            cursor_y += row_height
        pdf.set_y(y + panel_height + 5)

    def _draw_charges(self):
        pdf = self.pdf
        x, width = 10, 190
        columns = [('DESCRIPTION', 98, 'L'), ('QTY', 20, 'C'), ('RATE', 34, 'R'), ('AMOUNT', 38, 'R')]

        def draw_header(y):
            pdf.set_fill_color(15, 23, 42)
            pdf.rect(x, y, width, 9, 'F')
            cursor_x = x
            pdf.set_font('helvetica', 'B', 7)
            pdf.set_text_color(255, 255, 255)
            for label, col_width, align in columns:
                pad = 3 if align == 'L' else 0
                pdf.set_xy(cursor_x + pad, y + 2)
                pdf.cell(col_width - pad, 5, label, 0, 0, align)
                cursor_x += col_width
            return y + 9

        y = draw_header(pdf.get_y() + 2)
        for index, item in enumerate(self.invoice.items):
            description = self._clean(item.description)
            line_count = self._wrapped_lines(description, columns[0][1] - 8, 'B', 8.5)
            row_height = max(12, line_count * 4 + 6)
            if y + row_height > 259:
                pdf.add_page()
                y = draw_header(pdf.get_y())

            pdf.set_fill_color(*(255, 255, 255) if index % 2 == 0 else (248, 250, 252))
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(x, y, width, row_height, 'FD')
            pdf.set_font('helvetica', 'B', 8.5)
            pdf.set_text_color(15, 23, 42)
            pdf.set_xy(x + 4, y + 3)
            pdf.multi_cell(columns[0][1] - 8, 4, description, 0, 'L')

            cursor_x = x + columns[0][1]
            values = [
                (str(item.quantity), columns[1][1], 'C'),
                (f"Rs. {float(item.price):,.2f}", columns[2][1], 'R'),
                (f"Rs. {float(item.price * item.quantity):,.2f}", columns[3][1], 'R'),
            ]
            for value_index, (value, col_width, align) in enumerate(values):
                pdf.set_font('helvetica', 'B' if value_index == 2 else '', 8)
                pdf.set_text_color(*(self.config['accent'] if value_index == 2 else (51, 65, 85)))
                pdf.set_xy(cursor_x, y + max(2, (row_height - 5) / 2))
                pdf.cell(col_width - (3 if align == 'R' else 0), 5, value, 0, 0, align)
                cursor_x += col_width
            y += row_height
        pdf.set_y(y + 5)

    def _draw_totals(self):
        paid = float(self.invoice.amount_paid or 0)
        total = float(self.invoice.total_amount or 0)
        has_paid = paid > 0
        rows = [
            ('Subtotal', float(self.invoice.subtotal or 0)),
            ('Tax', float(self.invoice.tax or 0)),
        ]
        if has_paid:
            rows.append(('Amount Paid', paid))
        rows.append(('Balance Due' if has_paid else 'Total Due', max(0, total - paid) if has_paid else total))
        self._page_break_if_needed((len(rows) + 1) * 9 + 5)

        pdf = self.pdf
        x, y, width = 120, pdf.get_y(), 80
        for index, (label, amount) in enumerate(rows):
            is_total = index == len(rows) - 1
            background = (15, 23, 42) if is_total else ((255, 255, 255) if index % 2 == 0 else (248, 250, 252))
            text_color = (255, 255, 255) if is_total else (71, 85, 105)
            pdf.set_fill_color(*background)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(x, y, width, 9, 'FD')
            pdf.set_font('helvetica', 'B' if is_total else '', 8.5)
            pdf.set_text_color(*text_color)
            pdf.set_xy(x + 4, y + 2)
            pdf.cell(40, 5, label, 0, 0, 'L')
            pdf.set_xy(x + 42, y + 2)
            pdf.cell(width - 46, 5, f"Rs. {amount:,.2f}", 0, 0, 'R')
            y += 9
        pdf.set_y(y + 5)

    def _draw_notes(self):
        notes = []
        if self.invoice.notes:
            notes.append(('NOTES / TERMS', self.invoice.notes))
        if self.invoice.payment_details:
            notes.append(('PAYMENT DETAILS', self.invoice.payment_details))
        if not notes:
            return

        pdf = self.pdf
        for heading, value in notes:
            text = self._clean(value)
            box_height = 12 + self._wrapped_lines(text, 180, size=7.5) * 4
            self._page_break_if_needed(box_height + 4)
            x, y = 10, pdf.get_y()
            pdf.set_fill_color(255, 255, 255)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(x, y, 190, box_height, 'FD')
            pdf.set_font('helvetica', 'B', 7)
            pdf.set_text_color(*self.config['accent'])
            pdf.set_xy(x + 5, y + 3)
            pdf.cell(180, 4, heading, 0, 1)
            pdf.set_font('helvetica', '', 7.5)
            pdf.set_text_color(51, 65, 85)
            pdf.set_xy(x + 5, y + 8)
            pdf.multi_cell(180, 4, text, 0, 'L')
            pdf.set_y(y + box_height + 4)
