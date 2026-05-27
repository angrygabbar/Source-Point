import hashlib
import hmac
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from extensions import db
from models.newsletter import NewsArticle
from models.auth import User
from sqlalchemy import func

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


def _time_ago(dt):
    """Convert a datetime to a human-readable relative string."""
    if not dt:
        return ''
    now = datetime.utcnow()
    diff = now - dt

    seconds = int(diff.total_seconds())
    if seconds < 0:
        return 'Just now'
    if seconds < 60:
        return 'Just now'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes}m ago'
    hours = minutes // 60
    if hours < 24:
        return f'{hours}h ago'
    days = hours // 24
    if days == 1:
        return 'Yesterday'
    if days < 7:
        return f'{days}d ago'
    weeks = days // 7
    if weeks < 5:
        return f'{weeks}w ago'
    return dt.strftime('%b %d, %Y')


@newsletter_bp.route('/news')
def news_page():
    """
    Public news page — no login required.
    Displays the latest Technology news with search, stats, and smart features.
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str).strip()
    per_page = 12

    query = NewsArticle.query

    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                NewsArticle.title.ilike(search_filter),
                NewsArticle.summary.ilike(search_filter),
                NewsArticle.source_name.ilike(search_filter)
            )
        )

    articles = query.order_by(
        NewsArticle.published_at.desc().nullslast(),
        NewsArticle.fetched_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    # Stats
    total_articles = NewsArticle.query.count()
    sources_count = db.session.query(func.count(func.distinct(NewsArticle.source_name))).scalar() or 0
    latest_fetch = db.session.query(func.max(NewsArticle.fetched_at)).scalar()
    last_updated_ago = _time_ago(latest_fetch) if latest_fetch else None

    now = datetime.utcnow()
    for article in articles.items:
        ref_time = article.published_at or article.fetched_at
        article.time_ago = _time_ago(ref_time)
        article.is_new = (now - (article.fetched_at or now)).total_seconds() < 10800

    return render_template('news.html',
                           articles=articles.items,
                           pagination=articles,
                           page=page,
                           search=search,
                           total_articles=total_articles,
                           sources_count=sources_count,
                           last_updated_ago=last_updated_ago)


@newsletter_bp.route('/news/<int:article_id>')
def article_detail(article_id):
    """
    Internal article detail page — displays full scraped content.
    Falls back to summary + external link if content wasn't scraped.
    """
    article = NewsArticle.query.get_or_404(article_id)

    # Relative time
    ref_time = article.published_at or article.fetched_at
    article.time_ago = _time_ago(ref_time)

    # Related articles: same source or latest articles, excluding current
    related = []
    if article.source_name:
        related = NewsArticle.query.filter(
            NewsArticle.id != article.id,
            NewsArticle.source_name == article.source_name
        ).order_by(NewsArticle.published_at.desc().nullslast()).limit(4).all()

    # If not enough from same source, fill with latest
    if len(related) < 4:
        remaining = 4 - len(related)
        exclude_ids = [article.id] + [r.id for r in related]
        more = NewsArticle.query.filter(
            NewsArticle.id.notin_(exclude_ids)
        ).order_by(NewsArticle.published_at.desc().nullslast()).limit(remaining).all()
        related.extend(more)

    for r in related:
        r.time_ago = _time_ago(r.published_at or r.fetched_at)

    return render_template('news_article.html',
                           article=article,
                           related=related)


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
