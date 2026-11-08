import base64
import os
from functools import wraps
from flask import request, redirect, url_for, flash, render_template, current_app
from flask_login import current_user
from extensions import db

# --- LOGGING ---
def log_user_action(action, details=None):
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
            print(f"Failed to log activity: {e}")

# --- AUTH DECORATOR ---
def role_required(roles):
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


def _json_safe_attachments(attachments):
    """Encode binary attachments so they can be sent through Celery's JSON queue."""
    if not attachments:
        return attachments

    queue_attachments = []
    for attachment in attachments:
        queued_attachment = dict(attachment)
        data = queued_attachment.pop('data', None)
        if isinstance(data, (bytes, bytearray, memoryview)):
            queued_attachment['data_base64'] = base64.b64encode(data).decode('ascii')
        elif data is not None:
            queued_attachment['data'] = data
        queue_attachments.append(queued_attachment)
    return queue_attachments


def enqueue_email_job(task, *args, **kwargs):
    """Queue a mail task only when a Celery worker is reachable; return its ID."""
    try:
        workers = task.app.control.inspect(timeout=1).ping() or {}
    except Exception as error:
        raise RuntimeError("The email worker could not be reached. Check Redis and Celery on the server.") from error
    if not workers:
        raise RuntimeError("No email worker is available. Check the Celery worker service on the server.")
    return task.delay(*args, **kwargs).id

# --- EMAIL SERVICE (UPDATED) ---

def send_email(to, subject, template, cc=None, bcc=None, attachments=None, sync=False,
               return_task_id=False, require_worker=False, **kwargs):
    """
    Renders the email template and sends it.
    Args:
        sync (bool): If True, sends immediately (blocking). If False, sends via Celery (background).
    """
    # Avoid circular import
    from worker import send_email_task

    admin_email   = 'admin@sourcepoint.in'
    archive_email = 'sourcepoint.archieve@gmail.com'

    # CC Logic
    cc_emails = set()
    if cc:
        if isinstance(cc, str): cc_emails.add(cc)
        elif isinstance(cc, list): cc_emails.update(cc)
    cc_emails.add(admin_email)
    cc_emails.add(archive_email)

    # To Logic
    primary_recipients_emails = set()
    if isinstance(to, str):
        to_list = [{"email": to}]
        primary_recipients_emails.add(to)
    else:
        to_list = [{"email": email} for email in to]
        primary_recipients_emails.update(to)

    final_cc_emails = cc_emails - primary_recipients_emails
    cc_list = [{"email": email} for email in final_cc_emails] if final_cc_emails else None

    bcc_list = None
    if bcc:
        if isinstance(bcc, str): bcc_list = [{"email": bcc}]
        elif isinstance(bcc, list): bcc_list = [{"email": email} for email in bcc if email]

    # Render Template (Needs Request/App Context)
    try:
        html_content = render_template(template, **kwargs)
    except Exception as e:
        print(f"Template Rendering Error: {e}")
        raise e

    # Dispatch
    if sync:
        # Run immediately in this thread (Blocking) and return the provider result.
        # This is used for transactional admin actions that must not claim an email
        # was sent when the queue or email provider is unavailable.
        return bool(send_email_task(to_list, subject, html_content, cc_list, bcc_list, attachments))
    else:
        # Queue delivery so slow email-provider responses do not hold open an
        # HTTP request through Cloudflare. Transactional API callers can ask for
        # the Celery task ID and report its eventual result to the client.
        task_args = (to_list, subject, html_content, cc_list, bcc_list, _json_safe_attachments(attachments))
        task_id = enqueue_email_job(send_email_task, *task_args) if require_worker else send_email_task.delay(*task_args).id
        if return_task_id:
            return task_id

    return True
