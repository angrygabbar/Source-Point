from extensions import db, celery
import sib_api_v3_sdk
import os
import base64
import pybreaker
from datetime import datetime, timedelta
from flask import render_template
import logging
from enums import InvoiceStatus, UserRole

# Configure Logger for Background Tasks
logger = logging.getLogger(__name__)

# --- 1. CIRCUIT BREAKER CONFIGURATION ---
email_breaker = pybreaker.CircuitBreaker(
    fail_max=3, 
    reset_timeout=60,
    listeners=[pybreaker.CircuitBreakerListener()] 
)

# --- 2. EMAIL SENDING LOGIC ---
def _send_via_brevo_api(to_list, subject, html_content, cc_list=None, bcc_list=None, attachments=None):
    """
    Internal helper to send emails using Brevo API with Circuit Breaker protection.
    """
    api_key = os.environ.get('BREVO_API_KEY')
    admin_email   = 'admin@sourcepoint.in'
    archive_email = 'sourcepoint.archieve@gmail.com'
    sender_email = 'notifications@sourcepoint.in'
    sender_name = 'Source Point'

    if not api_key:
        logger.warning("Brevo API key is not set. Email skipped.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = {"name": sender_name, "email": sender_email}

    email_attachments = []
    if attachments:
        for attachment_data in attachments:
            encoded_content = base64.b64encode(attachment_data['data']).decode()
            email_attachments.append({
                "content": encoded_content,
                "name": attachment_data['filename']
            })

    smtp_email_data = {
        "to": to_list,
        "sender": sender,
        "subject": subject,
        "html_content": html_content
    }
    if cc_list: smtp_email_data["cc"] = cc_list
    if bcc_list: smtp_email_data["bcc"] = bcc_list
    if email_attachments: smtp_email_data["attachment"] = email_attachments

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(**smtp_email_data)

    try:
        @email_breaker
        def perform_send():
            return api_instance.send_transac_email(send_smtp_email)
            
        perform_send()
        logger.info(f"[Celery] Email sent successfully to {[t['email'] for t in to_list]}")
        
    except pybreaker.CircuitBreakerError:
        logger.error("[Celery] Circuit Breaker Open: Email service is down. Email dropped.")
    except Exception as e:
        logger.error(f"[Celery] Error sending email: {e}")

# --- 3. TASKS ---

@celery.task
def send_email_task(to_list, subject, html_content, cc_list, bcc_list, attachments):
    _send_via_brevo_api(to_list, subject, html_content, cc_list, bcc_list, attachments)

@celery.task
def send_single_reminder_task(payment_id):
    from utils import send_email
    from models.finance import EMIPayment
    
    payment = EMIPayment.query.get(payment_id)
    if not payment or payment.reminder_sent:
        return

    try:
        today = datetime.utcnow().date()
        days_remaining = (payment.due_date - today).days
        borrower = payment.plan.borrower
        lender = payment.plan.lender
        
        if borrower and borrower.email:
            send_email(
                to=borrower.email,
                subject=f"Upcoming Payment Reminder: {payment.description or 'EMI'}",
                template="mail/emi_reminder_borrower.html",
                user=borrower, lender=lender, payment=payment, days_remaining=days_remaining
            )

        if lender and lender.email:
            send_email(
                to=lender.email,
                subject=f"Incoming Payment Expectation: {payment.description or 'EMI'}",
                template="mail/emi_reminder_lender.html",
                user=lender, borrower=borrower, payment=payment, days_remaining=days_remaining
            )
        
        payment.reminder_sent = True
        db.session.commit()
        logger.info(f"[Celery Worker] EMI Reminder sent for ID {payment.id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Worker Error] Failed EMI reminder {payment.id}: {e}")

@celery.task
def process_emi_reminders_task():
    from models.finance import EMIPayment
    today = datetime.utcnow().date()
    logger.info(f"[Scheduler] Checking EMI payments due tomorrow ({today})...")

    batch = EMIPayment.query.filter(EMIPayment.status == 'Pending', EMIPayment.reminder_sent == False).limit(100).all()
    count = 0
    for payment in batch:
        if payment.plan and (payment.due_date - today).days == 1:
            send_single_reminder_task.delay(payment.id)
            count += 1
    logger.info(f"[Scheduler] Queued {count} EMI reminder tasks.")

@celery.task
def send_invoice_reminders_task():
    from models.commerce import Invoice
    logger.info("[Scheduler] Starting Invoice Reminder Job...")
    
    pending_invoices = Invoice.query.filter(Invoice.status != InvoiceStatus.PAID.value).all()
    if not pending_invoices: return

    count = 0
    for invoice in pending_invoices:
        try:
            if not invoice.recipient_email: continue
            
            invoice_date = invoice.created_at.strftime('%B %d, %Y') if invoice.created_at else "Unknown"
            due_date = invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else "Immediate"

            html_content = render_template('mail/reminder_invoice_email.html',
                recipient_name=invoice.recipient_name, invoice_number=invoice.invoice_number,
                created_at=invoice_date, total_amount=invoice.total_amount, due_date=due_date, invoice=invoice
            )
            
            _send_via_brevo_api(
                to_list=[{"email": invoice.recipient_email, "name": invoice.recipient_name}],
                subject=f"Payment Reminder: Invoice {invoice.invoice_number}",
                html_content=html_content
            )
            count += 1
        except Exception as e:
            logger.error(f"[Scheduler] Invoice {invoice.invoice_number} failed: {e}")
    logger.info(f"[Scheduler] Sent {count} invoice reminders.")

@celery.task
def check_hiring_events_task():
    """
    AUTOMATED SCHEDULER TASK (Every 15 mins):
    1. Reminds candidates 2 hours before test.
    2. Auto-completes tests when time expires.
    """
    from models.auth import User
    
    logger.info("[Scheduler] Checking Hiring Events...")
    now = datetime.utcnow()
    
    # --- PART A: 2-Hour Reminder ---
    upcoming_candidates = User.query.filter(
        User.test_start_time != None,
        User.reminder_sent == False
    ).all()

    remind_count = 0
    for candidate in upcoming_candidates:
        # FIX 1: Robust Date Handling (Handle strings from SQLite)
        start_time = candidate.test_start_time
        if isinstance(start_time, str):
            try:
                # Try parsing standard ISO format
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                continue

        # Check if start time is in the future
        if start_time > now:
            time_diff = start_time - now
            # If start time is within 2 hours (7200 seconds)
            if time_diff.total_seconds() <= 7200:
                try:
                    ist_time = (start_time + timedelta(hours=5, minutes=30)).strftime('%b %d, %Y at %I:%M %p')
                    problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "Code Test"
                    
                    html_content = render_template('mail/test_reminder.html', 
                                                   candidate=candidate, start_time_ist=ist_time, problem_title=problem_title)
                    
                    _send_via_brevo_api(
                        to_list=[{"email": candidate.email, "name": candidate.username}],
                        subject="Reminder: Your Coding Test Starts Soon",
                        html_content=html_content
                    )
                    
                    candidate.reminder_sent = True
                    remind_count += 1
                except Exception as e:
                    logger.error(f"[Scheduler] Failed reminder for {candidate.username}: {e}")

    # --- PART B: Auto-Completion (Expired Tests) ---
    expired_candidates = User.query.filter(
        User.test_end_time != None,
        User.test_completed == False
    ).all()

    complete_count = 0
    # FIX 2: Pre-fetch admin for templates
    admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()

    for candidate in expired_candidates:
        # Handle date string conversion for end_time if needed
        end_time = candidate.test_end_time
        if isinstance(end_time, str):
             try:
                end_time = datetime.fromisoformat(end_time)
             except ValueError:
                continue

        if end_time < now:
            try:
                candidate.test_completed = True
                problem_title = candidate.assigned_problem.title if candidate.assigned_problem else "Code Test"
                
                # 1. Notify Candidate
                html_candidate = render_template('mail/test_auto_completed.html', 
                                                 candidate=candidate, problem_title=problem_title)
                _send_via_brevo_api(
                    to_list=[{"email": candidate.email, "name": candidate.username}],
                    subject="Coding Test Completed",
                    html_content=html_candidate
                )

                # 2. Notify Admin/Moderator
                recipient_emails = []
                if candidate.moderator_id:
                    moderator = User.query.get(candidate.moderator_id)
                    if moderator: recipient_emails.append(moderator.email)
                else:
                    admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
                    recipient_emails = [a.email for a in admins]

                if recipient_emails and admin_user:
                    # FIX 2: Pass 'admin' object to template
                    html_admin = render_template('mail/test_completed_admin.html',
                                                 candidate=candidate, 
                                                 problem_title=problem_title,
                                                 admin=admin_user)
                    
                    to_list_admin = [{"email": email} for email in recipient_emails]
                    _send_via_brevo_api(
                        to_list=to_list_admin,
                        subject=f"Test Auto-Completed: {candidate.username}",
                        html_content=html_admin
                    )

                complete_count += 1
            except Exception as e:
                logger.error(f"[Scheduler] Failed auto-complete for {candidate.username}: {e}")

    db.session.commit()
    logger.info(f"[Scheduler] Hiring Check Done. Reminders: {remind_count}, Auto-Completed: {complete_count}")