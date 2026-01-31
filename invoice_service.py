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
            '\u200b': '',  #  Zero-width space
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