import os
import base64
from functools import wraps
from flask import request, redirect, url_for, flash, render_template, current_app
from flask_login import current_user
from extensions import db
import sib_api_v3_sdk
from datetime import datetime
import threading

# --- CONFIGURATION ---
BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_USERNAME', 'admin@sourcepoint.in')
MAIL_DEFAULT_SENDER_NAME = 'Source Point'

# --- LOGGING ---
def log_user_action(action, details=None):
    """Logs a user action to the database."""
    # Local import to prevent circular dependency with models/auth.py
    from models.auth import ActivityLog 
    
    if current_user.is_authenticated:
        try:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            new_log = ActivityLog(
                user_id=current_user.id,
                action=action,
                details=details,
                ip_address=ip_address
            )
            db.session.add(new_log)
            db.session.commit()
        except Exception as e:
            # Use logging in production instead of print
            print(f"Failed to log activity: {e}")

# --- AUTH DECORATOR ---
def role_required(roles):
    """
    Decorator to restrict access based on user roles.
    Accepts a single role string or a list of role strings.
    """
    if not isinstance(roles, list):
        roles = [roles]
        
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login_register'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.home')) 
                
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- EMAIL SERVICE ---

def _send_via_brevo_api(to_list, subject, html_content, cc_list=None, attachments=None):
    """
    Internal function that strictly handles the Brevo API call.
    Independent of Flask Context to allow for Celery extraction later.
    """
    if not BREVO_API_KEY:
        print("Brevo API key is not set. Email skipped.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = {"name": MAIL_DEFAULT_SENDER_NAME, "email": MAIL_DEFAULT_SENDER_EMAIL}

    email_attachments = []
    if attachments:
        for attachment_data in attachments:
            # Ensure content is encoded properly
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
    if cc_list:
        smtp_email_data["cc"] = cc_list
    if email_attachments:
        smtp_email_data["attachment"] = email_attachments

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(**smtp_email_data)

    try:
        api_instance.send_transac_email(send_smtp_email)
        print(f"Email sent successfully to {[t['email'] for t in to_list]}")
    except Exception as e:
        print(f"An error occurred while sending email: {e}")

def send_async_email_thread(app, to_list, subject, html_content, cc_list, attachments):
    """
    Wrapper for threading. Needs app context because it might access config (though Brevo logic is separated).
    """
    with app.app_context():
        _send_via_brevo_api(to_list, subject, html_content, cc_list, attachments)

def send_email(to, subject, template, cc=None, attachments=None, **kwargs):
    """
    Public interface to send emails.
    Renders template and offloads sending to a background thread.
    """
    admin_email = "sourcepoint.archieve@gmail.com"

    # CC Logic
    cc_emails = set()
    if cc:
        if isinstance(cc, str):
            cc_emails.add(cc)
        elif isinstance(cc, list):
            cc_emails.update(cc)
    cc_emails.add(admin_email)

    # To Logic
    primary_recipients_emails = set()
    if isinstance(to, str):
        to_list = [{"email": to}]
        primary_recipients_emails.add(to)
    else:
        to_list = [{"email": email} for email in to]
        primary_recipients_emails.update(to)

    # Filter CCs that are already in To
    final_cc_emails = cc_emails - primary_recipients_emails
    cc_list = [{"email": email} for email in final_cc_emails] if final_cc_emails else None

    # Render Template (Must be done in Request Context)
    html_content = render_template(template, **kwargs)

    # --- ASYNC EXECUTION ---
    # NOTE: To upgrade to Celery:
    # 1. Install redis & celery
    # 2. Move _send_via_brevo_api to tasks.py and decorate with @celery.task
    # 3. Replace the thread block below with: send_email_task.delay(...)
    
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=send_async_email_thread,
        args=(app, to_list, subject, html_content, cc_list, attachments)
    )
    thread.start()

    return True