from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User, ActivityLog
from models.hiring import JobApplication, CodeSnippet
from models.commerce import Order, StockRequest
from models.finance import Project, Transaction, BRD, EMIPlan, EMIPayment
from models.learning import LearningContent
# Updated Import: Added MAIL_DEFAULT_SENDER_EMAIL
from utils import role_required, log_user_action, send_email, MAIL_DEFAULT_SENDER_EMAIL
from invoice_service import BrdGenerator
from datetime import datetime, timedelta
from sqlalchemy import func
from werkzeug.utils import secure_filename
import csv
from io import TextIOWrapper
import re
import pypdf
from enums import UserRole, ApplicationStatus, OrderStatus

admin_core_bp = Blueprint('admin_core', __name__, url_prefix='/admin')

# =========================================================
# DASHBOARD & ANALYTICS
# =========================================================

@admin_core_bp.route('/')
@login_required
@role_required(UserRole.ADMIN.value)
def admin_dashboard():
    # 1. Pending Users
    pending_users_count = User.query.filter_by(is_approved=False).count()
    pending_users = User.query.filter_by(is_approved=False).limit(10).all()

    # 2. Snippets
    received_snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id)\
        .order_by(CodeSnippet.timestamp.desc()).limit(5).all()

    # 3. Applications
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).limit(10).all()
    
    pending_apps_count = JobApplication.query.filter_by(status=ApplicationStatus.PENDING.value).count()

    # 4. Activity Logs
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
    
    # 5. Directories
    candidates = User.query.filter_by(role=UserRole.CANDIDATE.value).limit(50).all()
    developers = User.query.filter_by(role=UserRole.DEVELOPER.value).limit(50).all()
    moderators = User.query.filter_by(role=UserRole.MODERATOR.value).limit(50).all()
    sellers = User.query.filter_by(role=UserRole.SELLER.value).limit(50).all()
    buyers = User.query.filter_by(role=UserRole.BUYER.value).limit(50).all()
    recruiters = User.query.filter_by(role=UserRole.RECRUITER.value).limit(50).all()
    
    # 6. Scheduling
    scheduled_candidates = User.query.filter(
        User.role == UserRole.CANDIDATE.value,
        User.problem_statement_id != None,
        User.moderator_id == None
    ).all()

    assigned_candidates_with_moderators = User.query.filter(
        User.role == UserRole.CANDIDATE.value,
        User.moderator_id.isnot(None)
    ).order_by(User.test_start_time.asc()).limit(20).all()
    
    moderator_ids = list(set([c.moderator_id for c in assigned_candidates_with_moderators]))
    moderators_for_assignments = User.query.filter(User.id.in_(moderator_ids)).all()
    moderators_map = {m.id: m for m in moderators_for_assignments}
    
    # 7. Orders & Stock Stats
    pending_orders_count = Order.query.filter_by(status=OrderStatus.PLACED.value).count()
    pending_requests_count = StockRequest.query.filter_by(status='Pending').count()

    return render_template('admin_dashboard.html',
                           pending_users=pending_users,
                           pending_users_count=pending_users_count,
                           received_snippets=received_snippets,
                           applications=applications, 
                           pending_apps_count=pending_apps_count,
                           recent_logs=recent_logs,
                           candidates=candidates,
                           developers=developers,
                           moderators=moderators,
                           sellers=sellers,
                           buyers=buyers,
                           recruiters=recruiters,
                           scheduled_candidates=scheduled_candidates,
                           assigned_candidates_with_moderators=assigned_candidates_with_moderators,
                           moderators_map=moderators_map,
                           pending_orders_count=pending_orders_count,
                           pending_requests_count=pending_requests_count)

