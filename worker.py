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
def notify_admin_pending_invoices_task():
    """
    AUTOMATED SCHEDULER TASK (8 AM IST Daily):
    Sends a digest email to the admin with all pending/unpaid/overdue invoices.
    """
    from models.commerce import Invoice
    from models.auth import User
    from decimal import Decimal

    logger.info("[Scheduler] Starting Admin Pending Invoices Digest...")

    # Fetch all non-paid invoices
    pending_invoices = Invoice.query.filter(
        Invoice.status != InvoiceStatus.PAID.value,
        Invoice.status != InvoiceStatus.CANCELLED.value
    ).order_by(Invoice.due_date.asc().nullsfirst()).all()

    if not pending_invoices:
        logger.info("[Scheduler] No pending invoices. Skipping admin digest.")
        return

    today = datetime.utcnow().date()

    # Calculate summary stats
    total_pending_amount = sum(inv.total_amount or Decimal('0') for inv in pending_invoices)

    overdue_invoices = []
    unpaid_invoices = []

    for inv in pending_invoices:
        # Mark overdue flag and compute days for template
        if inv.due_date and inv.due_date < today:
            inv.is_overdue = True
            inv.days_past_due = (today - inv.due_date).days
            inv.days_until_due = None
            overdue_invoices.append(inv)
        else:
            inv.is_overdue = False
            inv.days_past_due = None
            if inv.due_date:
                inv.days_until_due = (inv.due_date - today).days
            else:
                inv.days_until_due = None
            if inv.status == InvoiceStatus.UNPAID.value:
                unpaid_invoices.append(inv)

    # Sort overdue by amount descending (highest first for priority list)
    overdue_invoices.sort(key=lambda x: x.total_amount or 0, reverse=True)

    overdue_amount = sum(inv.total_amount or Decimal('0') for inv in overdue_invoices)
    unpaid_amount = sum(inv.total_amount or Decimal('0') for inv in unpaid_invoices)

    # Format report dates in IST
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    report_date = ist_now.strftime('%A, %B %d, %Y — %I:%M %p IST')
    report_date_short = ist_now.strftime('%d %b %Y')

    try:
        html_content = render_template('mail/admin_pending_invoices_digest.html',
            pending_invoices=pending_invoices,
            total_pending_amount=total_pending_amount,
            overdue_count=len(overdue_invoices),
            overdue_amount=overdue_amount,
            unpaid_count=len(unpaid_invoices),
            unpaid_amount=unpaid_amount,
            report_date=report_date,
            report_date_short=report_date_short
        )

        # Send to all admin users
        admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
        admin_emails = [{"email": a.email, "name": a.username} for a in admins if a.email]

        if admin_emails:
            _send_via_brevo_api(
                to_list=admin_emails,
                subject=f"📊 Daily Pending Invoices Report — {len(pending_invoices)} Unpaid (₹{total_pending_amount})",
                html_content=html_content
            )
            logger.info(f"[Scheduler] Admin digest sent: {len(pending_invoices)} invoices, ₹{total_pending_amount} pending.")
        else:
            logger.warning("[Scheduler] No admin users found to send digest.")

    except Exception as e:
        logger.error(f"[Scheduler] Admin invoice digest failed: {e}")

