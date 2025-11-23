import os
import base64
from functools import wraps
from flask import request, redirect, url_for, flash, render_template
from flask_login import current_user
from extensions import db
import sib_api_v3_sdk
from datetime import datetime

# --- BREVO (SIB) CONFIG ---
BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_USERNAME', 'admin@sourcepoint.in')
MAIL_DEFAULT_SENDER_NAME = 'Source Point'

# Avoid circular import for ActivityLog model
def log_user_action(action, details=None):
    """Logs a user action to the database."""
    from models import ActivityLog 
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
            print(f"Failed to log activity: {e}")

def role_required(roles):
    if not isinstance(roles, list):
        roles = [roles]
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.dashboard'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def send_email(to, subject, template, cc=None, attachments=None, **kwargs):
    """Function to send an email using Brevo (SIB). Adds admin to CC."""
    if not BREVO_API_KEY:
        print("Brevo API key is not set.")
        return False

    admin_email = "sourcepoint.archieve@gmail.com"

    cc_emails = set()
    if cc:
        if isinstance(cc, str):
            cc_emails.add(cc)
        elif isinstance(cc, list):
            cc_emails.update(cc)

    cc_emails.add(admin_email)

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    html_content = render_template(template, **kwargs)

    sender = {"name": MAIL_DEFAULT_SENDER_NAME, "email": MAIL_DEFAULT_SENDER_EMAIL}

    primary_recipients_emails = set()
    if isinstance(to, str):
        to_list = [{"email": to}]
        primary_recipients_emails.add(to)
    else:
        to_list = [{"email": email} for email in to]
        primary_recipients_emails.update(to)

    final_cc_emails = cc_emails - primary_recipients_emails
    cc_list = [{"email": email} for email in final_cc_emails]

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
    if cc_list:
        smtp_email_data["cc"] = cc_list
    if email_attachments:
        smtp_email_data["attachment"] = email_attachments

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(**smtp_email_data)

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except Exception as e:
        print(f"An error occurred while sending email to {to}: {e}")
        return False