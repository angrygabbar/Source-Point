from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from extensions import db, bcrypt
from models import User, JobApplication, ActivityUpdate, CodeSnippet, Project, Transaction, Order, AffiliateAd, ActivityLog, JobOpening, Feedback, CodeTestSubmission, ModeratorAssignmentHistory, Product, ProductImage, Invoice, InvoiceItem, BRD, LearningContent
from utils import role_required, log_user_action, send_email
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename
from invoice_service import InvoiceGenerator, BrdGenerator
import os
import cloudinary.uploader

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- TAX CONFIGURATION ---
GST_RATES = {
    'Electronics': 18.0,
    'Apparel': 12.0,
    'Home & Office': 12.0,
    'Books': 5.0,
    'Accessories': 12.0,
    'Other': 18.0 # Default
}

@admin_bp.route('/')
@login_required
@role_required('admin')
def admin_dashboard():
    pending_users = User.query.filter_by(is_approved=False).all()
    received_snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id).order_by(CodeSnippet.timestamp.desc()).all()
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).all()
    activities = ActivityUpdate.query.order_by(ActivityUpdate.timestamp.desc()).all()
    candidates = User.query.filter_by(role='candidate').all()
    developers = User.query.filter_by(role='developer').all()
    moderators = User.query.filter_by(role='moderator').all()
    scheduled_candidates = User.query.filter(
        User.role == 'candidate',
        User.problem_statement_id != None,
        User.moderator_id == None
    ).all()

    assigned_candidates_with_moderators = User.query.filter(
        User.role == 'candidate',
        User.moderator_id.isnot(None)
    ).all()
    moderator_ids = list(set([c.moderator_id for c in assigned_candidates_with_moderators]))
    moderators_for_assignments = User.query.filter(User.id.in_(moderator_ids)).all()
    moderators_map = {m.id: m for m in moderators_for_assignments}
    
    pending_orders_count = Order.query.filter_by(status='Order Placed').count()

    return render_template('admin_dashboard.html',
                           pending_users=pending_users,
                           received_snippets=received_snippets,
                           applications=applications, activities=activities,
                           candidates=candidates, developers=developers,
                           moderators=moderators, scheduled_candidates=scheduled_candidates,
                           assigned_candidates_with_moderators=assigned_candidates_with_moderators,
                           moderators_map=moderators_map,
                           pending_orders_count=pending_orders_count)

@admin_bp.route('/analytics')
@login_required
@role_required('admin')
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
        if status == 'pending': pending_apps = count
        elif status == 'accepted': accepted_apps = count
        elif status == 'rejected': rejected_apps = count
    
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

@admin_bp.route('/activity_logs')
@login_required
@role_required('admin')
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
    
    logs = query.order_by(ActivityLog.timestamp.desc()).all()
    return render_template('admin_activity_logs.html', logs=logs)

@admin_bp.route('/manage_users')
@login_required
@role_required('admin')
def manage_users():
    # --- Server-Side Pagination & Filtering Logic ---
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')

    query = User.query

    # Apply Search
    if search_query:
        query = query.filter(or_(
            User.username.ilike(f"%{search_query}%"),
            User.email.ilike(f"%{search_query}%")
        ))

    # Apply Filters
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if status_filter != 'all':
        is_active = True if status_filter == 'active' else False
        query = query.filter_by(is_active=is_active)

    # Apply Pagination (12 items per page for a nice grid layout)
    users_pagination = query.order_by(User.id).paginate(page=page, per_page=12, error_out=False)

    return render_template('manage_users.html', 
                           users=users_pagination, 
                           current_search=search_query,
                           current_role=role_filter,
                           current_status=status_filter)

@admin_bp.route('/create_user', methods=['POST'])
@login_required
@role_required('admin')
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([username, email, password, role]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.manage_users'))

    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        flash('Username or email already exists.', 'danger')
        return redirect(url_for('admin.manage_users'))

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    avatar_url = f'https://api.dicebear.com/8.x/initials/svg?seed={username}'

    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        role=role,
        avatar_url=avatar_url,
        is_approved=True
    )
    db.session.add(new_user)
    db.session.commit()
    log_user_action("Create User", f"Created user {username} with role {role}")
    flash(f'User {username} has been created successfully.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/toggle_user_status/<int:user_id>')
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    user_to_toggle = User.query.get_or_404(user_id)
    if user_to_toggle.id == current_user.id:
        flash('You cannot change your own status.', 'danger')
        return redirect(url_for('admin.manage_users'))

    user_to_toggle.is_active = not user_to_toggle.is_active
    db.session.commit()
    status = "activated" if user_to_toggle.is_active else "deactivated"
    
    log_user_action("Toggle User Status", f"{status.title()} user {user_to_toggle.username}")

    # Check if the request is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'User {user_to_toggle.username} has been {status}.',
            'is_active': user_to_toggle.is_active
        })

    flash(f'User {user_to_toggle.username} has been {status}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/approve_user/<int:user_id>')