@celery.task
def notify_admin_inventory_digest_task():
    """
    AUTOMATED SCHEDULER TASK (8:30 AM IST Daily):
    Sends a comprehensive inventory report to admin — out-of-stock, low-stock,
    category breakdown, seller allocations, and pending stock requests.
    """
    from models.commerce import Product, SellerInventory, StockRequest
    from models.auth import User
    from decimal import Decimal
    from sqlalchemy import func

    LOW_STOCK_THRESHOLD = 5  # Products with stock <= this are "low stock"

    logger.info("[Scheduler] Starting Admin Inventory Digest...")

    # --- 1. Fetch all products ---
    all_products = Product.query.order_by(Product.stock.asc()).all()
    if not all_products:
        logger.info("[Scheduler] No products in catalog. Skipping inventory digest.")
        return

    # --- 2. Classify products ---
    out_of_stock_products = [p for p in all_products if p.stock <= 0]
    low_stock_products = [p for p in all_products if 0 < p.stock <= LOW_STOCK_THRESHOLD]
    
    total_products = len(all_products)
    total_stock_units = sum(max(p.stock, 0) for p in all_products)
    total_inventory_value = sum((p.price or Decimal('0')) * max(p.stock, 0) for p in all_products)

    # --- 3. Category breakdown ---
    category_data = db.session.query(
        Product.category,
        func.count(Product.id).label('count'),
        func.sum(Product.stock).label('total_stock'),
        func.sum(Product.price * Product.stock).label('stock_value')
    ).group_by(Product.category).all()

    category_breakdown = []
    for cat in category_data:
        category_breakdown.append({
            'category': cat.category or 'Uncategorized',
            'count': cat.count,
            'total_stock': max(cat.total_stock or 0, 0),
            'stock_value': max(float(cat.stock_value or 0), 0)
        })
    category_breakdown.sort(key=lambda x: x['stock_value'], reverse=True)

    # --- 4. Seller inventory summary ---
    sellers_with_inventory = db.session.query(
        User.id, User.username, User.email,
        func.count(SellerInventory.id).label('product_count'),
        func.sum(SellerInventory.stock).label('total_stock')
    ).join(SellerInventory, SellerInventory.seller_id == User.id
    ).group_by(User.id, User.username, User.email).all()

    seller_summary = []
    for s in sellers_with_inventory:
        # Calculate stock value for this seller
        seller_items = SellerInventory.query.filter_by(seller_id=s.id).all()
        stock_value = sum(
            (item.product.price or Decimal('0')) * max(item.stock, 0) 
            for item in seller_items if item.product
        )
        seller_summary.append({
            'name': s.username,
            'email': s.email,
            'product_count': s.product_count,
            'total_stock': max(s.total_stock or 0, 0),
            'stock_value': float(stock_value)
        })
    seller_summary.sort(key=lambda x: x['stock_value'], reverse=True)

    # --- 5. Pending stock requests ---
    pending_requests_count = StockRequest.query.filter_by(status='Pending').count()

    # --- 6. Format dates ---
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    report_date = ist_now.strftime('%A, %B %d, %Y — %I:%M %p IST')
    report_date_short = ist_now.strftime('%d %b %Y')

    try:
        html_content = render_template('mail/admin_inventory_digest.html',
            total_products=total_products,
            total_stock_units=total_stock_units,
            total_inventory_value=total_inventory_value,
            out_of_stock_count=len(out_of_stock_products),
            out_of_stock_products=out_of_stock_products,
            low_stock_count=len(low_stock_products),
            low_stock_products=low_stock_products,
            low_stock_threshold=LOW_STOCK_THRESHOLD,
            category_breakdown=category_breakdown,
            seller_summary=seller_summary,
            pending_requests_count=pending_requests_count,
            report_date=report_date,
            report_date_short=report_date_short
        )

        # Send to all admin users
        admins = User.query.filter_by(role=UserRole.ADMIN.value).all()
        admin_emails = [{"email": a.email, "name": a.username} for a in admins if a.email]

        if admin_emails:
            subject_parts = [f"📦 Daily Inventory Report — {total_products} Products"]
            if len(out_of_stock_products) > 0:
                subject_parts.append(f"{len(out_of_stock_products)} Out of Stock")
            if len(low_stock_products) > 0:
                subject_parts.append(f"{len(low_stock_products)} Low Stock")

            _send_via_brevo_api(
                to_list=admin_emails,
                subject=" · ".join(subject_parts),
                html_content=html_content
            )
            logger.info(f"[Scheduler] Inventory digest sent: {total_products} products, "
                        f"{len(out_of_stock_products)} OOS, {len(low_stock_products)} low stock.")
        else:
            logger.warning("[Scheduler] No admin users found to send inventory digest.")

    except Exception as e:
        logger.error(f"[Scheduler] Admin inventory digest failed: {e}")