@admin_core_bp.route('/analytics')
@login_required
@role_required(UserRole.ADMIN.value)
def admin_analytics():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime(2000, 1, 1)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) if end_date_str else datetime.utcnow() + timedelta(days=1)

    finance_query = db.session.query(func.sum(Transaction.amount), Transaction.category).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).group_by(Transaction.category).all()
    
    total_funding = 0
    total_expense = 0
    for amount, category in finance_query:
        if category == 'funding': total_funding = amount
        elif category == 'expense': total_expense = amount
    
    app_query = db.session.query(func.count(JobApplication.id), JobApplication.status).filter(
        JobApplication.applied_at >= start_date,
        JobApplication.applied_at < end_date
    ).group_by(JobApplication.status).all()

    pending_apps = 0
    accepted_apps = 0
    rejected_apps = 0
    for count, status in app_query:
        if status == ApplicationStatus.PENDING.value: pending_apps = count
        elif status == ApplicationStatus.ACCEPTED.value: accepted_apps = count
        elif status == ApplicationStatus.REJECTED.value: rejected_apps = count
    
    project_status_counts = db.session.query(Project.status, func.count(Project.id)).filter(
        Project.start_date >= start_date,
        Project.start_date < end_date
    ).group_by(Project.status).all()
    
    proj_statuses = [s[0] for s in project_status_counts]
    proj_counts = [s[1] for s in project_status_counts]

    display_start = start_date_str if start_date_str else ''
    display_end = end_date_str if end_date_str else ''

    return render_template('admin_analytics.html',
                           total_funding=total_funding,
                           total_expense=total_expense,
                           pending_apps=pending_apps,
                           accepted_apps=accepted_apps,
                           rejected_apps=rejected_apps,
                           proj_statuses=proj_statuses,
                           proj_counts=proj_counts,
                           start_date=display_start,
                           end_date=display_end)

@admin_core_bp.route('/activity_logs')
@login_required
@role_required(UserRole.ADMIN.value)
def admin_activity_logs():
    filter_user = request.args.get('user')
    filter_action = request.args.get('action')
    filter_date = request.args.get('date')

    query = ActivityLog.query

    if filter_user:
        query = query.join(User).filter(User.username.ilike(f"%{filter_user}%"))
    if filter_action:
        query = query.filter(ActivityLog.action.ilike(f"%{filter_action}%"))
    if filter_date:
        date_obj = datetime.strptime(filter_date, '%Y-%m-%d')
        query = query.filter(func.date(ActivityLog.timestamp) == date_obj.date())
    
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return render_template('admin_activity_logs.html', logs=logs)

# =========================================================
# EMAIL TOOLS
# =========================================================

