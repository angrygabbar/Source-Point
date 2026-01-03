from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.auth import ActivityUpdate
from models.hiring import CodeSnippet
from utils import role_required, log_user_action
from enums import UserRole # --- IMPORT ENUM ---

developer_bp = Blueprint('developer', __name__)

@developer_bp.route('/developer', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.DEVELOPER.value) # --- USE ENUM ---
def developer_dashboard():
    if request.method == 'POST':
        content = request.form.get('activity_content')
        if content:
            new_activity = ActivityUpdate(content=content, author=current_user)
            db.session.add(new_activity)
            db.session.commit()
            log_user_action("Post Activity", "Posted developer activity update")
            flash('Activity posted!', 'success')
        return redirect(url_for('developer.developer_dashboard'))
    
    activities = ActivityUpdate.query.order_by(ActivityUpdate.timestamp.desc()).all()
    received_snippets = CodeSnippet.query.filter_by(recipient_id=current_user.id).order_by(CodeSnippet.timestamp.desc()).all()
    
    return render_template('developer_dashboard.html', activities=activities, received_snippets=received_snippets)