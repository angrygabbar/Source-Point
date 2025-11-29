from fpdf import FPDF
from bs4 import BeautifulSoup
from datetime import datetime
import re

class PDF(FPDF):
    def __init__(self, title="Document", confidentiality_text="CONFIDENTIAL", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = title
        self.confidentiality_text = confidentiality_text
        self.set_auto_page_break(auto=True, margin=25)
        
        # Corporate Color Palette
        self.c_primary = (30, 58, 138)    # Deep Navy Blue
        self.c_secondary = (71, 85, 105)  # Slate Gray
        self.c_accent = (241, 245, 249)   # Light Gray Background
        self.c_text = (51, 65, 85)        # Dark Gray Text

    def header(self):
        # Skip header on cover page (Page 1)
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 9)
            self.set_text_color(*self.c_secondary)
            
            # Left: Company/Platform
            self.cell(0, 10, "Source Point Platform", 0, 0, 'L')
            
            # Right: Document Title
            self.cell(0, 10, self.doc_title, 0, 0, 'R')
            
            # Divider Line
            self.ln(12)
            self.set_draw_color(200, 200, 200)
            self.line(10, 18, 200, 18)
            self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        
        # Left: Confidentiality
        self.cell(60, 10, self.confidentiality_text, 0, 0, 'L')
        
        # Center: Page Number
        self.cell(70, 10, f'Page {self.page_no()} of {{nb}}', 0, 0, 'C')
        
        # Right: Date
        self.cell(60, 10, datetime.utcnow().strftime('%Y-%m-%d'), 0, 0, 'R')

class InvoiceGenerator:
    def __init__(self, invoice):
        self.invoice = invoice
        self.pdf = PDF(title=f"Invoice #{invoice.invoice_number}")
        self.pdf.alias_nb_pages()
        self.pdf.add_page()
        
        # Invoice Specific Colors
        self.c_dark_blue = (20, 40, 100)
        self.c_light_blue = (230, 240, 255)
        self.c_gray = (100, 100, 100)

    def generate_pdf(self):
        self._draw_header()
        self._add_invoice_info()
        self._add_items_table()
        self._add_totals()
        return bytes(self.pdf.output())

    def _draw_header(self):
        self.pdf.set_font('helvetica', 'B', 20)
        self.pdf.set_text_color(*self.c_dark_blue)
        self.pdf.cell(0, 10, "INVOICE", 0, 1, 'R')
        
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.set_text_color(*self.c_gray)
        self.pdf.cell(0, 5, "Source Point Platform", 0, 1, 'L')
        self.pdf.cell(0, 5, "123 Tech Park, Innovation Drive", 0, 1, 'L')
        self.pdf.cell(0, 5, "Pune, Maharashtra, India", 0, 1, 'L')
        self.pdf.ln(10)

    def _add_invoice_info(self):
        self.pdf.set_draw_color(220, 220, 220)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)
        
        # Two columns: Bill To vs Invoice Details
        y_start = self.pdf.get_y()
        
        # Left Column
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(90, 5, "Bill To:", 0, 1)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.set_text_color(50, 50, 50)
        self.pdf.cell(90, 5, self.invoice.recipient_name, 0, 1)
        self.pdf.multi_cell(90, 5, self.invoice.bill_to_address or "", 0, 'L')
        
        # Right Column (Reset Y, Move X)
        self.pdf.set_xy(110, y_start)
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(40, 5, "Invoice #:", 0, 0)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.cell(50, 5, self.invoice.invoice_number, 0, 1, 'R')
        
        self.pdf.set_x(110)
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.cell(40, 5, "Date:", 0, 0)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.cell(50, 5, self.invoice.created_at.strftime('%Y-%m-%d'), 0, 1, 'R')
        
        self.pdf.set_x(110)
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.cell(40, 5, "Due Date:", 0, 0)
        self.pdf.set_font('helvetica', '', 10)
        due_date = self.invoice.due_date.strftime('%Y-%m-%d') if self.invoice.due_date else "Immediate"
        self.pdf.cell(50, 5, due_date, 0, 1, 'R')
        
        self.pdf.ln(15)

    def _add_items_table(self):
        # Header
        self.pdf.set_fill_color(*self.c_dark_blue)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font('helvetica', 'B', 10)
        self.pdf.cell(10, 8, "#", 0, 0, 'C', 1)
        self.pdf.cell(100, 8, "Description", 0, 0, 'L', 1)
        self.pdf.cell(20, 8, "Qty", 0, 0, 'C', 1)
        self.pdf.cell(30, 8, "Price", 0, 0, 'R', 1)
        self.pdf.cell(30, 8, "Total", 0, 1, 'R', 1)
        
        # Rows
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.set_fill_color(245, 247, 250)
        
        fill = False
        count = 1
        for item in self.invoice.items:
            self.pdf.cell(10, 8, str(count), 0, 0, 'C', fill)
            self.pdf.cell(100, 8, item.description, 0, 0, 'L', fill)
            self.pdf.cell(20, 8, str(item.quantity), 0, 0, 'C', fill)
            self.pdf.cell(30, 8, f"{item.price:,.2f}", 0, 0, 'R', fill)
            self.pdf.cell(30, 8, f"{item.quantity * item.price:,.2f}", 0, 1, 'R', fill)
            fill = not fill
            count += 1
        
        self.pdf.ln(5)

    def _add_totals(self):
        # Totals box on the right
        x_start = 110
        self.pdf.set_x(x_start)
        self.pdf.set_font('helvetica', '', 10)
        self.pdf.cell(50, 8, "Subtotal:", 0, 0, 'R')
        self.pdf.cell(30, 8, f"{self.invoice.subtotal:,.2f}", 0, 1, 'R')
        
        self.pdf.set_x(x_start)
        self.pdf.cell(50, 8, f"Tax ({self.invoice.tax}%):", 0, 0, 'R')
        self.pdf.cell(30, 8, f"{(self.invoice.total_amount - self.invoice.subtotal):,.2f}", 0, 1, 'R')
        
        self.pdf.set_x(x_start)
        self.pdf.set_font('helvetica', 'B', 12)
        self.pdf.set_fill_color(*self.c_light_blue)
        self.pdf.cell(50, 10, "Total:", 0, 0, 'R', 1)
        self.pdf.cell(30, 10, f"INR {self.invoice.total_amount:,.2f}", 0, 1, 'R', 1)


