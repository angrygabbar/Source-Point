# Source Point/invoice_service.py

from fpdf import FPDF
from bs4 import BeautifulSoup
from datetime import datetime
import re

class PDF(FPDF):
    def __init__(self, title="Document", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Skip header on the cover page (page 1)
        if self.page_no() > 1:
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, self.doc_title, 0, 0, 'R')
            self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

class InvoiceGenerator:
    def __init__(self, invoice):
        self.invoice = invoice
        self.pdf = PDF(title=f"Invoice #{invoice.invoice_number}")
        self.pdf.add_page()
        
        # --- Color Palette ---
        self.c_dark_blue = (20, 40, 100)    # Dark Navy for Headers
        self.c_blue = (30, 60, 160)         # Standard Blue
        self.c_light_blue = (200, 225, 255) # Light Blue background for totals
        self.c_teal = (50, 180, 200)        # Teal for accents
        self.c_gray_text = (80, 80, 80)
        self.c_border = (0, 0, 0)           # Black borders

    def _clean_text(self, text):
        """Sanitizes text to be compatible with Helvetica (Latin-1) font."""
        if text is None:
            return ""
        text = str(text)
        # Replacement map for common incompatible characters
        replacements = {
            '\u200b': '',  # Zero-width space
            '\xa0': ' ',   # Non-breaking space
            '’': "'",      # Smart quotes
            '‘': "'",
            '“': '"',
            '”': '"',
            '–': '-',      # En-dash
            '—': '-',      # Em-dash
            '₹': 'Rs. ',   # Rupee symbol (often problematic in standard fonts)
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
            
        # Encode to Latin-1, replacing unmappable characters to prevent crashes
        return text.encode('latin-1', 'replace').decode('latin-1')

    def generate_pdf(self):
        self._draw_graphics_top_right()
        self._add_company_header()
        self._add_invoice_details_grid()
        self._add_address_grid()
        self._add_items_table()
        self._add_totals_and_notes()
        self._draw_graphics_bottom_left()
        
        return bytes(self.pdf.output())

    def _draw_graphics_top_right(self):
        """Draws the geometric triangles in the top right corner."""
        x_start = 170
        y_start = 0
        
        self.pdf.set_fill_color(*self.c_teal)
        self.pdf.polygon([(x_start + 10, y_start), (x_start + 30, y_start), (x_start + 20, y_start + 10)], 'F')
        
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.polygon([(x_start + 20, y_start + 10), (x_start + 40, y_start + 10), (x_start + 30, y_start + 20)], 'F')
        
        self.pdf.set_fill_color(*self.c_dark_blue)
        self.pdf.polygon([(x_start + 30, y_start), (210, y_start), (210, y_start + 15)], 'F')

    def _draw_graphics_bottom_left(self):
        """Draws the geometric triangles in the bottom left corner."""
        x_start = 0
        y_start = 285 # Near bottom of A4
        
        self.pdf.set_fill_color(*self.c_teal)
        self.pdf.polygon([(x_start, y_start), (x_start + 15, y_start + 12), (x_start, y_start + 12)], 'F')
        
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.polygon([(x_start + 15, y_start + 12), (x_start + 30, y_start + 12), (x_start + 10, y_start)], 'F')

    def _add_company_header(self):
        self.pdf.set_y(15)
        
        self.pdf.set_font('helvetica', 'B', 16)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(100, 8, "Source Point", 0, 0, 'L')
        
        self.pdf.set_font('helvetica', '', 28)
        self.pdf.set_text_color(*self.c_dark_blue)
        self.pdf.cell(0, 8, "INVOICE", 0, 1, 'R')
        
        self.pdf.set_font('helvetica', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.set_y(24)
        self.pdf.cell(100, 4, "123 Tech Park, Innovation Drive", 0, 1, 'L')
        self.pdf.cell(100, 4, "Pune, Maharashtra 411001", 0, 1, 'L')
        self.pdf.cell(100, 4, "India", 0, 1, 'L')
        
        self.pdf.ln(10)

    def _add_invoice_details_grid(self):
        self.pdf.set_draw_color(*self.c_border)
        self.pdf.set_line_width(0.2)
        
        start_y = self.pdf.get_y()
        
        self.pdf.rect(10, start_y, 190, 32)
        self.pdf.line(105, start_y, 105, start_y + 32)
        
        self.pdf.set_xy(12, start_y + 2)
        
        def add_row(label, value):
            x = self.pdf.get_x()
            y = self.pdf.get_y()
            self.pdf.set_font('helvetica', '', 9)
            self.pdf.set_text_color(*self.c_gray_text)
            self.pdf.cell(30, 6, label, 0, 0, 'L')
            
            self.pdf.set_font('helvetica', 'B', 9)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(60, 6, self._clean_text(str(value)), 0, 1, 'L') # Cleaned
            self.pdf.set_x(x)

        add_row("Invoice#", self.invoice.invoice_number)
        add_row("Invoice Date", self.invoice.created_at.strftime('%d %b %Y'))
        add_row("Terms", "Due on Receipt")
        add_row("Due Date", self.invoice.due_date.strftime('%d %b %Y') if self.invoice.due_date else "Immediate")

        self.pdf.set_y(start_y + 32)

    def _add_address_grid(self):
        start_y = self.pdf.get_y()
        
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.set_text_color(0, 0, 0)
        
        self.pdf.rect(10, start_y, 190, 8)
        self.pdf.rect(10, start_y + 8, 190, 30)
        self.pdf.line(105, start_y, 105, start_y + 38)
        
        self.pdf.set_xy(12, start_y + 1)
        self.pdf.cell(93, 6, "Bill To", 0, 0, 'L')
        self.pdf.set_xy(107, start_y + 1)
        self.pdf.cell(93, 6, "Ship To", 0, 1, 'L')
        
        content_y = start_y + 10
        
        self.pdf.set_xy(12, content_y)
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.cell(90, 5, self._clean_text(self.invoice.recipient_name), 0, 1, 'L') # Cleaned
        self.pdf.set_font('helvetica', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.set_x(12)
        self.pdf.multi_cell(90, 4, self._clean_text(self.invoice.bill_to_address or ''), 0, 'L') # Cleaned
        
        self.pdf.set_xy(107, content_y)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font('helvetica', '', 9)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.multi_cell(90, 4, self._clean_text(self.invoice.ship_to_address or ''), 0, 'L') # Cleaned
        
        self.pdf.set_y(start_y + 40)

    def _add_items_table(self):
        self.pdf.set_fill_color(*self.c_dark_blue)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.set_draw_color(*self.c_dark_blue)
        
        self.pdf.cell(10, 10, "#", 1, 0, 'C', 1)
        self.pdf.cell(110, 10, "Item & Description", 1, 0, 'L', 1)
        self.pdf.cell(20, 10, "Qty", 1, 0, 'R', 1)
        self.pdf.cell(25, 10, "Rate", 1, 0, 'R', 1)
        self.pdf.cell(25, 10, "Amount", 1, 1, 'R', 1)
        
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_draw_color(0, 0, 0)
        self.pdf.set_font('helvetica', '', 9)
        
        count = 1
        for item in self.invoice.items:
            y_start = self.pdf.get_y()
            
            self.pdf.set_x(20)
            self.pdf.multi_cell(110, 6, self._clean_text(item.description), 0, 'L') # Cleaned
            
            # Calculate actual height used by multi_cell
            y_end = self.pdf.get_y()
            row_height = max(12, y_end - y_start) 
            
            self.pdf.set_y(y_start)
            self.pdf.set_x(10)
            
            self.pdf.cell(10, row_height, str(count), 1, 0, 'C')
            self.pdf.cell(110, row_height, "", 1, 0, 'L')
            self.pdf.cell(20, row_height, str(item.quantity), 1, 0, 'R')
            self.pdf.cell(25, row_height, f"{item.price:,.2f}", 1, 0, 'R')
            self.pdf.cell(25, row_height, f"{(item.quantity * item.price):,.2f}", 1, 1, 'R')
            count += 1
            
            self.pdf.set_y(y_start + row_height)

    def _add_totals_and_notes(self):
        self.pdf.set_font('helvetica', 'B', 9)
        self.pdf.cell(165, 8, "Sub Total (Base)", 1, 0, 'R')
        self.pdf.cell(25, 8, f"{self.invoice.subtotal:,.2f}", 1, 1, 'R')
        
        self.pdf.ln(5)
        
        y_start = self.pdf.get_y()
        
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(100, 5, "Terms & Conditions", 0, 1, 'L')
        
        self.pdf.set_font('helvetica', '', 8)
        self.pdf.set_text_color(*self.c_gray_text)
        terms = "Full payment is due upon receipt of this invoice.\nLate payments may incur additional charges."
        if self.invoice.notes:
            terms = self.invoice.notes
        self.pdf.multi_cell(100, 4, self._clean_text(terms), 0, 'L') # Cleaned
        
        self.pdf.set_xy(125, y_start)
        
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.set_draw_color(0, 0, 0)
        self.pdf.rect(125, y_start, 75, 24, 'FD')
        
        self.pdf.set_xy(125, y_start + 2)
        self.pdf.set_font('helvetica', 'B', 9)
        self.pdf.set_text_color(0, 0, 0)
        
        # --- FIXED TAX DISPLAY ---
        self.pdf.cell(40, 6, f"Total Tax", 0, 0, 'L')
        self.pdf.cell(30, 6, f"{self.invoice.tax:,.2f}", 0, 1, 'R') # Removed % and added number formatting
        
        self.pdf.set_x(125)
        self.pdf.cell(40, 6, "Total", 0, 0, 'L')
        self.pdf.cell(30, 6, f"INR {self.invoice.total_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.set_x(125)
        self.pdf.cell(40, 6, "Balance Due", 0, 0, 'L')
        self.pdf.cell(30, 6, f"INR {self.invoice.total_amount:,.2f}", 0, 1, 'R')
        
        self.pdf.set_y(self.pdf.get_y() + 25)
        self.pdf.set_font('helvetica', 'I', 10)
        self.pdf.set_text_color(*self.c_gray_text)
        self.pdf.cell(0, 10, "Thanks for shopping with us.", 0, 1, 'C')

class BrdGenerator:
    def __init__(self, project):
        self.project = project
        self.pdf = PDF(title=f"BRD: {project.name}")
        self.pdf.add_page()
        self.pdf.set_font("helvetica", size=12)
        # Professional Colors
        self.primary_color = (67, 56, 202)   # Indigo-700
        self.header_bg = (238, 242, 255)     # Indigo-50
        self.text_color = (55, 65, 81)       # Gray-700

    def generate_pdf(self):
        self._add_cover_page()
        self.pdf.add_page() # Start content on new page
        self._add_brd_content()
        return bytes(self.pdf.output())

    def _sanitize_html(self, html_content):
        """Prepares HTML for FPDF write_html method with better spacing handling."""
        if not html_content:
            return ""
        
        # 1. Pre-processing: Standardize Characters
        replacements = {
            '“': '"', '”': '"', '‘': "'", '’': "'",
            '–': '-', '—': '-', '…': '...', '•': '-', '&nbsp;': ' ',
            '\u200b': '', '\ufeff': '', # Zero-width spaces
        }
        for char, replacement in replacements.items():
            html_content = html_content.replace(char, replacement)

        soup = BeautifulSoup(html_content, "html.parser")
        
        # 2. Table Fixes: Force borders and width
        for table in soup.find_all("table"):
            table['border'] = '1'
            table['width'] = '100%'
            table['cellpadding'] = '5'
            if table.has_attr('style'): del table['style']

        # 3. Paragraph Formatting (Fixing spacing)
        # Instead of blindly unwrapping, we ensure distinct paragraphs
        for p in soup.find_all("p"):
            if p.get_text(strip=True) or p.find('img'):
                # Add explicit break tags to control spacing
                p.insert_after(soup.new_tag("br"))
                p.insert_after(soup.new_tag("br"))
                p.unwrap()
            else:
                p.decompose() # Remove empty paragraphs

        # 4. Final Cleanup
        html_str = str(soup)
        # Reduce excessive newlines created by BR tags to a maximum of 2
        html_str = re.sub(r'(<br\s*/?>){3,}', '<br><br>', html_str)
        
        return html_str

    def _add_cover_page(self):
        """Creates a professional cover page."""
        self.pdf.set_fill_color(*self.primary_color)
        self.pdf.rect(0, 0, 210, 60, 'F') # Top banner
        
        self.pdf.set_y(25)
        self.pdf.set_font('helvetica', 'B', 32)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.cell(0, 10, "Business Requirement", 0, 1, 'C')
        self.pdf.cell(0, 15, "Document", 0, 1, 'C')
        
        self.pdf.set_y(100)
        self.pdf.set_font('helvetica', '', 14)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(0, 10, "PROJECT NAME:", 0, 1, 'C')
        
        self.pdf.set_font('helvetica', 'B', 24)
        self.pdf.set_text_color(*self.primary_color)
        self.pdf.cell(0, 15, self.project.name, 0, 1, 'C')
        
        self.pdf.set_y(150)
        self.pdf.set_font('helvetica', '', 12)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(0, 10, f"Date Generated: {datetime.utcnow().strftime('%B %d, %Y')}", 0, 1, 'C')
        self.pdf.cell(0, 10, f"Status: {self.project.status}", 0, 1, 'C')
        
        self.pdf.set_y(260)
        self.pdf.set_font('helvetica', 'I', 10)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.cell(0, 10, "Generated by Source Point Platform", 0, 1, 'C')

    def _add_brd_content(self):
        """Adds the content sections using write_html."""
        brd_sections = {
            "1. Executive Summary": self.project.brd.executive_summary,
            "2. Project Objectives": self.project.brd.project_objectives,
            "3. Project Scope": self.project.brd.project_scope,
            "4. Business Requirements": self.project.brd.business_requirements,
            "5. Key Stakeholders": self.project.brd.key_stakeholders,
            "6. Project Constraints": self.project.brd.project_constraints,
            "7. Cost-Benefit Analysis": self.project.brd.cost_benefit_analysis
        }

        for title, content in brd_sections.items():
            # Section Header
            self.pdf.set_font('helvetica', 'B', 14)
            self.pdf.set_text_color(*self.primary_color)
            self.pdf.set_fill_color(*self.header_bg)
            self.pdf.cell(0, 10, title, 0, 1, 'L', 1)
            self.pdf.ln(2) 
            
            if content:
                self.pdf.set_font('helvetica', '', 11)
                self.pdf.set_text_color(*self.text_color)
                
                html_data = self._sanitize_html(content)
                
                try:
                    self.pdf.write_html(html_data)
                except Exception as e:
                    # Fallback for safety
                    clean_text = BeautifulSoup(content, "html.parser").get_text()
                    clean_text = clean_text.replace('•', '-').replace('“', '"').replace('”', '"')
                    self.pdf.multi_cell(0, 6, clean_text)
                
                self.pdf.ln(5) 
            else:
                self.pdf.set_font('helvetica', 'I', 11)
                self.pdf.set_text_color(150, 150, 150)
                self.pdf.cell(0, 8, "Not provided", 0, 1)
                self.pdf.ln(5)