# Source Point/invoice_service.py

from fpdf import FPDF

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # We handle the header manually in the generator for specific styling
        pass

    def footer(self):
        # We handle the footer manually to include the geometric graphics
        pass

class InvoiceGenerator:
    def __init__(self, invoice):
        self.invoice = invoice
        self.pdf = PDF()
        self.pdf.add_page()
        
        # --- Color Palette (Extracted from reference image) ---
        self.c_dark_blue = (20, 40, 100)    # Dark Navy for Headers
        self.c_blue = (30, 60, 160)         # Standard Blue
        self.c_light_blue = (200, 225, 255) # Light Blue background for totals
        self.c_teal = (50, 180, 200)        # Teal for accents
        self.c_gray_text = (80, 80, 80)
        self.c_border = (0, 0, 0)           # Black borders

    def generate_pdf(self):
        self._draw_graphics_top_right()
        self._add_company_header()
        self._add_invoice_details_grid()
        self._add_address_grid()
        self._add_items_table()
        self._add_totals_and_notes()
        self._draw_graphics_bottom_left()
        
        # UPDATE: fpdf2 output() returns a bytearray directly
        return bytes(self.pdf.output())

    def _draw_graphics_top_right(self):
        """Draws the geometric triangles in the top right corner."""
        x_start = 170
        y_start = 0
        
        # Teal Triangle
        self.pdf.set_fill_color(*self.c_teal)
        self.pdf.polygon([(x_start + 10, y_start), (x_start + 30, y_start), (x_start + 20, y_start + 10)], 'F')
        
        # Light Blue Triangle
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.polygon([(x_start + 20, y_start + 10), (x_start + 40, y_start + 10), (x_start + 30, y_start + 20)], 'F')
        
        # Dark Blue Triangle
        self.pdf.set_fill_color(*self.c_dark_blue)
        self.pdf.polygon([(x_start + 30, y_start), (210, y_start), (210, y_start + 15)], 'F')

    def _draw_graphics_bottom_left(self):
        """Draws the geometric triangles in the bottom left corner."""
        x_start = 0
        y_start = 285 # Near bottom of A4
        
        # Teal Triangle
        self.pdf.set_fill_color(*self.c_teal)
        self.pdf.polygon([(x_start, y_start), (x_start + 15, y_start + 12), (x_start, y_start + 12)], 'F')
        
        # Light Blue Triangle
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.polygon([(x_start + 15, y_start + 12), (x_start + 30, y_start + 12), (x_start + 10, y_start)], 'F')

    def _add_company_header(self):
        self.pdf.set_y(15)
        
        # Company Name (Left)
        self.pdf.set_font('Arial', 'B', 16)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(100, 8, "Source Point", 0, 0, 'L')
        
        # "INVOICE" Title (Right)
        self.pdf.set_font('Arial', '', 28)
        self.pdf.set_text_color(*self.c_dark_blue)
        self.pdf.cell(0, 8, "INVOICE", 0, 1, 'R')
        
        # Company Address
        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.set_y(24)
        self.pdf.cell(100, 4, "123 Tech Park, Innovation Drive", 0, 1, 'L')
        self.pdf.cell(100, 4, "Pune, Maharashtra 411001", 0, 1, 'L')
        self.pdf.cell(100, 4, "India", 0, 1, 'L')
        
        self.pdf.ln(10)

    def _add_invoice_details_grid(self):
        """Draws the box containing Invoice#, Date, Terms."""
        self.pdf.set_draw_color(*self.c_border)
        self.pdf.set_line_width(0.2)
        
        start_y = self.pdf.get_y()
        
        # Draw Outer Box
        self.pdf.rect(10, start_y, 190, 32)
        # Draw Vertical Split Line (approx middle)
        self.pdf.line(105, start_y, 105, start_y + 32)
        
        # --- Left Column Content ---
        self.pdf.set_xy(12, start_y + 2)
        
        # Helper for label-value pairs
        def add_row(label, value):
            x = self.pdf.get_x()
            y = self.pdf.get_y()
            self.pdf.set_font('Arial', '', 9)
            self.pdf.set_text_color(*self.c_gray_text)
            self.pdf.cell(30, 6, label, 0, 0, 'L')
            
            self.pdf.set_font('Arial', 'B', 9)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(60, 6, str(value), 0, 1, 'L')
            self.pdf.set_x(x) # Reset X

        add_row("Invoice#", self.invoice.invoice_number)
        add_row("Invoice Date", self.invoice.created_at.strftime('%d %b %Y'))
        add_row("Terms", "Due on Receipt")
        add_row("Due Date", self.invoice.due_date.strftime('%d %b %Y') if self.invoice.due_date else "Immediate")

        # Move cursor past the grid
        self.pdf.set_y(start_y + 32)

    def _add_address_grid(self):
        """Draws the Bill To / Ship To section."""
        start_y = self.pdf.get_y()
        
        # Headers Row
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_text_color(0, 0, 0)
        
        # Box for Headers
        self.pdf.rect(10, start_y, 190, 8)
        self.pdf.rect(10, start_y + 8, 190, 30) # Box for content
        self.pdf.line(105, start_y, 105, start_y + 38) # Vertical divider
        
        # Header Text
        self.pdf.set_xy(12, start_y + 1)
        self.pdf.cell(93, 6, "Bill To", 0, 0, 'L')
        self.pdf.set_xy(107, start_y + 1)
        self.pdf.cell(93, 6, "Ship To", 0, 1, 'L')
        
        # Content Text
        content_y = start_y + 10
        
        # Bill To Content
        self.pdf.set_xy(12, content_y)
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(90, 5, self.invoice.recipient_name, 0, 1, 'L')
        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.set_x(12)
        self.pdf.multi_cell(90, 4, self.invoice.bill_to_address, 0, 'L')
        
        # Ship To Content
        self.pdf.set_xy(107, content_y)
        self.pdf.set_text_color(0, 0, 0)
        # Reuse recipient name for ship to if needed, or just address
        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.multi_cell(90, 4, self.invoice.ship_to_address, 0, 'L')
        
        self.pdf.set_y(start_y + 40) # Space after address grid

    def _add_items_table(self):
        # Header Styling
        self.pdf.set_fill_color(*self.c_dark_blue)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font('Arial', '', 10)
        self.pdf.set_draw_color(*self.c_dark_blue) # Border matches fill
        
        # Header Row
        self.pdf.cell(10, 10, "#", 1, 0, 'C', 1)
        self.pdf.cell(110, 10, "Item & Description", 1, 0, 'L', 1)
        self.pdf.cell(20, 10, "Qty", 1, 0, 'R', 1)
        self.pdf.cell(25, 10, "Rate", 1, 0, 'R', 1)
        self.pdf.cell(25, 10, "Amount", 1, 1, 'R', 1)
        
        # Reset for Items
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_draw_color(0, 0, 0) # Black borders
        self.pdf.set_font('Arial', '', 9)
        
        count = 1
        for item in self.invoice.items:
            y_start = self.pdf.get_y()
            
            # Calculate height based on description wrapping
            self.pdf.set_x(20) # Move to description column X
            
            # Print Description Text via MultiCell (handles wrapping)
            self.pdf.multi_cell(110, 6, item.description, 0, 'L')
            row_height = 12 # Fixed height for consistency
            
            # Reset cursor to top of row to draw the other columns
            self.pdf.set_y(y_start)
            self.pdf.set_x(10)
            
            # Draw cells (Empty string for description cell as it's already drawn)
            self.pdf.cell(10, row_height, str(count), 1, 0, 'C')
            self.pdf.cell(110, row_height, "", 1, 0, 'L') # Border for description
            self.pdf.cell(20, row_height, str(item.quantity), 1, 0, 'R')
            self.pdf.cell(25, row_height, f"{item.price:,.2f}", 1, 0, 'R')
            self.pdf.cell(25, row_height, f"{(item.quantity * item.price):,.2f}", 1, 1, 'R')
            count += 1
            
            # Move to next row position
            self.pdf.set_y(y_start + row_height)

    def _add_totals_and_notes(self):
        # Subtotal Line
        self.pdf.set_font('Arial', 'B', 9)
        self.pdf.cell(165, 8, "Sub Total", 1, 0, 'R')
        self.pdf.cell(25, 8, f"{self.invoice.subtotal:,.2f}", 1, 1, 'R')
        
        self.pdf.ln(5)
        
        y_start = self.pdf.get_y()
        
        # --- Left Side: Terms & Conditions ---
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(100, 5, "Terms & Conditions", 0, 1, 'L')
        
        self.pdf.set_font('Arial', '', 8)
        self.pdf.set_text_color(*self.c_gray_text)
        terms = "Full payment is due upon receipt of this invoice.\nLate payments may incur additional charges."
        if self.invoice.notes:
            terms = self.invoice.notes
        self.pdf.multi_cell(100, 4, terms, 0, 'L')
        
        # --- Right Side: Totals Box (Blue Background) ---
        self.pdf.set_xy(125, y_start)
        
        # Box Background
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.set_draw_color(0, 0, 0)
        self.pdf.rect(125, y_start, 75, 24, 'FD')
        
        # Tax
        self.pdf.set_xy(125, y_start + 2)
        self.pdf.set_font('Arial', 'B', 9)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(40, 6, f"Tax Rate", 0, 0, 'L')
        self.pdf.cell(30, 6, f"{self.invoice.tax}%", 0, 1, 'R')
        
        # Total
        self.pdf.set_x(125)
        self.pdf.cell(40, 6, "Total", 0, 0, 'L')
        self.pdf.cell(30, 6, f"INR {self.invoice.total_amount:,.2f}", 0, 1, 'R')
        
        # Balance Due
        self.pdf.set_x(125)
        self.pdf.cell(40, 6, "Balance Due", 0, 0, 'L')
        self.pdf.cell(30, 6, f"INR {self.invoice.total_amount:,.2f}", 0, 1, 'R')
        
        # --- Bottom Footer Message ---
        self.pdf.set_y(self.pdf.get_y() + 25)
        self.pdf.set_font('Arial', 'I', 10)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.cell(0, 10, "Thanks for shopping with us.", 0, 1, 'C')


