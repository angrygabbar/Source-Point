# Source Point/models/finance.py
from extensions import db
from datetime import datetime
from sqlalchemy import Numeric

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    # Enhancement: Numeric for currency
    budget = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    status = db.Column(db.String(50), nullable=False, default='Planning')
    
    transactions = db.relationship('Transaction', backref='project', lazy=True, cascade="all, delete-orphan")
    brd = db.relationship('BRD', backref='project', uselist=False, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    # Enhancement: Numeric for currency
    amount = db.Column(Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

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

class EMIPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    # Enhancement: Numeric for currency
    total_principal = db.Column(Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships with string references
    borrower = db.relationship('User', foreign_keys=[borrower_id], backref='borrowing_plans')
    lender = db.relationship('User', foreign_keys=[lender_id], backref='lending_plans')
    payments = db.relationship('EMIPayment', backref='plan', lazy=True, cascade="all, delete-orphan")

class EMIPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('emi_plan.id'), nullable=False)
    installment_number = db.Column(db.Integer, nullable=False, default=1)
    due_date = db.Column(db.Date, nullable=False)
    # Enhancement: Numeric for currency
    amount = db.Column(Numeric(10, 2), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    reminder_days_before = db.Column(db.Integer, default=3)
    reminder_sent = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)