@celery.task
def notify_sellers_inventory_digest_task():
    """
    AUTOMATED SCHEDULER TASK (9 AM IST Daily):
    Sends each seller a personalized inventory digest showing ONLY their own
    allocated products, stock levels, and pending stock requests.
    """
    from models.commerce import Product, SellerInventory, StockRequest
    from models.auth import User
    from decimal import Decimal

    LOW_STOCK_THRESHOLD = 5

    logger.info("[Scheduler] Starting Seller Inventory Digests...")

    # Get all sellers who have inventory allocations
    sellers = db.session.query(User).filter(
        User.role == UserRole.SELLER.value,
        User.id.in_(db.session.query(SellerInventory.seller_id).distinct())
    ).all()

    if not sellers:
        logger.info("[Scheduler] No sellers with inventory found. Skipping.")
        return

    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    report_date = ist_now.strftime('%A, %B %d, %Y — %I:%M %p IST')
    report_date_short = ist_now.strftime('%d %b %Y')

    sent_count = 0

    for seller in sellers:
        try:
            # Get this seller's inventory items with product details
            seller_inventory = SellerInventory.query.filter_by(
                seller_id=seller.id
            ).all()

            if not seller_inventory:
                continue

            # Build item list for template
            inventory_items = []
            for si in seller_inventory:
                product = si.product
                if not product:
                    continue
                inventory_items.append({
                    'product_code': product.product_code or f'SP-{product.id:04d}',
                    'product_name': product.name,
                    'brand': product.brand,
                    'category': product.category,
                    'unit_price': float(product.price or 0),
                    'stock': si.stock,
                })

            # Sort: out of stock first, then low stock, then by name
            inventory_items.sort(key=lambda x: (
                0 if x['stock'] <= 0 else (1 if x['stock'] <= LOW_STOCK_THRESHOLD else 2),
                x['product_name']
            ))

            # Calculate stats
            total_products = len(inventory_items)
            total_stock_units = sum(max(i['stock'], 0) for i in inventory_items)
            total_stock_value = sum(i['unit_price'] * max(i['stock'], 0) for i in inventory_items)
            out_of_stock_count = sum(1 for i in inventory_items if i['stock'] <= 0)
            low_stock_count = sum(1 for i in inventory_items if 0 < i['stock'] <= LOW_STOCK_THRESHOLD)
            healthy_count = total_products - out_of_stock_count - low_stock_count

            # Get this seller's pending stock requests
            pending_reqs = StockRequest.query.filter_by(
                seller_id=seller.id, status='Pending'
            ).order_by(StockRequest.request_date.desc()).all()

            pending_requests = []
            for req in pending_reqs:
                pending_requests.append({
                    'product_name': req.product.name if req.product else 'Unknown',
                    'quantity': req.quantity,
                    'request_date': req.request_date.strftime('%d %b %Y') if req.request_date else 'N/A'
                })

            html_content = render_template('mail/seller_inventory_digest.html',
                seller_name=seller.username,
                total_products=total_products,
                total_stock_units=total_stock_units,
                total_stock_value=total_stock_value,
                out_of_stock_count=out_of_stock_count,
                low_stock_count=low_stock_count,
                healthy_count=healthy_count,
                low_stock_threshold=LOW_STOCK_THRESHOLD,
                inventory_items=inventory_items,
                pending_requests=pending_requests,
                report_date=report_date,
                report_date_short=report_date_short
            )

            # Build subject line
            subject = f"📦 Your Daily Inventory Report — {total_products} Products, {total_stock_units} Units"
            if out_of_stock_count > 0:
                subject += f" · ⚠️ {out_of_stock_count} Out of Stock"

            _send_via_brevo_api(
                to_list=[{"email": seller.email, "name": seller.username}],
                subject=subject,
                html_content=html_content
            )
            sent_count += 1
            logger.info(f"[Scheduler] Seller digest sent to {seller.username}: "
                        f"{total_products} products, {out_of_stock_count} OOS.")

        except Exception as e:
            logger.error(f"[Scheduler] Seller digest failed for {seller.username}: {e}")

    logger.info(f"[Scheduler] Completed seller digests: {sent_count}/{len(sellers)} sent.")

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