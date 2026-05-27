import hashlib
import hmac
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models.newsletter import NewsArticle
from models.auth import User

newsletter_bp = Blueprint('newsletter', __name__)

# --- Secret key for generating unsubscribe tokens ---
NEWSLETTER_SECRET = os.environ.get('SECRET_KEY', 'newsletter-fallback-secret')


def generate_unsubscribe_token(user_id, email):
    """Generate a secure HMAC token for one-click unsubscribe links."""
    message = f"{user_id}:{email}".encode()
    return hmac.new(NEWSLETTER_SECRET.encode(), message, hashlib.sha256).hexdigest()[:32]


def verify_unsubscribe_token(user_id, email, token):
    """Verify the unsubscribe token matches the user."""
    expected = generate_unsubscribe_token(user_id, email)
    return hmac.compare_digest(expected, token)


@newsletter_bp.route('/news')
def news_page():
    """
    Public news page — no login required.
    Displays the latest Technology news, paginated.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10

    articles = NewsArticle.query.order_by(
        NewsArticle.published_at.desc().nullslast(),
        NewsArticle.fetched_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('news.html',
                           articles=articles.items,
                           pagination=articles,
                           page=page)


@newsletter_bp.route('/newsletter/unsubscribe')
def unsubscribe():
    """
    One-click unsubscribe from newsletter emails.
    Uses HMAC token for security — no login required.
    URL format: /newsletter/unsubscribe?uid=<user_id>&token=<hmac_token>
    """
    user_id = request.args.get('uid', type=int)
    token = request.args.get('token', '')

    if not user_id or not token:
        return render_template('newsletter_status.html',
                               status='error',
                               message='Invalid unsubscribe link.'), 400

    user = User.query.get(user_id)
    if not user:
        return render_template('newsletter_status.html',
                               status='error',
                               message='User not found.'), 404

    if not verify_unsubscribe_token(user.id, user.email, token):
        return render_template('newsletter_status.html',
                               status='error',
                               message='Invalid or expired unsubscribe link.'), 403

    if not user.newsletter_subscribed:
        return render_template('newsletter_status.html',
                               status='info',
                               message='You are already unsubscribed from the newsletter.',
                               user=user)

    user.newsletter_subscribed = False
    db.session.commit()

    return render_template('newsletter_status.html',
                           status='success',
                           message='You have been successfully unsubscribed from the SourcePoint newsletter.',
                           user=user,
                           resubscribe_url=url_for('newsletter.resubscribe',
                                                   uid=user.id,
                                                   token=generate_unsubscribe_token(user.id, user.email)))


@newsletter_bp.route('/newsletter/resubscribe')
def resubscribe():
    """
    Re-subscribe to newsletter emails (in case user changed their mind).
    Uses the same HMAC token for security.
    """
    user_id = request.args.get('uid', type=int)
    token = request.args.get('token', '')

    if not user_id or not token:
        return render_template('newsletter_status.html',
                               status='error',
                               message='Invalid link.'), 400

    user = User.query.get(user_id)
    if not user:
        return render_template('newsletter_status.html',
                               status='error',
                               message='User not found.'), 404

    if not verify_unsubscribe_token(user.id, user.email, token):
        return render_template('newsletter_status.html',
                               status='error',
                               message='Invalid or expired link.'), 403

    if user.newsletter_subscribed:
        return render_template('newsletter_status.html',
                               status='info',
                               message='You are already subscribed to the newsletter.',
                               user=user)

    user.newsletter_subscribed = True
    db.session.commit()

    return render_template('newsletter_status.html',
                           status='success',
                           message='Welcome back! You have been re-subscribed to the SourcePoint newsletter.',
                           user=user)