@admin_core_bp.route('/broadcast_email', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def broadcast_email():
    if request.method == 'POST':
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')

        if not subject or not body:
            flash('Subject and body are required.', 'danger')
            return redirect(url_for('admin_core.broadcast_email'))

        attachments = []
        if file and file.filename != '':
            file_data = file.read()
            attachments.append({
                'filename': secure_filename(file.filename),
                'content_type': file.content_type,
                'data': file_data
            })

        signature = """<br><br>...Source Point Team...""" 
        final_body = body + signature

        # --- UPDATED LOGIC: SEND WITH BCC ---
        users = User.query.all()
        # Collect all valid emails
        bcc_recipients = [u.email for u in users if u.email]
        
        # FIX: Set the "To" address to the System Sender (e.g., admin@sourcepoint.in)
        # This prevents the specific admin's personal email from showing in the "To" field.
        # Everyone else remains hidden in BCC.
        to_email = MAIL_DEFAULT_SENDER_EMAIL
        
        # Ensure the 'To' email is not also in the 'BCC' list to avoid duplicate delivery
        if to_email in bcc_recipients:
            bcc_recipients.remove(to_email)

        if bcc_recipients or to_email:
            send_email(
                to=to_email,
                bcc=bcc_recipients,
                subject=subject,
                template="mail/broadcast.html",
                user=current_user,
                body=final_body,
                attachments=attachments
            )
            count = len(bcc_recipients)
            log_user_action("Broadcast Email", f"Sent broadcast email with subject: {subject} to {count} users (BCC)")
            flash(f'Broadcast sent successfully to {count} users (via BCC).', 'success')
        else:
            flash('No recipients found to broadcast to.', 'warning')

        return redirect(url_for('admin_core.admin_dashboard'))
    return render_template('broadcast_email.html')

@admin_core_bp.route('/send_specific_email', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def send_specific_email():
    if request.method == 'POST':
        user_ids = request.form.getlist('user_ids')
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')

        if not user_ids:
            flash('Please select at least one user.', 'danger')
            return redirect(url_for('admin_core.send_specific_email'))

        if not subject or not body:
            flash('Subject and body are required.', 'danger')
            return redirect(url_for('admin_core.send_specific_email'))

        attachments = []
        if file and file.filename != '':
            file_data = file.read()
            attachments.append({
                'filename': secure_filename(file.filename),
                'content_type': file.content_type,
                'data': file_data
            })

        signature = """<br><br>...Source Point Team..."""
        final_body = body + signature

        users = User.query.filter(User.id.in_(user_ids)).all()
        count = 0
        for user in users:
            if user.email:
                send_email(to=user.email, subject=subject, template="mail/broadcast.html", user=user, body=final_body, attachments=attachments)
                count += 1
        
        log_user_action("Send Specific Email", f"Sent email to {count} recipients.")
        flash(f'Email has been sent to {count} users.', 'success')
        return redirect(url_for('admin_core.admin_dashboard'))

    users = User.query.all()
    return render_template('send_specific_email.html', users=users)

@admin_core_bp.route('/update_learning_content', methods=['POST'])
@login_required
@role_required([UserRole.ADMIN.value, UserRole.DEVELOPER.value])
def update_learning_content():
    language_id = request.form.get('language_id')
    content = request.form.get('content')

    learning_content = LearningContent.query.get(language_id)
    if learning_content:
        learning_content.content = content
        db.session.commit()
        log_user_action("Update Learning Content", f"Updated content for {language_id}")
        flash(f'The {language_id.upper()} learning page has been updated.', 'success')
    else:
        flash(f'Could not find the learning page for {language_id.upper()}.', 'danger')

    return redirect(url_for('main.learn_language', language=language_id))

# =========================================================
# FINANCE (Projects & EMI)
# =========================================================

@admin_core_bp.route('/projects')
@login_required
@role_required(UserRole.ADMIN.value)
def projects():
    return render_template('projects_hub.html')

@admin_core_bp.route('/manage_projects')
@login_required
@role_required(UserRole.ADMIN.value)
def manage_projects():
    projects = Project.query.order_by(Project.start_date.desc()).all()
    return render_template('manage_projects.html', projects=projects)

@admin_core_bp.route('/create_project', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        budget = request.form.get('budget')
        status = request.form.get('status')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        new_project = Project(name=name, description=description, start_date=start_date, end_date=end_date, budget=float(budget) if budget else 0.0, status=status)
        db.session.add(new_project)
        db.session.commit()
        log_user_action("Create Project", f"Created project {name}")
        flash(f'Project "{name}" created.', 'success')
        return redirect(url_for('admin_core.manage_projects'))
    return render_template('create_project.html')

@admin_core_bp.route('/project/<int:project_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@admin_core_bp.route('/project/<int:project_id>/add_transaction', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def add_transaction(project_id):
    project = Project.query.get_or_404(project_id)
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    category = request.form.get('category')
    date_str = request.form.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    new_transaction = Transaction(description=description, amount=amount, category=category, date=date, project_id=project.id)
    db.session.add(new_transaction)
    db.session.commit()
    log_user_action("Add Transaction", f"Added transaction to project {project.name}")
    flash(f'Transaction for "{project.name}" added.', 'success')
    return redirect(url_for('admin_core.project_detail', project_id=project.id))

@admin_core_bp.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if request.method == 'POST':
        transaction.description = request.form.get('description')
        transaction.amount = float(request.form.get('amount'))
        transaction.category = request.form.get('category')
        date_str = request.form.get('date')
        transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else transaction.date
        db.session.commit()
        flash('Transaction updated successfully.', 'success')
        return redirect(url_for('admin_core.project_detail', project_id=transaction.project_id))
    return render_template('edit_transaction.html', transaction=transaction)

@admin_core_bp.route('/delete_transaction/<int:transaction_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    project_id = transaction.project_id
    db.session.delete(transaction)
    db.session.commit()
    log_user_action("Delete Transaction", f"Deleted transaction ID {transaction_id}")
    flash('Transaction deleted.', 'success')
    return redirect(url_for('admin_core.project_detail', project_id=project_id))

@admin_core_bp.route('/project/<int:project_id>/update_status', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_project_status(project_id):
    project = Project.query.get_or_404(project_id)
    new_status = request.form.get('status')
    if new_status:
        project.status = new_status
        db.session.commit()
        flash(f'Project status updated to "{new_status}".', 'success')
    return redirect(url_for('admin_core.project_detail', project_id=project.id))

@admin_core_bp.route('/project/<int:project_id>/brd')
@login_required
@role_required(UserRole.ADMIN.value)
def view_brd(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('brd_details.html', project=project)

@admin_core_bp.route('/project/<int:project_id>/brd/edit', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def edit_brd(project_id):
    project = Project.query.get_or_404(project_id)
    brd = project.brd or BRD(project_id=project_id)

    if request.method == 'POST':
        brd.executive_summary = request.form.get('executive_summary')
        brd.project_objectives = request.form.get('project_objectives')
        brd.project_scope = request.form.get('project_scope')
        brd.business_requirements = request.form.get('business_requirements')
        brd.key_stakeholders = request.form.get('key_stakeholders')
        brd.project_constraints = request.form.get('project_constraints')
        brd.cost_benefit_analysis = request.form.get('cost_benefit_analysis')

        if not project.brd:
            db.session.add(brd)

        db.session.commit()
        flash('BRD updated successfully.', 'success')
        return redirect(url_for('admin_core.view_brd', project_id=project.id))

    return render_template('edit_brd.html', project=project, brd=brd)

@admin_core_bp.route('/project/<int:project_id>/brd/share', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def share_brd(project_id):
    project = Project.query.get_or_404(project_id)
    recipient_email = request.form.get('recipient_email')

    if not recipient_email:
        flash('Recipient email is required.', 'danger')
        return redirect(url_for('admin_core.view_brd', project_id=project.id))

    brd_generator = BrdGenerator(project)
    pdf_data = brd_generator.generate_pdf()
    attachment = {'filename': f'BRD_{project.name}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}

    send_email(
        to=recipient_email, subject=f'Business Requirement Document for {project.name}',
        template='mail/brd_shared.html', project_name=project.name, attachments=[attachment], now=datetime.utcnow()
    )
    
    log_user_action("Share BRD", f"Shared BRD for {project.name} with {recipient_email}")
    flash(f'BRD for {project.name} sent to {recipient_email}.', 'success')
    return redirect(url_for('admin_core.view_brd', project_id=project.id))

@admin_core_bp.route('/emi_manager')
@login_required
@role_required(UserRole.ADMIN.value)
def emi_manager():
    plans = EMIPlan.query.order_by(EMIPlan.created_at.desc()).all()
    # Filter by not admin using Enum value (if consistent with model data)
    users = User.query.filter(User.role != UserRole.ADMIN.value).order_by(User.username).all()
    return render_template('emi_manager.html', plans=plans, users=users)

@admin_core_bp.route('/emi_manager/import', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def import_emi_schedule():
    borrower_id = request.form.get('borrower_id')
    lender_id = request.form.get('lender_id')
    title = request.form.get('title')
    reminder_days = int(request.form.get('reminder_days', 3))
    file = request.files.get('schedule_file')

    if not borrower_id or not lender_id or not title or not file:
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin_core.emi_manager'))

    if borrower_id == lender_id:
        flash('Borrower and Lender cannot be the same user.', 'danger')
        return redirect(url_for('admin_core.emi_manager'))

    filename = secure_filename(file.filename)
    payments_to_add = []
    total_amount = 0.0
    processing_fee = 0.0

    try:
        if filename.endswith('.csv'):
            csv_file = TextIOWrapper(file, encoding='utf-8')
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                try:
                    amount = float(row.get('Amount', 0).replace(',', ''))
                    description = row.get('Description', f'Installment for {title}')
                    if 'processing fee' in description.lower():
                        processing_fee += amount
                        continue

                    date_str = row.get('Date', '')
                    try:
                        due_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        due_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    if amount > 0 and due_date:
                        total_amount += amount
                        payments_to_add.append({
                            'due_date': due_date, 
                            'amount': amount, 
                            'description': description
                        })
                except Exception as e:
                    print(f"Skipping CSV row error: {e}")
                    continue
        
        elif filename.endswith('.pdf'):
            try:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages: 
                    text += page.extract_text() + "\n"
                
                lines = text.split('\n')
                date_pattern_num = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')
                date_pattern_text = re.compile(r'\b(\d{1,2})[\s/-]*([A-Za-z]{3})[\s/-]*(\d{4})\b')
                fee_pattern = re.compile(r'Processing\s*Fee\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.?\d*)', re.IGNORECASE)

                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if 'txn date' in line.lower() or 'transaction date' in line.lower(): continue

                    fee_match = fee_pattern.search(line)
                    if fee_match:
                        try:
                            fee_val = float(fee_match.group(1).replace(',', ''))
                            processing_fee += fee_val
                        except ValueError: pass
                        continue

                    due_date = None
                    end_of_date_index = 0

                    text_match = date_pattern_text.search(line)
                    if text_match:
                        try:
                            day, month, year = text_match.groups()
                            date_str = f"{day}-{month}-{year}"
                            due_date = datetime.strptime(date_str, '%d-%b-%Y').date()
                            end_of_date_index = text_match.end()
                        except ValueError: pass
                    
                    if not due_date:
                        num_match = date_pattern_num.search(line)
                        if num_match:
                            try:
                                day, month, year = num_match.groups()
                                if len(year) == 2: year = "20" + year
                                due_date = datetime(int(year), int(month), int(day)).date()
                                end_of_date_index = num_match.end()
                            except ValueError: pass

                    if due_date:
                        remaining_text = line[end_of_date_index:]
                        amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', remaining_text)
                        
                        if amount_matches:
                            amount_str = amount_matches[0].replace(',', '')
                            try:
                                amount = float(amount_str)
                                if amount > 0:
                                    payments_to_add.append({
                                        'due_date': due_date, 
                                        'amount': amount, 
                                        'description': f'Installment for {title}'
                                    })
                                    total_amount += amount
                            except ValueError: continue

            except Exception as e:
                flash('Error reading PDF file.', 'danger')
                return redirect(url_for('admin_core.emi_manager'))

        if not payments_to_add:
            flash('No valid payment records found.', 'warning')
            return redirect(url_for('admin_core.emi_manager'))

        payments_to_add.sort(key=lambda x: x['due_date'])

        if processing_fee > 0 and payments_to_add:
            payments_to_add[0]['amount'] += processing_fee
            payments_to_add[0]['description'] += f" + Proc. Fee ({processing_fee})"
            total_amount += processing_fee

        new_plan = EMIPlan(borrower_id=borrower_id, lender_id=lender_id, title=title, total_principal=total_amount)
        db.session.add(new_plan)
        db.session.commit()

        for index, pay in enumerate(payments_to_add, start=1):
            payment = EMIPayment(
                plan_id=new_plan.id, installment_number=index, due_date=pay['due_date'],
                amount=pay['amount'], description=pay['description'], reminder_days_before=reminder_days
            )
            db.session.add(payment)
        
        db.session.commit()
        log_user_action("Create EMI Plan", f"Created plan '{title}' for Borrower {borrower_id}")
        flash(f'EMI Schedule imported successfully ({len(payments_to_add)} installments).', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Failed to process file: {str(e)}', 'danger')

    return redirect(url_for('admin_core.emi_manager'))

@admin_core_bp.route('/emi_manager/update_payment', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def update_emi_payment():
    payment_id = request.form.get('payment_id')
    amount = request.form.get('amount')
    due_date_str = request.form.get('due_date')
    description = request.form.get('description')
    status = request.form.get('status')

    payment = EMIPayment.query.get_or_404(payment_id)
    
    if amount: payment.amount = float(amount)
    if due_date_str: payment.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    if description: payment.description = description
    if status:
        payment.status = status
        if status == 'Pending': payment.payment_date = None
        elif status == 'Paid' and not payment.payment_date: payment.payment_date = datetime.utcnow()
        
    db.session.commit()
    log_user_action("Update EMI Payment", f"Updated installment #{payment.installment_number} for plan {payment.plan.title}")
    
    flash('Payment details updated successfully.', 'success')
    return redirect(url_for('admin_core.emi_manager'))

@admin_core_bp.route('/emi_manager/mark_paid/<int:payment_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def mark_emi_paid(payment_id):
    payment = EMIPayment.query.get_or_404(payment_id)
    
    if payment.status == 'Paid':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Payment already marked as Paid.'})
        flash('Payment is already paid.', 'warning')
        return redirect(url_for('admin_core.emi_manager'))

    payment.status = 'Paid'
    payment.payment_date = datetime.utcnow()
    db.session.commit()

    try:
        send_email(
            to=payment.plan.lender.email,
            subject=f"Payment Received: {payment.description}",
            template="mail/emi_paid_notification_lender.html",
            lender=payment.plan.lender, borrower=payment.plan.borrower, payment=payment, paid_date=datetime.utcnow()
        )
    except Exception: pass

    log_user_action("Mark EMI Paid", f"Marked installment #{payment.installment_number} as paid")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': f'Installment marked as Paid.',
            'payment_date': payment.payment_date.strftime('%d/%m')
        })

    flash(f'Installment marked as paid.', 'success')
    return redirect(url_for('admin_core.emi_manager'))

@admin_core_bp.route('/emi_manager/delete_plan/<int:plan_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_emi_plan(plan_id):
    plan = EMIPlan.query.get_or_404(plan_id)
    title = plan.title
    db.session.delete(plan)
    db.session.commit()
    log_user_action("Delete EMI Plan", f"Deleted EMI plan: {title}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'EMI Plan "{title}" has been deleted.', 'remove_row_id': f'plan-{plan_id}'})

    flash(f'EMI Plan "{title}" has been deleted.', 'success')
    return redirect(url_for('admin_core.emi_manager'))