@login_required
@role_required('admin')
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()

    email_sent = send_email(
        to=user.email,
        subject="Your DevConnect Hub Account is Approved!",
        template="mail/account_approved.html",
        user=user,
        now=datetime.utcnow()
    )
    log_user_action("Approve User", f"Approved user {user.username}")
    if email_sent:
        flash(f'User {user.username} has been approved and a notification has been sent.', 'success')
    else:
        flash(f'User {user.username} has been approved, but the notification email could not be sent.', 'warning')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/reject_user/<int:user_id>')
@login_required
@role_required('admin')
def reject_user(user_id):
    user_to_reject = User.query.filter_by(id=user_id, is_approved=False).first_or_404() 
    username = user_to_reject.username
    db.session.delete(user_to_reject)
    db.session.commit()
    log_user_action("Reject User", f"Rejected user registration for {username}")
    flash(f'User registration for {username} has been rejected and deleted.', 'warning')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/view_profile/<int:user_id>')
@login_required
@role_required('admin')
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user_profile.html', user=user)

@admin_bp.route('/edit_profile/<int:user_id>')
@login_required
@role_required('admin')
def edit_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('edit_user_profile.html', user=user)

@admin_bp.route('/update_user_profile/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_user_profile(user_id):
    user_to_update = User.query.get_or_404(user_id)

    user_to_update.mobile_number = request.form.get('mobile_number')
    user_to_update.primary_skill = request.form.get('primary_skill')
    user_to_update.primary_skill_experience = request.form.get('primary_skill_experience')
    user_to_update.secondary_skill = request.form.get('secondary_skill')
    user_to_update.secondary_skill_experience = request.form.get('secondary_skill_experience')

    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            if file and file.filename.endswith('.pdf'):
                try:
                    # --- CLOUDINARY LOGIC ---
                    upload_result = cloudinary.uploader.upload(
                        file, 
                        resource_type="raw", 
                        folder="resumes",
                        public_id=f"resume_{user_to_update.id}"
                    )
                    user_to_update.resume_filename = upload_result['secure_url']
                except Exception as e:
                    flash(f'Upload failed: {str(e)}', 'danger')
                    return redirect(url_for('admin.edit_user_profile', user_id=user_id))
            else:
                flash('Only PDF files are allowed for resumes.', 'danger')
                return redirect(url_for('admin.edit_user_profile', user_id=user_id))

    db.session.commit()
    log_user_action("Update User Profile", f"Admin updated profile for {user_to_update.username}")
    flash(f'{user_to_update.username}\'s profile has been updated.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/change_user_password/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_change_user_password(user_id):
    user_to_update = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('admin.edit_user_profile', user_id=user_id))

    user_to_update.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    log_user_action("Admin Change Password", f"Admin changed password for {user_to_update.username}")
    flash(f'Password for {user_to_update.username} has been updated.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/manage_ads', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_ads():
    if request.method == 'POST':
        ad_name = request.form.get('ad_name')
        affiliate_link = request.form.get('affiliate_link')

        existing_ad = AffiliateAd.query.filter_by(ad_name=ad_name).first()
        if existing_ad:
            existing_ad.affiliate_link = affiliate_link
            log_user_action("Update Ad", f"Updated ad {ad_name}")
            flash(f'Ad "{ad_name}" has been updated.', 'success')
        else:
            new_ad = AffiliateAd(ad_name=ad_name, affiliate_link=affiliate_link)
            db.session.add(new_ad)
            log_user_action("Create Ad", f"Created new ad {ad_name}")
            flash(f'New ad "{ad_name}" has been added.', 'success')
        db.session.commit()
        return redirect(url_for('admin.manage_ads'))

    ads = AffiliateAd.query.all()
    return render_template('manage_ads.html', ads=ads)

@admin_bp.route('/delete_ad/<int:ad_id>')
@login_required
@role_required('admin')
def delete_ad(ad_id):
    ad_to_delete = AffiliateAd.query.get_or_404(ad_id)
    ad_name = ad_to_delete.ad_name
    db.session.delete(ad_to_delete)
    db.session.commit()
    log_user_action("Delete Ad", f"Deleted ad {ad_name}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Ad "{ad_name}" deleted.', 'remove_row_id': f'ad-{ad_id}'})

    flash(f'Ad "{ad_name}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_ads'))

@admin_bp.route('/post_job', methods=['POST'])
@login_required
@role_required('admin')
def post_job():
    title = request.form.get('job_title')
    description = request.form.get('job_description')
    if title and description:
        new_job = JobOpening(title=title, description=description)
        db.session.add(new_job)
        db.session.commit()
        log_user_action("Post Job", f"Posted new job opening: {title}")
        flash('New job opening has been posted.', 'success')
    else:
        flash('Job title and description are required.', 'danger')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/accept_application/<int:app_id>')
@login_required
@role_required('admin')
def accept_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = 'accepted'
    db.session.commit()

    send_email(
        to=application.candidate.email,
        subject=f"Update on your application for {application.job.title}",
        template="mail/application_status_update.html",
        candidate=application.candidate,
        job=application.job,
        status="Accepted",
        now=datetime.utcnow()
    )
    
    log_user_action("Accept Application", f"Accepted application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been accepted.", 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/reject_application/<int:app_id>')
@login_required
@role_required('admin')
def reject_application(app_id):
    application = JobApplication.query.get_or_404(app_id)
    application.status = 'rejected'
    db.session.commit()

    send_email(
        to=application.candidate.email,
        subject=f"Update on your application for {application.job.title}",
        template="mail/application_status_update.html",
        candidate=application.candidate,
        job=application.job,
        status="Rejected",
        now=datetime.utcnow()
    )
    
    log_user_action("Reject Application", f"Rejected application for {application.candidate.username}")
    flash(f"Application from {application.candidate.username} for '{application.job.title}' has been rejected.", 'warning')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/add_contact_for_candidate', methods=['POST'])
@login_required
@role_required('admin')
def add_contact_for_candidate():
    candidate_id = request.form.get('candidate_id')
    developer_id = request.form.get('developer_id')
    candidate = User.query.get(candidate_id)
    developer = User.query.get(developer_id)
    if candidate and developer and developer.role == 'developer':
        candidate.allowed_contacts.append(developer)
        db.session.commit()
        log_user_action("Link Contacts", f"Linked developer {developer.username} to {candidate.username}")
        flash(f'Developer {developer.username} added to {candidate.username}\'s contacts.', 'success')
    else:
        flash('Invalid selection. Please try again.', 'danger')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/assign_moderator', methods=['POST'])
@login_required
@role_required('admin')
def assign_moderator():
    candidate_id = request.form.get('candidate_id')
    moderator_id = request.form.get('moderator_id')

    candidate = User.query.get(candidate_id)
    moderator = User.query.get(moderator_id)

    if not candidate or not moderator or moderator.role != 'moderator':
        flash("Invalid user selection.", 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    if not all([candidate.assigned_problem, candidate.test_start_time, candidate.test_end_time]):
        flash(f"Error: Candidate {candidate.username} does not have a complete test schedule. Please assign or reschedule the test from the Events page.", 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    candidate.moderator_id = moderator_id
    db.session.commit()

    history_record = ModeratorAssignmentHistory(
        candidate_id=candidate.id,
        moderator_id=moderator.id,
        problem_statement_id=candidate.problem_statement_id
    )
    db.session.add(history_record)
    db.session.commit()
    
    log_user_action("Assign Moderator", f"Assigned moderator {moderator.username} to candidate {candidate.username}")

    ist_offset = timedelta(hours=5, minutes=30)
    email_context = {
        "moderator": moderator,
        "candidate": candidate,
        "problem_title": candidate.assigned_problem.title,
        "start_time_ist": candidate.test_start_time + ist_offset,
        "end_time_ist": candidate.test_end_time + ist_offset,
        "meeting_link": candidate.meeting_link,
        "now": datetime.utcnow()
    }

    email_sent = send_email(
        to=moderator.email,
        cc=[candidate.email],
        subject=f"Moderator Assignment for {candidate.username}'s Test",
        template="mail/moderator_assigned.html",
        **email_context
    )

    if email_sent:
        flash(f'Moderator {moderator.username} has been assigned to {candidate.username}. A notification has been sent.', 'success')
    else:
        flash(f'Moderator {moderator.username} has been assigned, but the notification email could not be sent.', 'warning')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/broadcast_email', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def broadcast_email():
    if request.method == 'POST':
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')

        if not subject or not body:
            flash('Subject and body are required.', 'danger')
            return redirect(url_for('admin.broadcast_email'))

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

        users = User.query.all()
        count = 0
        for user in users:
            if user.email:
                send_email(to=user.email, subject=subject, template="mail/broadcast.html", user=user, body=final_body, attachments=attachments)
                count += 1
        
        log_user_action("Broadcast Email", f"Sent broadcast email with subject: {subject}")
        flash(f'Broadcast sent successfully to {count} users.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('broadcast_email.html')

@admin_bp.route('/send_specific_email', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def send_specific_email():
    if request.method == 'POST':
        user_ids = request.form.getlist('user_ids')
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')

        if not user_ids:
            flash('Please select at least one user.', 'danger')
            return redirect(url_for('admin.send_specific_email'))

        if not subject or not body:
            flash('Subject and body are required.', 'danger')
            return redirect(url_for('admin.send_specific_email'))

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
        
        log_user_action("Send Specific Email", f"Sent email to {count} recipients. Subject: {subject}")
        flash(f'Email has been sent to {count} users.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    users = User.query.all()
    return render_template('send_specific_email.html', users=users)

# --- INVENTORY ---
@admin_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_inventory():
    if request.method == 'POST':
        product_code = request.form.get('product_code')
        name = request.form.get('name')
        stock = request.form.get('stock')
        price = request.form.get('price')

        if Product.query.filter_by(product_code=product_code).first():
            flash(f'Product ID {product_code} already exists.', 'danger')
        else:
            new_product = Product(product_code=product_code, name=name, stock=int(stock), price=float(price))
            db.session.add(new_product)
            db.session.commit()
            log_user_action("Add Product", f"Added new product: {name}")
            flash(f'Product "{name}" added successfully.', 'success')
        return redirect(url_for('admin.manage_inventory'))
    
    products = Product.query.order_by(Product.name).all()
    total_inventory_value = sum(int(p.stock) * float(p.price) for p in products)
    total_products_count = len(products)
    low_stock_count = sum(1 for p in products if int(p.stock) < 10)

    return render_template('manage_inventory.html', products=products, total_inventory_value=total_inventory_value, total_products_count=total_products_count, low_stock_count=low_stock_count)

@admin_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_product_page():
    if request.method == 'POST':
        product_code = request.form.get('product_code')
        name = request.form.get('name')
        stock = request.form.get('stock')
        price = request.form.get('price')
        description = request.form.get('description')
        image_urls = request.form.getlist('image_urls[]')
        category = request.form.get('category')
        brand = request.form.get('brand')
        mrp = request.form.get('mrp')
        warranty = request.form.get('warranty')
        return_policy = request.form.get('return_policy')

        if Product.query.filter_by(product_code=product_code).first():
            flash(f'Product ID {product_code} already exists.', 'danger')
            return redirect(url_for('admin.add_product_page'))
        
        # Primary Image (use first one, or None)
        primary_image = image_urls[0].strip() if image_urls and image_urls[0].strip() else None
        
        new_product = Product(
            product_code=product_code,
            name=name,
            stock=int(stock),
            price=float(price),
            description=description,
            image_url=primary_image,
            category=category,
            brand=brand,
            mrp=float(mrp) if mrp else None,
            warranty=warranty,
            return_policy=return_policy
        )
        db.session.add(new_product)
        db.session.commit()
        
        # Add all images to ProductImage table
        for url in image_urls:
            if url.strip():
                img = ProductImage(product_id=new_product.id, image_url=url.strip())
                db.session.add(img)
        db.session.commit()
        
        log_user_action("Add Product", f"Added product {name} to catalog")
        flash(f'Product "{name}" added to catalog successfully.', 'success')
        return redirect(url_for('admin.manage_inventory'))
    return render_template('add_product.html')

@admin_bp.route('/inventory/update', methods=['POST'])
@login_required
@role_required('admin')
def update_product():
    product_id = request.form.get('product_id')
    product = Product.query.get_or_404(product_id)
    
    product.name = request.form.get('name')
    product.stock = int(request.form.get('stock'))
    product.price = float(request.form.get('price'))
    product.category = request.form.get('category')
    product.brand = request.form.get('brand')
    mrp = request.form.get('mrp')
    if mrp: product.mrp = float(mrp)
    product.warranty = request.form.get('warranty')
    product.return_policy = request.form.get('return_policy')
    
    # --- UPDATED IMAGE LOGIC ---
    image_urls = request.form.getlist('image_urls[]')
    
    # 1. Update Primary Image (use first valid one)
    primary_image = image_urls[0].strip() if image_urls and image_urls[0].strip() else None
    product.image_url = primary_image

    # 2. Reset ProductImage table for this product
    # Clear existing images
    ProductImage.query.filter_by(product_id=product.id).delete()
    
    # Add new list
    for url in image_urls:
        if url.strip():
            img = ProductImage(product_id=product.id, image_url=url.strip())
            db.session.add(img)

    db.session.commit()
    log_user_action("Update Product", f"Updated product {product.name}")
    flash(f'Product "{product.name}" updated.', 'success')
    return redirect(url_for('admin.manage_inventory'))

@admin_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required('admin')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    log_user_action("Delete Product", f"Deleted product {name}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Product deleted.', 'remove_row_id': f'product-{product_id}'})

    flash('Product deleted.', 'success')
    return redirect(url_for('admin.manage_inventory'))

# --- INVOICES ---
@admin_bp.route('/invoices', methods=['GET'])
@login_required
@role_required('admin')
def manage_invoices():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('manage_invoices.html', invoices=invoices)

@admin_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_invoice():
    if request.method == 'POST':
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        invoice_number = f"INV{datetime.utcnow().year}{last_invoice.id + 1 if last_invoice else 1:03d}"

        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None

        recipient_name = request.form.get('recipient_name')
        recipient_email = request.form.get('recipient_email')
        bill_to_address = request.form.get('bill_to_address')
        ship_to_address = request.form.get('ship_to_address')
        order_id = request.form.get('order_id')
        notes = request.form.get('notes')
        payment_details = request.form.get('payment_details')
        tax = float(request.form.get('tax', 0.0))

        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        item_product_ids = request.form.getlist('item_product_id[]')

        subtotal = 0
        invoice_items = []
        
        for i in range(len(item_descriptions)):
            if item_descriptions[i] and item_quantities[i] and item_prices[i]:
                quantity = int(item_quantities[i])
                price = float(item_prices[i])
                amount = quantity * price
                subtotal += amount
                
                invoice_items.append(InvoiceItem(description=item_descriptions[i], quantity=quantity, price=price))

                if i < len(item_product_ids) and item_product_ids[i]:
                    product = Product.query.get(item_product_ids[i])
                    if product:
                        product.stock -= quantity
        
        total_amount = subtotal * (1 + tax / 100)

        invoice = Invoice(
            invoice_number=invoice_number, recipient_name=recipient_name, recipient_email=recipient_email,
            bill_to_address=bill_to_address, ship_to_address=ship_to_address, order_id=order_id,
            subtotal=subtotal, tax=tax, total_amount=total_amount, due_date=due_date,
            notes=notes, payment_details=payment_details, admin_id=current_user.id
        )

        invoice.items = invoice_items
        db.session.add(invoice)
        db.session.commit()

        try:
            invoice_generator = InvoiceGenerator(invoice)
            pdf_data = invoice_generator.generate_pdf()
            attachment = {'filename': f'{invoice.invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}

            send_email(
                to=recipient_email, subject=f'Your Invoice ({invoice.invoice_number}) from Source Point',
                template='mail/professional_invoice_email.html', recipient_name=recipient_name,
                invoice_number=invoice.invoice_number, total_amount=invoice.total_amount,
                due_date=invoice.due_date.strftime('%B %d, %Y'), attachments=[attachment]
            )
        except Exception as e:
            print(f"Error generating/sending invoice: {e}")

        log_user_action("Create Invoice", f"Created invoice {invoice.invoice_number} for {recipient_name}")
        flash('Invoice created and sent successfully! Inventory updated.', 'success')
        return redirect(url_for('admin.manage_invoices'))
    
    products = Product.query.filter(Product.stock > 0).order_by(Product.name).all()
    
    # Serialize for JSON compatibility
    products_js = [
        {
            'id': p.id, 
            'name': p.name, 
            'price': p.price, 
            'code': p.product_code
        } for p in products
    ]
    return render_template('create_invoice.html', products=products_js)

@admin_bp.route('/invoices/delete/<int:invoice_id>')
@login_required
@role_required('admin')
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice_number = invoice.invoice_number
    db.session.delete(invoice)
    db.session.commit()
    log_user_action("Delete Invoice", f"Deleted invoice {invoice_number}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Invoice deleted.', 'remove_row_id': f'invoice-{invoice_id}'})

    flash(f'Invoice {invoice_number} has been deleted.', 'success')
    return redirect(url_for('admin.manage_invoices'))

@admin_bp.route('/invoices/resend', methods=['POST'])
@login_required
@role_required('admin')
def resend_invoice():
    invoice_id = request.form.get('invoice_id')
    recipient_emails_str = request.form.get('recipient_emails')

    if not invoice_id or not recipient_emails_str:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid request parameters.'})
        flash('Invalid request.', 'danger')
        return redirect(url_for('admin.manage_invoices'))

    invoice = Invoice.query.get_or_404(invoice_id)
    recipient_list = [email.strip() for email in recipient_emails_str.split(',') if email.strip()]

    invoice_generator = InvoiceGenerator(invoice)
    pdf_data = invoice_generator.generate_pdf()
    attachment = {'filename': f'{invoice.invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}

    try:
        send_email(
            to=recipient_list, subject=f'Invoice ({invoice.invoice_number}) from Source Point',
            template='mail/professional_invoice_email.html', recipient_name=invoice.recipient_name,
            invoice_number=invoice.invoice_number, total_amount=invoice.total_amount,
            due_date=invoice.due_date.strftime('%B %d, %Y'), attachments=[attachment]
        )
        message = f'Invoice {invoice.invoice_number} has been resent!'
        success = True
    except Exception as e:
        message = f'Failed to resend invoice: {str(e)}'
        success = False

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.manage_invoices'))

@admin_bp.route('/invoices/remind/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin')
def send_invoice_reminder(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice_generator = InvoiceGenerator(invoice)
    pdf_data = invoice_generator.generate_pdf()
    attachment = {'filename': f'{invoice.invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}

    email_sent = send_email(
        to=invoice.recipient_email, subject=f'Payment Reminder: Invoice {invoice.invoice_number}',
        template='mail/reminder_invoice_email.html', recipient_name=invoice.recipient_name,
        invoice_number=invoice.invoice_number, created_at=invoice.created_at.strftime('%B %d, %Y'),
        total_amount=invoice.total_amount, due_date=invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else "Immediate",
        attachments=[attachment]
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if email_sent:
            return jsonify({'success': True, 'message': f'Reminder sent to {invoice.recipient_email}.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send reminder.'})

    if email_sent: flash(f'Reminder sent to {invoice.recipient_email}.', 'success')
    else: flash('Failed to send reminder email.', 'danger')
    return redirect(url_for('admin.manage_invoices'))

@admin_bp.route('/invoices/mark_paid/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin')
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'Paid':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return jsonify({'success': False, 'message': 'Invoice is already paid.'})
        flash('This invoice is already paid.', 'warning')
        return redirect(url_for('admin.manage_invoices'))

    # Update Status
    invoice.status = 'Paid'
    db.session.commit()

    # Send Receipt Email
    email_status = "and receipt email sent"
    try:
        send_email(
            to=invoice.recipient_email,
            subject=f"Payment Receipt: Invoice {invoice.invoice_number}",
            template="mail/payment_received.html",
            invoice=invoice,
            recipient_name=invoice.recipient_name,
            total_amount=invoice.total_amount
        )
    except Exception as e:
        print(f"Email error: {e}")
        email_status = "but failed to send email"

    log_user_action("Mark Invoice Paid", f"Marked invoice {invoice.invoice_number} as paid")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Invoice marked as Paid {email_status}.'})

    flash(f'Invoice marked as Paid {email_status}.', 'success')
    return redirect(url_for('admin.manage_invoices'))

@admin_bp.route('/orders')
@login_required
@role_required('admin')
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('manage_orders.html', orders=orders)

@admin_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if not new_status:
        flash('Status is required.', 'danger')
        return redirect(url_for('admin.manage_orders'))

    old_status = order.status
    
    if old_status != new_status:
        order.status = new_status
        db.session.commit()
        log_user_action("Update Order", f"Updated order {order.order_number} to {new_status}")
        flash(f'Order {order.order_number} status updated to {new_status}.', 'success')

        try:
            send_email(
                to=order.buyer.email, subject=f'Order Update: {new_status} (Order #{order.order_number})',
                template='mail/order_status_update.html', buyer_name=order.buyer.username,
                order_number=order.order_number, status=new_status, order_date=order.created_at.strftime('%B %d, %Y'),
                total_amount=order.total_amount, shipping_address=order.shipping_address, now=datetime.utcnow()
            )
        except Exception as e:
            print(f"Failed to send status update email: {e}")

        if new_status == 'Order Accepted' and old_status != 'Order Accepted':
            existing_invoice = Invoice.query.filter_by(order_id=order.order_number).first()
            
            if not existing_invoice:
                last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
                next_id = (last_invoice.id + 1) if last_invoice else 1
                inv_num = f"INV{datetime.utcnow().year}{next_id:03d}"
                
                # --- REVISED TAX LOGIC: INCLUSIVE & CATEGORY-BASED ---
                calculated_subtotal = 0.0
                calculated_tax_amt = 0.0
                invoice_items_to_add = []

                for order_item in order.items:
                    # Find product to determine tax rate
                    product = Product.query.filter_by(name=order_item.product_name).first()
                    category = product.category if product and product.category else 'Other'
                    tax_rate_percent = GST_RATES.get(category, 18.0) # Default to 18%

                    # Logic: Price is Inclusive.
                    # Base Price = Total / (1 + TaxRate/100)
                    inclusive_total_item = order_item.price_at_purchase * order_item.quantity
                    base_total_item = inclusive_total_item / (1 + (tax_rate_percent / 100.0))
                    tax_amt_item = inclusive_total_item - base_total_item
                    
                    # Base Unit Price
                    base_unit_price = order_item.price_at_purchase / (1 + (tax_rate_percent / 100.0))

                    calculated_subtotal += base_total_item
                    calculated_tax_amt += tax_amt_item
                    
                    # Create Invoice Item with BASE unit price so sum(items) == Subtotal
                    inv_item = InvoiceItem(
                        description=order_item.product_name, 
                        quantity=order_item.quantity, 
                        price=base_unit_price, 
                        invoice_id=None # Assigned after invoice creation
                    )
                    invoice_items_to_add.append(inv_item)

                # Final total should match order total exactly (or within floating point tolerance)
                # We use order.total_amount to ensure buyer isn't charged 0.01 diff
                final_total = order.total_amount
                
                # Calculate "Effective Tax Rate" for the DB field (since it only stores one rate)
                # Rate = (Total Tax / Subtotal) * 100
                effective_tax_rate = (calculated_tax_amt / calculated_subtotal * 100) if calculated_subtotal > 0 else 0.0

                new_invoice = Invoice(
                    invoice_number=inv_num, recipient_name=order.buyer.username, recipient_email=order.buyer.email,
                    bill_to_address=order.billing_address or order.shipping_address, ship_to_address=order.shipping_address,
                    order_id=order.order_number, subtotal=calculated_subtotal, tax=effective_tax_rate, total_amount=final_total,
                    due_date=datetime.utcnow().date(), notes="Auto-generated invoice. Prices include applicable GST.", admin_id=current_user.id
                )
                db.session.add(new_invoice)
                db.session.commit() # Commit to get ID

                for inv_item in invoice_items_to_add:
                    inv_item.invoice_id = new_invoice.id
                    db.session.add(inv_item)
                db.session.commit()

                try:
                    invoice_generator = InvoiceGenerator(new_invoice)
                    pdf_data = invoice_generator.generate_pdf()
                    attachment = {'filename': f'{new_invoice.invoice_number}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}
                    send_email(
                        to=new_invoice.recipient_email, subject=f'Invoice for Order {order.order_number}',
                        template='mail/professional_invoice_email.html', recipient_name=new_invoice.recipient_name,
                        invoice_number=new_invoice.invoice_number, total_amount=new_invoice.total_amount,
                        due_date=new_invoice.due_date.strftime('%B %d, %Y'), attachments=[attachment]
                    )
                    flash('Invoice generated and sent to buyer successfully.', 'info')
                except Exception as e:
                    print(f"Failed to generate/send invoice: {e}")
                    flash('Order accepted, but failed to send invoice email.', 'warning')

    return redirect(url_for('admin.manage_orders'))

@admin_bp.route('/records')
@login_required
@role_required('admin')
def manage_records():
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    feedback = Feedback.query.order_by(Feedback.created_at.desc()).all()
    submissions = CodeTestSubmission.query.order_by(CodeTestSubmission.submitted_at.desc()).all()
    history = ModeratorAssignmentHistory.query.order_by(ModeratorAssignmentHistory.assigned_at.desc()).all()
    events = User.query.filter(User.test_completed == True).order_by(User.test_end_time.desc()).all()

    moderator_ids = [e.moderator_id for e in events if e.moderator_id]
    moderators = User.query.filter(User.id.in_(moderator_ids)).all()
    moderators_map = {m.id: m for m in moderators}

    return render_template('manage_records.html', jobs=jobs, feedback=feedback, submissions=submissions, history=history, events=events, moderators_map=moderators_map)

@admin_bp.route('/records/delete_job/<int:job_id>')
@login_required
@role_required('admin')
def delete_job_opening(job_id):
    job = JobOpening.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    log_user_action("Delete Job", f"Deleted job opening {job.title}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Job deleted.', 'remove_row_id': f'job-{job_id}'})

    flash(f'Job opening "{job.title}" deleted.', 'success')
    return redirect(url_for('admin.manage_records'))

@admin_bp.route('/records/delete_feedback/<int:feedback_id>')
@login_required
@role_required('admin')
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    log_user_action("Delete Feedback", f"Deleted feedback ID {feedback_id}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Feedback deleted.', 'remove_row_id': f'feed-{feedback_id}'})

    flash('Feedback record deleted.', 'success')
    return redirect(url_for('admin.manage_records'))

@admin_bp.route('/records/delete_submission/<int:submission_id>')
@login_required
@role_required('admin')
def delete_submission_record(submission_id):
    submission = CodeTestSubmission.query.get_or_404(submission_id)
    db.session.delete(submission)
    db.session.commit()
    log_user_action("Delete Submission", f"Deleted submission ID {submission_id}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Submission deleted.', 'remove_row_id': f'sub-{submission_id}'})

    flash('Code submission record deleted.', 'success')
    return redirect(url_for('admin.manage_records'))

@admin_bp.route('/records/delete_assignment_history/<int:history_id>')
@login_required
@role_required('admin')
def delete_assignment_history(history_id):
    history_record = ModeratorAssignmentHistory.query.get_or_404(history_id)
    db.session.delete(history_record)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'History deleted.', 'remove_row_id': f'hist-{history_id}'})

    flash('Assignment history record deleted.', 'success')
    return redirect(url_for('admin.manage_records'))

@admin_bp.route('/records/delete_coding_event/<int:user_id>')
@login_required
@role_required('admin')
def delete_coding_event(user_id):
    candidate = User.query.get_or_404(user_id)
    candidate.problem_statement_id = None
    candidate.test_start_time = None
    candidate.test_end_time = None
    candidate.test_completed = False
    candidate.moderator_id = None
    CodeTestSubmission.query.filter_by(candidate_id=user_id).delete()
    db.session.commit()
    log_user_action("Clear Event", f"Cleared event history for {candidate.username}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Event cleared.', 'remove_row_id': f'evt-{user_id}'})

    flash(f'Coding event history for {candidate.username} has been cleared.', 'success')
    return redirect(url_for('admin.manage_records'))

@admin_bp.route('/projects')
@login_required
@role_required('admin')
def projects():
    return render_template('projects_hub.html')

@admin_bp.route('/manage_projects')
@login_required
@role_required('admin')
def manage_projects():
    projects = Project.query.order_by(Project.start_date.desc()).all()
    return render_template('manage_projects.html', projects=projects)

@admin_bp.route('/create_project', methods=['GET', 'POST'])
@login_required
@role_required('admin')
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
        return redirect(url_for('admin.manage_projects'))
    return render_template('create_project.html')

@admin_bp.route('/project/<int:project_id>')
@login_required
@role_required('admin')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@admin_bp.route('/project/<int:project_id>/add_transaction', methods=['POST'])
@login_required
@role_required('admin')
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
    return redirect(url_for('admin.project_detail', project_id=project.id))

@admin_bp.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
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
        return redirect(url_for('admin.project_detail', project_id=transaction.project_id))
    return render_template('edit_transaction.html', transaction=transaction)

@admin_bp.route('/delete_transaction/<int:transaction_id>')
@login_required
@role_required('admin')
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    project_id = transaction.project_id
    db.session.delete(transaction)
    db.session.commit()
    log_user_action("Delete Transaction", f"Deleted transaction ID {transaction_id}")
    flash('Transaction deleted.', 'success')
    return redirect(url_for('admin.project_detail', project_id=project_id))

@admin_bp.route('/project/<int:project_id>/update_status', methods=['POST'])
@login_required
@role_required('admin')
def update_project_status(project_id):
    project = Project.query.get_or_404(project_id)
    new_status = request.form.get('status')
    if new_status:
        project.status = new_status
        db.session.commit()
        flash(f'Project status updated to "{new_status}".', 'success')
    return redirect(url_for('admin.project_detail', project_id=project_id))

@admin_bp.route('/project/<int:project_id>/brd')
@login_required
@role_required('admin')
def view_brd(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('brd_details.html', project=project)

@admin_bp.route('/project/<int:project_id>/brd/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
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
        return redirect(url_for('admin.view_brd', project_id=project.id))

    return render_template('edit_brd.html', project=project, brd=brd)

@admin_bp.route('/project/<int:project_id>/brd/share', methods=['POST'])
@login_required
@role_required('admin')
def share_brd(project_id):
    project = Project.query.get_or_404(project_id)
    recipient_email = request.form.get('recipient_email')

    if not recipient_email:
        flash('Recipient email is required.', 'danger')
        return redirect(url_for('admin.view_brd', project_id=project.id))

    brd_generator = BrdGenerator(project)
    pdf_data = brd_generator.generate_pdf()
    attachment = {'filename': f'BRD_{project.name}.pdf', 'content_type': 'application/pdf', 'data': pdf_data}

    send_email(
        to=recipient_email, subject=f'Business Requirement Document for {project.name}',
        template='mail/brd_shared.html', project_name=project.name, attachments=[attachment], now=datetime.utcnow()
    )
    
    log_user_action("Share BRD", f"Shared BRD for {project.name} with {recipient_email}")
    flash(f'BRD for {project.name} sent to {recipient_email}.', 'success')
    return redirect(url_for('admin.view_brd', project_id=project.id))

@admin_bp.route('/update_learning_content', methods=['POST'])
@login_required
@role_required(['admin', 'developer'])
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