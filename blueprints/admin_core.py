import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.auth import User, ActivityLog
from models.hiring import JobApplication, CodeSnippet
from models.commerce import Order, StockRequest
from models.finance import Project, Transaction, BRD, EMIPlan, EMIPayment
from models.learning import LearningContent
from utils import role_required, log_user_action, send_email
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


@admin_core_bp.route('/health-check')
@login_required
@role_required(UserRole.ADMIN.value)
def health_check_page():
    """Live server health check dashboard — collects all metrics and renders UI."""
    import psutil
    import platform
    import socket
    import requests as http_requests

    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    report_time = ist_now.strftime('%d %b %Y, %I:%M %p IST')
    checks = {}
    overall_status = 'HEALTHY'
    alerts = []

    # 1. SYSTEM INFO
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.utcnow() - boot_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
        checks['system'] = {
            'status': 'OK', 'hostname': socket.gethostname(),
            'platform': f"{platform.system()} {platform.release()}",
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'uptime': uptime_str,
            'boot_time': boot_time.strftime('%b %d, %Y %I:%M %p'),
        }
    except Exception as e:
        checks['system'] = {'status': 'ERROR', 'error': str(e)}

    # 2. CPU
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)
        load_avg = psutil.getloadavg()
        cpu_status = 'CRITICAL' if cpu_percent > 90 else ('WARNING' if cpu_percent > 75 else 'OK')
        if cpu_status == 'CRITICAL':
            overall_status = 'CRITICAL'
            alerts.append(f"CPU usage critically high: {cpu_percent}%")
        elif cpu_status == 'WARNING':
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
            alerts.append(f"CPU usage high: {cpu_percent}%")
        # Per-core usage
        per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        checks['cpu'] = {
            'status': cpu_status, 'usage_percent': cpu_percent,
            'cores_physical': cpu_count, 'cores_logical': cpu_count_logical,
            'load_avg_1m': f"{load_avg[0]:.2f}", 'load_avg_5m': f"{load_avg[1]:.2f}",
            'load_avg_15m': f"{load_avg[2]:.2f}", 'per_cpu': per_cpu,
        }
    except Exception as e:
        checks['cpu'] = {'status': 'ERROR', 'error': str(e)}
        alerts.append(f"CPU check failed: {e}")

    # 3. MEMORY
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        mem_status = 'CRITICAL' if mem.percent > 90 else ('WARNING' if mem.percent > 80 else 'OK')
        if mem_status == 'CRITICAL':
            overall_status = 'CRITICAL'
            alerts.append(f"Memory critically high: {mem.percent}%")
        elif mem_status == 'WARNING':
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
            alerts.append(f"Memory usage high: {mem.percent}%")
        checks['memory'] = {
            'status': mem_status, 'total_gb': f"{mem.total / (1024**3):.1f}",
            'used_gb': f"{mem.used / (1024**3):.1f}", 'available_gb': f"{mem.available / (1024**3):.1f}",
            'usage_percent': mem.percent,
            'swap_total_gb': f"{swap.total / (1024**3):.1f}",
            'swap_used_gb': f"{swap.used / (1024**3):.1f}", 'swap_percent': swap.percent,
        }
    except Exception as e:
        checks['memory'] = {'status': 'ERROR', 'error': str(e)}

    # 4. DISK
    try:
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        disk_status = 'CRITICAL' if disk.percent > 90 else ('WARNING' if disk.percent > 80 else 'OK')
        if disk_status == 'CRITICAL':
            overall_status = 'CRITICAL'
            alerts.append(f"Disk usage critically high: {disk.percent}%")
        elif disk_status == 'WARNING':
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
            alerts.append(f"Disk usage high: {disk.percent}%")
        checks['disk'] = {
            'status': disk_status, 'total_gb': f"{disk.total / (1024**3):.1f}",
            'used_gb': f"{disk.used / (1024**3):.1f}", 'free_gb': f"{disk.free / (1024**3):.1f}",
            'usage_percent': disk.percent,
            'read_gb': f"{disk_io.read_bytes / (1024**3):.2f}" if disk_io else 'N/A',
            'write_gb': f"{disk_io.write_bytes / (1024**3):.2f}" if disk_io else 'N/A',
        }
    except Exception as e:
        checks['disk'] = {'status': 'ERROR', 'error': str(e)}

    # 5. DATABASE
    try:
        start = datetime.utcnow()
        db.session.execute(db.text('SELECT 1'))
        db_latency = (datetime.utcnow() - start).total_seconds() * 1000
        user_count = db.session.execute(db.text('SELECT COUNT(*) FROM "user"')).scalar()
        article_count = db.session.execute(db.text("SELECT COUNT(*) FROM news_article")).scalar()
        try:
            db_size = db.session.execute(db.text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
        except Exception:
            db_size = 'N/A'
        try:
            active_conn = db.session.execute(db.text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")).scalar()
        except Exception:
            active_conn = 'N/A'
        db_status = 'WARNING' if db_latency > 500 else 'OK'
        if db_status == 'WARNING':
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
            alerts.append(f"Database latency high: {db_latency:.0f}ms")
        checks['database'] = {
            'status': db_status, 'latency_ms': f"{db_latency:.1f}",
            'database_size': db_size, 'active_connections': active_conn,
            'total_users': user_count, 'total_articles': article_count,
        }
    except Exception as e:
        checks['database'] = {'status': 'CRITICAL', 'error': str(e)}
        overall_status = 'CRITICAL'
        alerts.append(f"Database connection failed: {e}")

    # 6. REDIS
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
        r = redis.from_url(redis_url, socket_timeout=5)
        start = datetime.utcnow()
        r.ping()
        redis_latency = (datetime.utcnow() - start).total_seconds() * 1000
        info = r.info()
        checks['redis'] = {
            'status': 'OK', 'latency_ms': f"{redis_latency:.1f}",
            'memory_used': info.get('used_memory_human', 'N/A'),
            'connected_clients': info.get('connected_clients', 'N/A'),
            'total_keys': r.dbsize(), 'uptime_days': info.get('uptime_in_days', 'N/A'),
            'redis_version': info.get('redis_version', 'N/A'),
        }
    except Exception as e:
        checks['redis'] = {'status': 'CRITICAL', 'error': str(e)}
        overall_status = 'CRITICAL'
        alerts.append(f"Redis connection failed: {e}")

    # 7. APPLICATION
    try:
        site_url = os.environ.get('SITE_URL', 'http://web:5000')
        start = datetime.utcnow()
        resp = http_requests.get(f"{site_url}/health", timeout=10)
        app_latency = (datetime.utcnow() - start).total_seconds() * 1000
        app_status = 'OK'
        if resp.status_code != 200:
            app_status = 'CRITICAL'
            overall_status = 'CRITICAL'
            alerts.append(f"App /health returned HTTP {resp.status_code}")
        elif app_latency > 2000:
            app_status = 'WARNING'
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
        checks['application'] = {
            'status': app_status, 'http_status': resp.status_code,
            'response_time_ms': f"{app_latency:.0f}",
        }
    except Exception as e:
        checks['application'] = {'status': 'CRITICAL', 'error': str(e)}
        overall_status = 'CRITICAL'
        alerts.append(f"App health check failed: {e}")

    # 8. NETWORK
    try:
        net = psutil.net_io_counters()
        net_connections = len(psutil.net_connections(kind='inet'))
        checks['network'] = {
            'status': 'OK',
            'bytes_sent_gb': f"{net.bytes_sent / (1024**3):.2f}",
            'bytes_recv_gb': f"{net.bytes_recv / (1024**3):.2f}",
            'packets_sent': f"{net.packets_sent:,}",
            'packets_recv': f"{net.packets_recv:,}",
            'errors_in': net.errin, 'errors_out': net.errout,
            'active_connections': net_connections,
        }
        if net.errin > 100 or net.errout > 100:
            checks['network']['status'] = 'WARNING'
            if overall_status == 'HEALTHY': overall_status = 'WARNING'
            alerts.append(f"Network errors: {net.errin} in, {net.errout} out")
    except Exception as e:
        checks['network'] = {'status': 'ERROR', 'error': str(e)}

    # 9. TOP PROCESSES
    try:
        processes = []
        for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                          key=lambda p: p.info.get('cpu_percent', 0) or 0, reverse=True)[:8]:
            processes.append({
                'pid': proc.info['pid'], 'name': proc.info['name'],
                'cpu': proc.info.get('cpu_percent', 0) or 0,
                'memory': proc.info.get('memory_percent', 0) or 0,
            })
        checks['top_processes'] = processes
    except Exception:
        checks['top_processes'] = []

    return render_template('admin_health_check.html',
                           checks=checks, overall_status=overall_status,
                           alerts=alerts, report_time=report_time)


@admin_core_bp.route('/run-health-check', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def run_health_check():
    """Manually trigger a server health check email. Runs async."""
    from worker import server_health_check_task
    server_health_check_task.delay()
    flash('🩺 Health check report will be emailed to you shortly.', 'success')
    return redirect(url_for('admin_core.health_check_page'))

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
        # IDs the admin chose to EXCLUDE from this broadcast
        excluded_ids = set(request.form.getlist('excluded_ids'))

        if not subject or not body:
            flash('Subject and body are required.', 'danger')
            return redirect(url_for('admin_core.broadcast_email'))

        attachments = []
        if file and file.filename != '':
            file_data = file.read()
            ct = getattr(file, 'mimetype', None) or 'application/octet-stream'
            attachments.append({
                'filename': secure_filename(file.filename),
                'content_type': ct,
                'data': file_data
            })

        all_users = User.query.filter_by(is_active=True).order_by(User.username).all()
        # Send to every active user EXCEPT those explicitly excluded
        bcc_recipients = [
            u.email for u in all_users
            if u.email and str(u.id) not in excluded_ids
        ]

        to_email = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'admin@sourcepoint.in')
        if to_email in bcc_recipients:
            bcc_recipients.remove(to_email)

        if bcc_recipients or to_email:
            send_email(
                to=to_email,
                bcc=bcc_recipients,
                subject=subject,
                template="mail/broadcast.html",
                user=current_user,
                body=body,
                attachments=attachments
            )
            count = len(bcc_recipients)
            skipped = len(excluded_ids)
            log_user_action("Broadcast Email", f"Sent broadcast to {count} users, skipped {skipped}")
            flash(f'Broadcast sent to {count} users ({skipped} excluded).', 'success')
        else:
            flash('No recipients after exclusions.', 'warning')

        return redirect(url_for('admin_core.admin_dashboard'))

    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template('broadcast_email.html', users=users)

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
            ct = getattr(file, 'mimetype', None) or 'application/octet-stream'
            attachments.append({
                'filename': secure_filename(file.filename),
                'content_type': ct,
                'data': file_data
            })

        users = User.query.filter(User.id.in_(user_ids)).all()
        count = 0
        for user in users:
            if user.email:
                # mail/broadcast.html needs: recipient, subject, message|safe
                send_email(
                    to=user.email,
                    subject=subject,
                    template="mail/broadcast.html",
                    recipient=user,
                    message=body,
                    attachments=attachments
                )
                count += 1

        log_user_action("Send Specific Email", f"Sent email to {count} recipients.")
        flash(f'Email sent to {count} user(s) successfully.', 'success')
        return redirect(url_for('admin_core.admin_dashboard'))

    users = User.query.order_by(User.username).all()
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
        log_user_action("Update Project Status", f"Changed project {project.name} to {new_status}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Status updated to {new_status}.', 'new_status': new_status})
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
        # Save Content
        brd.executive_summary = request.form.get('executive_summary')
        brd.project_objectives = request.form.get('project_objectives')
        brd.project_scope = request.form.get('project_scope')
        brd.business_requirements = request.form.get('business_requirements')
        brd.key_stakeholders = request.form.get('key_stakeholders')
        brd.project_constraints = request.form.get('project_constraints')
        brd.cost_benefit_analysis = request.form.get('cost_benefit_analysis')

        # Save Labels
        brd.executive_summary_label = request.form.get('executive_summary_label')
        brd.project_objectives_label = request.form.get('project_objectives_label')
        brd.project_scope_label = request.form.get('project_scope_label')
        brd.business_requirements_label = request.form.get('business_requirements_label')
        brd.key_stakeholders_label = request.form.get('key_stakeholders_label')
        brd.project_constraints_label = request.form.get('project_constraints_label')
        brd.cost_benefit_analysis_label = request.form.get('cost_benefit_analysis_label')

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
                        payments_to_add.append({'due_date': due_date, 'amount': amount, 'description': description})
                except Exception: continue
        
        elif filename.endswith('.pdf'):
            try:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages: text += page.extract_text() + "\n"
                
                lines = text.split('\n')
                date_pattern_num = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')
                date_pattern_text = re.compile(r'\b(\d{1,2})[\s/-]*([A-Za-z]{3})[\s/-]*(\d{4})\b')
                fee_pattern = re.compile(r'Processing\s*Fee\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.?\d*)', re.IGNORECASE)

                for line in lines:
                    line = line.strip()
                    if not line or 'txn date' in line.lower() or 'transaction date' in line.lower(): continue
                    fee_match = fee_pattern.search(line)
                    if fee_match:
                        try:
                            processing_fee += float(fee_match.group(1).replace(',', ''))
                        except ValueError: pass
                        continue
                    
                    due_date = None
                    end_idx = 0
                    text_match = date_pattern_text.search(line)
                    if text_match:
                        try:
                            d, m, y = text_match.groups()
                            due_date = datetime.strptime(f"{d}-{m}-{y}", '%d-%b-%Y').date()
                            end_idx = text_match.end()
                        except ValueError: pass
                    
                    if not due_date:
                        num_match = date_pattern_num.search(line)
                        if num_match:
                            try:
                                d, m, y = num_match.groups()
                                if len(y) == 2: y = "20" + y
                                due_date = datetime(int(y), int(m), int(d)).date()
                                end_idx = num_match.end()
                            except ValueError: pass
                    
                    if due_date:
                        rem = line[end_idx:]
                        amts = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', rem)
                        if amts:
                            try:
                                a = float(amts[0].replace(',', ''))
                                if a > 0:
                                    payments_to_add.append({'due_date': due_date, 'amount': a, 'description': f'Installment for {title}'})
                                    total_amount += a
                            except ValueError: continue
            except Exception:
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

        for i, pay in enumerate(payments_to_add, start=1):
            payment = EMIPayment(plan_id=new_plan.id, installment_number=i, due_date=pay['due_date'], amount=pay['amount'], description=pay['description'], reminder_days_before=reminder_days)
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
    payment = EMIPayment.query.get_or_404(payment_id)
    if request.form.get('amount'): payment.amount = float(request.form.get('amount'))
    if request.form.get('due_date'): payment.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
    if request.form.get('description'): payment.description = request.form.get('description')
    status = request.form.get('status')
    if status:
        payment.status = status
        if status == 'Pending': payment.payment_date = None
        elif status == 'Paid' and not payment.payment_date: payment.payment_date = datetime.utcnow()
    
    db.session.commit()
    flash('Payment details updated successfully.', 'success')
    return redirect(url_for('admin_core.emi_manager'))

@admin_core_bp.route('/emi_manager/mark_paid/<int:payment_id>', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def mark_emi_paid(payment_id):
    payment = EMIPayment.query.get_or_404(payment_id)
    if payment.status == 'Paid':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': False, 'message': 'Already paid.'})
        return redirect(url_for('admin_core.emi_manager'))

    payment.status = 'Paid'
    payment.payment_date = datetime.utcnow()
    db.session.commit()
    
    try:
        send_email(to=payment.plan.lender.email, subject=f"Payment Received: {payment.description}", template="mail/emi_paid_notification_lender.html", lender=payment.plan.lender, borrower=payment.plan.borrower, payment=payment, paid_date=datetime.utcnow())
    except Exception: pass
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Marked as Paid.', 'payment_date': payment.payment_date.strftime('%d/%m')})
    return redirect(url_for('admin_core.emi_manager'))

@admin_core_bp.route('/emi_manager/delete_plan/<int:plan_id>')
@login_required
@role_required(UserRole.ADMIN.value)
def delete_emi_plan(plan_id):
    plan = EMIPlan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'message': 'Plan deleted.', 'remove_row_id': f'plan-{plan_id}'})
    return redirect(url_for('admin_core.emi_manager'))

# =========================================================
# NEWSLETTER MANAGEMENT
# =========================================================

@admin_core_bp.route('/newsletter', methods=['GET'])
@login_required
@role_required(UserRole.ADMIN.value)
def admin_newsletter():
    from models.newsletter import NewsArticle
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'newest')

    query = NewsArticle.query

    if search:
        query = query.filter(
            db.or_(
                NewsArticle.title.ilike(f"%{search}%"),
                NewsArticle.source_name.ilike(f"%{search}%")
            )
        )

    if status_filter == 'unsent':
        query = query.filter_by(is_sent=False)
    elif status_filter == 'sent':
        query = query.filter_by(is_sent=True)

    if sort_by == 'oldest':
        query = query.order_by(NewsArticle.published_at.asc().nullslast())
    elif sort_by == 'source':
        query = query.order_by(NewsArticle.source_name.asc().nullslast())
    elif sort_by == 'title':
        query = query.order_by(NewsArticle.title.asc())
    else: # newest
        query = query.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())

    articles_pagination = query.paginate(page=page, per_page=20, error_out=False)

    # Stats
    total_articles = NewsArticle.query.count()
    unsent_count = NewsArticle.query.filter_by(is_sent=False).count()
    
    total_users = User.query.filter(User.email.isnot(None), User.email != '').count()
    subscribed_users = User.query.filter(User.email.isnot(None), User.email != '', User.newsletter_subscribed == True).count()
    
    # Last sent
    last_sent_article = NewsArticle.query.filter_by(is_sent=True).order_by(NewsArticle.fetched_at.desc()).first()
    last_sent_date = last_sent_article.fetched_at if last_sent_article else None

    return render_template(
        'admin_newsletter.html',
        articles=articles_pagination,
        total_articles=total_articles,
        unsent_count=unsent_count,
        total_users=total_users,
        subscribed_users=subscribed_users,
        last_sent_date=last_sent_date,
        current_search=search,
        current_status=status_filter,
        current_sort=sort_by
    )

@admin_core_bp.route('/newsletter/send', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN.value)
def send_manual_newsletter():
    try:
        data = request.get_json()
        article_ids = data.get('article_ids', [])
        
        if not article_ids:
            return jsonify({'success': False, 'message': 'No articles selected.'}), 400
            
        from worker import send_manual_newsletter_task
        
        # Dispatch to Celery
        send_manual_newsletter_task.delay(article_ids)
        
        log_user_action("Send Manual Newsletter", f"Triggered send for {len(article_ids)} articles.")
        
        return jsonify({
            'success': True, 
            'message': f'Newsletter task dispatched successfully for {len(article_ids)} articles. They will be marked as sent once emails are dispatched.'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error dispatching task: {str(e)}'}), 500