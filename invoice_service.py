# DecConnectHub/invoice_service.py

from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # This method is empty to allow for a custom header in the main function
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, 'Page ' + str(self.page_no()), 0, 0, 'C')

class InvoiceGenerator:
    def __init__(self, invoice):
        self.invoice = invoice
        self.pdf = PDF()
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)
        # Define colors
        self.primary_color = (79, 70, 229) # Indigo
        self.secondary_color = (107, 114, 128) # Gray
        self.border_color = (229, 231, 235) # Light Gray

    def generate_pdf(self):
        self._add_header()
        self._add_recipient_details()
        self._add_invoice_items()
        self._add_summary()
        self._add_footer_notes()
        return self.pdf.output(dest='S').encode('latin-1')

    def _add_header(self):
        # Company Name
        self.pdf.set_font('Arial', 'B', 20)
        self.pdf.set_text_color(*self.primary_color)
        self.pdf.cell(95, 10, "Source Point", 0, 0, 'L')
        
        # Invoice Title
        self.pdf.set_font('Arial', 'B', 28)
        self.pdf.set_text_color(50, 50, 50)
        self.pdf.cell(95, 10, "INVOICE", 0, 1, 'R')
        
        # Company Address
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(*self.secondary_color)
        self.pdf.cell(95, 5, "123 Tech Park, Innovation Drive", 0, 0, 'L')
        
        # Invoice Details
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_text_color(50, 50, 50)
        self.pdf.cell(95, 5, f"Invoice #: {self.invoice.invoice_number}", 0, 1, 'R')

        # Company City/State
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(*self.secondary_color)
        self.pdf.cell(95, 5, "Pune, Maharashtra, 411001", 0, 0, 'L')

        # Date
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(95, 5, f"Date: {self.invoice.created_at.strftime('%B %d, %Y')}", 0, 1, 'R')

        # Company Email
        self.pdf.cell(95, 5, "admin@sourcepoint.in", 0, 0, 'L')

        # Due Date
        self.pdf.cell(95, 5, f"Due Date: {self.invoice.due_date.strftime('%B %d, %Y')}", 0, 1, 'R')
        self.pdf.ln(15)

    def _add_recipient_details(self):
        self.pdf.set_font('Arial', 'B', 11)
        self.pdf.set_text_color(0, 0, 0)
        
        # Headers for columns
        self.pdf.cell(95, 7, "BILL TO", 0, 0, 'L')
        self.pdf.cell(95, 7, "SHIP TO", 0, 1, 'L')
        
        # Line under headers
        self.pdf.set_draw_color(*self.primary_color)
        self.pdf.set_line_width(0.5)
        self.pdf.line(self.pdf.get_x(), self.pdf.get_y(), self.pdf.get_x() + 190, self.pdf.get_y())
        self.pdf.ln(2)

        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(*self.secondary_color)
        
        y_before = self.pdf.get_y()
        
        # Bill To Address
        self.pdf.multi_cell(95, 5, f"{self.invoice.recipient_name}\n{self.invoice.bill_to_address}", 0, 'L')
        y_after_bill = self.pdf.get_y()
        
        # Reset Y and set X for the second column
        self.pdf.set_y(y_before)
        self.pdf.set_x(105)
        
        # Ship To Address
        self.pdf.multi_cell(95, 5, f"{self.invoice.recipient_name}\n{self.invoice.ship_to_address}", 0, 'L')
        y_after_ship = self.pdf.get_y()

        self.pdf.set_y(max(y_after_bill, y_after_ship))
        self.pdf.ln(10)

    def _add_invoice_items(self):
        # Table Header
        self.pdf.set_fill_color(*self.primary_color)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_draw_color(*self.border_color)
        self.pdf.set_font('Arial', 'B', 10)
        
        self.pdf.cell(100, 10, "DESCRIPTION", 1, 0, 'C', 1)
        self.pdf.cell(30, 10, "QUANTITY", 1, 0, 'C', 1)
        self.pdf.cell(30, 10, "UNIT PRICE", 1, 0, 'C', 1)
        self.pdf.cell(30, 10, "TOTAL", 1, 1, 'C', 1)
        
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(50, 50, 50)

        for item in self.invoice.items:
            # This is the crucial part for handling multi-line descriptions
            x_start = self.pdf.get_x()
            y_start = self.pdf.get_y()
            
            # Draw description cell with word wrapping
            self.pdf.multi_cell(100, 8, item.description, 1, 'L')
            
            # Calculate height of the description cell
            row_height = self.pdf.get_y() - y_start
            
            # Reset position to the start of the row and draw other cells
            self.pdf.set_xy(x_start + 100, y_start)
            self.pdf.cell(30, row_height, str(item.quantity), 1, 0, 'C')
            self.pdf.cell(30, row_height, f"INR {item.price:.2f}", 1, 0, 'R')
            self.pdf.cell(30, row_height, f"INR {item.quantity * item.price:.2f}", 1, 1, 'R')

    def _add_summary(self):
        self.pdf.ln(5)
        
        # Subtotal
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(*self.secondary_color)
        self.pdf.cell(130, 8, "Subtotal:", 0, 0, 'R')
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_text_color(50, 50, 50)
        self.pdf.cell(60, 8, f"INR {self.invoice.subtotal:.2f}", 0, 1, 'R')
        
        # Tax
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(*self.secondary_color)
        self.pdf.cell(130, 8, f"Tax ({self.invoice.tax}%):", 0, 0, 'R')
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_text_color(50, 50, 50)
        self.pdf.cell(60, 8, f"INR {(self.invoice.subtotal * self.invoice.tax / 100):.2f}", 0, 1, 'R')
        
        # Total
        self.pdf.set_font('Arial', 'B', 12)
        self.pdf.set_text_color(*self.primary_color)
        self.pdf.cell(130, 10, "Total Amount:", 0, 0, 'R')
        self.pdf.cell(60, 10, f"INR {self.invoice.total_amount:.2f}", 0, 1, 'R')
        self.pdf.ln(10)

    def _add_footer_notes(self):
        # Position at the bottom
        if self.pdf.get_y() > 220:
             self.pdf.add_page()
        self.pdf.set_y(230)
        
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_text_color(50, 50, 50)
        
        # Payment Details
        if self.invoice.payment_details:
            self.pdf.cell(0, 6, "Payment Details", 0, 1, 'L')
            self.pdf.set_font('Arial', '', 9)
            self.pdf.set_text_color(*self.secondary_color)
            self.pdf.multi_cell(0, 5, self.invoice.payment_details, 0, 'L')
            self.pdf.ln(5)

        # Notes
        if self.invoice.notes:
            self.pdf.set_font('Arial', 'B', 10)
            self.pdf.set_text_color(50, 50, 50)
            self.pdf.cell(0, 6, "Notes", 0, 1, 'L')
            self.pdf.set_font('Arial', '', 9)
            self.pdf.set_text_color(*self.secondary_color)
            self.pdf.multi_cell(0, 5, self.invoice.notes, 0, 'L')