class BrdGenerator:
    def __init__(self, project):
        self.project = project
        self.pdf = PDF(title=f"BRD: {project.name}", confidentiality_text="INTERNAL & CONFIDENTIAL")
        self.pdf.alias_nb_pages()
        
        # Professional Styles
        self.font_header = 'helvetica'
        self.font_body = 'helvetica'
        self.c_primary = (30, 58, 138)    # #1e3a8a (Navy)
        self.c_secondary = (51, 65, 85)   # #334155 (Slate)
        self.c_bg_header = (241, 245, 249) # #f1f5f9 (Light Gray)

    def generate_pdf(self):
        self.pdf.add_page()
        self._add_cover_page()
        
        self.pdf.add_page()
        self._add_document_control()
        
        self.pdf.add_page()
        self._add_toc()
        
        self.pdf.add_page()
        self._add_content()
        
        return bytes(self.pdf.output())

    def _add_cover_page(self):
        """Generates a professional cover page."""
        # Top Accent Bar
        self.pdf.set_fill_color(*self.c_primary)
        self.pdf.rect(0, 0, 210, 15, 'F')
        
        self.pdf.set_y(60)
        
        # Document Type Label
        self.pdf.set_font(self.font_header, 'B', 14)
        self.pdf.set_text_color(100, 116, 139) # Light Slate
        self.pdf.cell(0, 10, "BUSINESS REQUIREMENT DOCUMENT", 0, 1, 'C')
        
        # Project Title (Big)
        self.pdf.ln(5)
        self.pdf.set_font(self.font_header, 'B', 32)
        self.pdf.set_text_color(*self.c_primary)
        self.pdf.multi_cell(0, 15, self.project.name.upper(), 0, 'C')
        
        # Divider
        self.pdf.ln(20)
        self.pdf.set_draw_color(200, 200, 200)
        self.pdf.line(50, self.pdf.get_y(), 160, self.pdf.get_y())
        self.pdf.ln(20)
        
        # Project Meta Data Box
        self.pdf.set_fill_color(248, 250, 252) # Very light gray
        self.pdf.rect(55, self.pdf.get_y(), 100, 45, 'F')
        
        self.pdf.set_font(self.font_body, '', 11)
        self.pdf.set_text_color(*self.c_secondary)
        
        self.pdf.ln(5)
        self.pdf.cell(0, 8, f"Project ID: #{self.project.id}", 0, 1, 'C')
        self.pdf.cell(0, 8, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}", 0, 1, 'C')
        self.pdf.cell(0, 8, f"Status: {self.project.status}", 0, 1, 'C')
        self.pdf.cell(0, 8, f"Version: 1.0", 0, 1, 'C')

        # Bottom Graphic
        self.pdf.set_fill_color(*self.c_primary)
        self.pdf.rect(0, 280, 210, 17, 'F')

    def _add_document_control(self):
        """Standard version control table."""
        self._section_header("0.0 Document Control")
        
        self.pdf.set_font(self.font_body, '', 10)
        self.pdf.set_text_color(*self.c_secondary)
        self.pdf.ln(5)
        
        # Table Header
        self.pdf.set_fill_color(*self.c_bg_header)
        self.pdf.set_font(self.font_header, 'B', 10)
        self.pdf.cell(25, 10, "Version", 1, 0, 'C', 1)
        self.pdf.cell(35, 10, "Date", 1, 0, 'C', 1)
        self.pdf.cell(50, 10, "Author", 1, 0, 'L', 1)
        self.pdf.cell(80, 10, "Change Description", 1, 1, 'L', 1)
        
        # Table Row
        self.pdf.set_font(self.font_body, '', 10)
        self.pdf.cell(25, 10, "1.0", 1, 0, 'C')
        self.pdf.cell(35, 10, datetime.utcnow().strftime('%Y-%m-%d'), 1, 0, 'C')
        self.pdf.cell(50, 10, "Source Point Admin", 1, 0, 'L')
        self.pdf.cell(80, 10, "Initial Draft", 1, 1, 'L')
        
        self.pdf.ln(15)
        
        # Approvals
        self.pdf.set_font(self.font_header, 'B', 12)
        self.pdf.cell(0, 10, "Approvals", 0, 1, 'L')
        self.pdf.set_font(self.font_body, '', 10)
        self.pdf.cell(0, 6, "The following stakeholders must review and approve this document:", 0, 1)
        self.pdf.ln(5)
        
        roles = ["Project Manager", "Lead Developer", "Client Representative", "QA Lead"]
        for role in roles:
            self.pdf.cell(70, 10, role, 0, 0)
            self.pdf.cell(70, 10, "__________________________", 0, 0)
            self.pdf.cell(30, 10, "Date: ________", 0, 1)

    def _add_toc(self):
        """Static Table of Contents."""
        self.pdf.set_font(self.font_header, 'B', 16)
        self.pdf.set_text_color(*self.c_primary)
        self.pdf.cell(0, 10, "Table of Contents", 0, 1, 'L')
        self.pdf.ln(10)
        
        sections = [
            "1. Executive Summary",
            "2. Project Objectives",
            "3. Project Scope",
            "4. Business Requirements",
            "5. Key Stakeholders",
            "6. Project Constraints",
            "7. Cost-Benefit Analysis"
        ]
        
        self.pdf.set_font(self.font_body, '', 12)
        self.pdf.set_text_color(*self.c_secondary)
        
        for sec in sections:
            self.pdf.cell(10) # Indent
            self.pdf.cell(0, 10, sec, 0, 1)
            self.pdf.set_draw_color(240, 240, 240)
            self.pdf.line(20, self.pdf.get_y(), 190, self.pdf.get_y())

    def _add_content(self):
        """Renders the BRD dynamic content."""
        brd = self.project.brd
        
        content_map = [
            ("1.0 Executive Summary", brd.executive_summary),
            ("2.0 Project Objectives", brd.project_objectives),
            ("3.0 Project Scope", brd.project_scope),
            ("4.0 Business Requirements", brd.business_requirements),
            ("5.0 Key Stakeholders", brd.key_stakeholders),
            ("6.0 Project Constraints", brd.project_constraints),
            ("7.0 Cost-Benefit Analysis", brd.cost_benefit_analysis),
        ]
        
        for title, html_text in content_map:
            # Check for page break before starting a new section
            if self.pdf.get_y() > 240:
                self.pdf.add_page()
            
            self._section_header(title)
            
            if html_text:
                self._render_html_body(html_text)
            else:
                self.pdf.set_font(self.font_body, 'I', 11)
                self.pdf.set_text_color(150, 150, 150)
                self.pdf.cell(0, 10, "No information provided for this section.", 0, 1)
            
            self.pdf.ln(10) # Extra spacing after section

    def _section_header(self, title):
        """Styled header with background block."""
        self.pdf.set_font(self.font_header, 'B', 14)
        self.pdf.set_text_color(*self.c_primary)
        self.pdf.set_fill_color(*self.c_bg_header)
        # Full width block
        self.pdf.cell(0, 12, f"  {title}", 0, 1, 'L', 1)
        self.pdf.ln(3)

    def _render_html_body(self, html_content):
        """Cleans and renders HTML content using FPDF's built-in HTML parser."""
        self.pdf.set_font(self.font_body, '', 11)
        self.pdf.set_text_color(*self.c_secondary)
        
        # 1. Clean HTML: Allow tables and lists
        clean_html = self._sanitize_html(html_content)
        
        try:
            # Using basic HTML writing which supports simple tables
            self.pdf.write_html(clean_html)
        except Exception as e:
            # Fallback for errors: Strip tags and just print text
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            self.pdf.multi_cell(0, 6, text)

    def _sanitize_html(self, html_content):
        """Prepares HTML for FPDF write_html method, PRESERVING TABLES."""
        if not html_content: return ""
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Whitelist Tags: NOW INCLUDES TABLE TAGS
        allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'li', 'h1', 'h2', 'h3', 
                        'table', 'thead', 'tbody', 'tr', 'th', 'td']

        for tag in soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
        
        # 2. Fix Tables: Force borders and width so they show up
        for table in soup.find_all('table'):
            table.attrs = {} # Clear existing styles
            table['border'] = '1'
            table['width'] = '100%'
            table['cellpadding'] = '5'
            
        for cell in soup.find_all(['td', 'th']):
            cell.attrs = {} # Clear styles on cells
            
        # 3. Fix Lists: Clean attributes
        for ul in soup.find_all('ul'):
            ul.attrs = {} 
        
        # 4. Text Normalization
        text = str(soup)
        # Replace Paragraph tags with double line breaks for cleaner PDF spacing
        text = text.replace('<p>', '').replace('</p>', '<br><br>')
        text = text.replace('&nbsp;', ' ')
        
        return text