class BrdGenerator:
    def __init__(self, project):
        self.project = project
        self.pdf = PDF()
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)
        self.primary_color = (79, 70, 229) # Indigo
        self.secondary_color = (107, 114, 128) # Gray

    def generate_pdf(self):
        self._add_header()
        self._add_brd_content()
        return bytes(self.pdf.output())

    def _add_header(self):
        self.pdf.set_fill_color(*self.primary_color)
        self.pdf.rect(0, 0, 210, 40, 'F')
        
        self.pdf.set_y(15)
        self.pdf.set_font('Arial', 'B', 24)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.cell(0, 10, f"BRD: {self.project.name}", 0, 1, 'C')
        
        self.pdf.ln(20)

    def _add_brd_content(self):
        brd_sections = {
            "Executive Summary": self.project.brd.executive_summary,
            "Project Objectives": self.project.brd.project_objectives,
            "Project Scope": self.project.brd.project_scope,
            "Business Requirements": self.project.brd.business_requirements,
            "Key Stakeholders": self.project.brd.key_stakeholders,
            "Project Constraints": self.project.brd.project_constraints,
            "Cost-Benefit Analysis": self.project.brd.cost_benefit_analysis
        }

        for title, content in brd_sections.items():
            self.pdf.set_font('Arial', 'B', 14)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(0, 10, title, 0, 1, 'L')
            
            self.pdf.set_font('Arial', '', 12)
            self.pdf.set_text_color(*self.secondary_color)
            self.pdf.multi_cell(0, 10, content or 'Not provided')
            self.pdf.ln(5)