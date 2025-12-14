from flask_login import UserMixin
from datetime import datetime
import uuid
from extensions import db

candidate_contacts = db.Table('candidate_contacts',
    db.Column('candidate_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('developer_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class LearningContent(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProblemStatement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    users = db.relationship('User', foreign_keys='User.problem_statement_id', backref='assigned_problem', lazy=True)
    assignment_history = db.relationship('ModeratorAssignmentHistory', backref='problem', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='candidate')
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    avatar_url = db.Column(db.String(200), nullable=False, default='https://api.dicebear.com/8.x/initials/svg?seed=User')
    
    problem_statement_id = db.Column(db.Integer, db.ForeignKey('problem_statement.id'), nullable=True)
    test_start_time = db.Column(db.DateTime, nullable=True)
    test_end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    test_completed = db.Column(db.Boolean, default=False, nullable=False) 

    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    mobile_number = db.Column(db.String(20), nullable=True)
    primary_skill = db.Column(db.String(100), nullable=True)
    primary_skill_experience = db.Column(db.String(50), nullable=True)
    secondary_skill = db.Column(db.String(100), nullable=True)
    secondary_skill_experience = db.Column(db.String(50), nullable=True)
    resume_filename = db.Column(db.String(200), nullable=True)

    secret_question = db.Column(db.String(255), nullable=True)
    secret_answer_hash = db.Column(db.String(128), nullable=True)
    meeting_link = db.Column(db.String(255), nullable=True)

    allowed_contacts = db.relationship('User', secondary=candidate_contacts,
                                       primaryjoin=(candidate_contacts.c.candidate_id == id),
                                       secondaryjoin=(candidate_contacts.c.developer_id == id),
                                       backref=db.backref('contact_for', lazy='dynamic'), lazy='dynamic')

    created_problems = db.relationship('ProblemStatement', foreign_keys=[ProblemStatement.created_by_id], backref='creator', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)
    activity_updates = db.relationship('ActivityUpdate', backref='author', lazy=True)
    sent_snippets = db.relationship('CodeSnippet', foreign_keys='CodeSnippet.sender_id', backref='snippet_sender', lazy=True)
    received_snippets = db.relationship('CodeSnippet', foreign_keys='CodeSnippet.recipient_id', backref='snippet_recipient', lazy=True)
    applications = db.relationship('JobApplication', backref='candidate', lazy=True, cascade="all, delete-orphan")
    test_submissions = db.relationship('CodeTestSubmission', foreign_keys='CodeTestSubmission.candidate_id', backref='candidate_submitter', lazy='dynamic')
    received_tests = db.relationship('CodeTestSubmission', foreign_keys='CodeTestSubmission.recipient_id', backref='test_recipient', lazy=True)
    feedback_given = db.relationship('Feedback', foreign_keys='Feedback.moderator_id', backref='moderator', lazy=True)
    feedback_received = db.relationship('Feedback', foreign_keys='Feedback.candidate_id', backref='candidate', lazy=True)
    invoices = db.relationship('Invoice', backref='admin', lazy=True)
    moderator_assignments = db.relationship('ModeratorAssignmentHistory', foreign_keys='ModeratorAssignmentHistory.moderator_id', backref='moderator', lazy=True)
    candidate_assignments = db.relationship('ModeratorAssignmentHistory', foreign_keys='ModeratorAssignmentHistory.candidate_id', backref='candidate', lazy=True)
    orders = db.relationship('Order', backref='buyer', lazy=True)
    
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class ActivityUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CodeSnippet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False, default='java')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class JobOpening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    applications = db.relationship('JobApplication', backref='job', lazy=True, cascade="all, delete-orphan")

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_opening.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    applied_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class CodeTestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(50), nullable=False, default='java')
    submitted_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class AffiliateAd(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_name = db.Column(db.String(100), nullable=False, unique=True)
    affiliate_link = db.Column(db.Text, nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code_correctness = db.Column(db.Integer, nullable=False)
    code_efficiency = db.Column(db.Integer, nullable=False)
    code_readability = db.Column(db.Integer, nullable=False)
    problem_solving = db.Column(db.Integer, nullable=False)
    time_management = db.Column(db.Integer, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False) 

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
    category = db.Column(db.String(50), nullable=True)
    brand = db.Column(db.String(100), nullable=True)
    mrp = db.Column(db.Float, nullable=True) 
    warranty = db.Column(db.String(200), nullable=True)
    return_policy = db.Column(db.String(200), nullable=True)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    bill_to_address = db.Column(db.Text, nullable=True)
    ship_to_address = db.Column(db.Text, nullable=True)
    order_id = db.Column(db.String(50), nullable=True)
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Unpaid', nullable=False) 
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    payment_details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)

class ModeratorAssignmentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_statement_id = db.Column(db.Integer, db.ForeignKey('problem_statement.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

class BRD(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, unique=True)
    executive_summary = db.Column(db.Text, nullable=True)
    project_objectives = db.Column(db.Text, nullable=True)
    project_scope = db.Column(db.Text, nullable=True)
    business_requirements = db.Column(db.Text, nullable=True)
    key_stakeholders = db.Column(db.Text, nullable=True)
    project_constraints = db.Column(db.Text, nullable=True)
    cost_benefit_analysis = db.Column(db.Text, nullable=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    budget = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(50), nullable=False, default='Planning')
    transactions = db.relationship('Transaction', backref='project', lazy=True, cascade="all, delete-orphan")
    brd = db.relationship('BRD', backref='project', uselist=False, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Order Placed') 
    shipping_address = db.Column(db.Text, nullable=False)
    billing_address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class EMIPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    total_principal = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    borrower = db.relationship('User', foreign_keys=[borrower_id], backref='borrowing_plans')
    lender = db.relationship('User', foreign_keys=[lender_id], backref='lending_plans')
    payments = db.relationship('EMIPayment', backref='plan', lazy=True, cascade="all, delete-orphan")

class EMIPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('emi_plan.id'), nullable=False)
    installment_number = db.Column(db.Integer, nullable=False, default=1)  # Added this field
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    reminder_days_before = db.Column(db.Integer, default=3)
    reminder_sent = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)