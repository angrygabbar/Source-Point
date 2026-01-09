from extensions import db, celery
import sib_api_v3_sdk
import os
import base64
from datetime import datetime
from flask import render_template

# --- EMAIL BACKEND LOGIC ---
def _send_via_brevo_api(to_list, subject, html_content, cc_list=None, bcc_list=None, attachments=None):
    api_key = os.environ.get('BREVO_API_KEY')
    sender_email = os.environ.get('MAIL_USERNAME', 'admin@sourcepoint.in')
    sender_name = 'Source Point'

    if not api_key:
        print("Brevo API key is not set. Email skipped.")
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
        api_instance.send_transac_email(send_smtp_email)
        print(f"[Celery] Email sent successfully to {[t['email'] for t in to_list]}")
    except Exception as e:
        print(f"[Celery] Error sending email: {e}")

# --- CELERY TASKS ---

@celery.task
def send_email_task(to_list, subject, html_content, cc_list, bcc_list, attachments):
    """Async task to send emails via Brevo."""
    _send_via_brevo_api(to_list, subject, html_content, cc_list, bcc_list, attachments)

@celery.task
def send_single_reminder_task(payment_id):
    """
    Worker task: Processes a single EMI reminder.
    Fetching inside the task ensures data freshness and isolation.
    """
    from utils import send_email
    from models import EMIPayment
    
    # Re-fetch payment to ensure we have fresh data
    payment = EMIPayment.query.get(payment_id)
    if not payment:
        return
        
    # Double check status to prevent race conditions
    if payment.reminder_sent:
        return

    try:
        today = datetime.utcnow().date()
        days_remaining = (payment.due_date - today).days
        
        borrower = payment.plan.borrower
        lender = payment.plan.lender
        
        if borrower and borrower.email:
            send_email(
                to=borrower.email,
                subject=f"Payment Reminder: {payment.description if payment.description else 'EMI'}",
                template="mail/emi_reminder_borrower.html",
                user=borrower,
                lender=lender,
                payment=payment,
                days_remaining=days_remaining
            )

        if lender and lender.email:
            send_email(
                to=lender.email,
                subject=f"Incoming Payment Reminder: {payment.description if payment.description else 'EMI'}",
                template="mail/emi_reminder_lender.html",
                user=lender,
                borrower=borrower,
                payment=payment,
                days_remaining=days_remaining
            )
        
        # Update and Commit
        payment.reminder_sent = True
        db.session.commit()
        print(f"[Celery Worker] Reminder sent for Payment ID {payment.id}")
        
    except Exception as e:
        db.session.rollback()
        print(f"[Worker Error] Failed to send reminder for ID {payment.id}: {e}")

@celery.task
def process_emi_reminders_task():
    """
    Dispatcher task: Finds pending reminders and queues individual tasks.
    This runs quickly and delegates the heavy lifting.
    """
    from models import EMIPayment
    
    today = datetime.utcnow().date()
    print(f"[Celery Dispatcher] Checking EMI Check for {today}...")

    # Fetch pending payments
    batch = EMIPayment.query.filter(
        EMIPayment.status == 'Pending',
        EMIPayment.reminder_sent == False
    ).limit(100).all()

    queued_count = 0
    for payment in batch:
        # Check logic here to avoid queuing unnecessary tasks
        days_remaining = (payment.due_date - today).days
        
        # Only queue if the payment plan exists and it's time to remind
        if payment.plan and 0 <= days_remaining <= payment.reminder_days_before:
            send_single_reminder_task.delay(payment.id)
            queued_count += 1

    print(f"[Celery Dispatcher] Queued {queued_count} reminder tasks.")