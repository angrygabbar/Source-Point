from datetime import datetime

from bs4 import BeautifulSoup
from extensions import db
from enums import RollbackTermsDecision
from models.commerce import InventoryRollbackTerms, InventoryRollbackTermsDecision


DEFAULT_ROLLBACK_TERMS_TITLE = "Inventory Rollback Terms and Conditions"
DEFAULT_ROLLBACK_TERMS_CONTENT = """<h2>Inventory Rollback Terms</h2>
<ol>
  <li>Rollback requests are only for inventory that is currently assigned to your seller account.</li>
  <li>The requested rollback quantity cannot exceed your available seller inventory.</li>
  <li>Submitting a rollback request does not immediately change stock. Inventory moves back to master stock only after admin approval.</li>
  <li>You must provide accurate product and quantity details. Incorrect requests may be rejected by the admin team.</li>
  <li>Approved rollback quantities will be deducted from your seller inventory and added back to master inventory.</li>
  <li>Rejected requests will not change your seller inventory.</li>
  <li>Admin notes and decisions are final for each submitted rollback request.</li>
  <li>You are responsible for reviewing the latest terms before using the rollback feature.</li>
</ol>"""


ALLOWED_TERMS_TAGS = {
    'a', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'li', 'ol', 'p', 'pre', 's', 'span', 'strong', 'table', 'tbody', 'td', 'th',
    'thead', 'tr', 'u', 'ul'
}
ALLOWED_TERMS_ATTRS = {
    'a': {'href', 'rel', 'target', 'title'},
    'td': {'colspan', 'rowspan', 'style'},
    'th': {'colspan', 'rowspan', 'style'},
    'span': {'style'},
    'p': {'style'},
    'div': {'style'},
    'table': {'style'},
}
BLOCKED_TERMS_TAGS = {'script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button'}


class RollbackTermsService:
    @staticmethod
    def ensure_active_terms(created_by_id=None):
        active_terms = InventoryRollbackTerms.query.filter_by(is_active=True)\
            .order_by(InventoryRollbackTerms.version.desc(), InventoryRollbackTerms.id.desc())\
            .first()
        if active_terms:
            return active_terms

        latest_terms = InventoryRollbackTerms.query\
            .order_by(InventoryRollbackTerms.version.desc(), InventoryRollbackTerms.id.desc())\
            .first()
        next_version = (latest_terms.version + 1) if latest_terms else 1
        active_terms = InventoryRollbackTerms(
            version=next_version,
            title=DEFAULT_ROLLBACK_TERMS_TITLE,
            content=DEFAULT_ROLLBACK_TERMS_CONTENT,
            is_active=True,
            created_by_id=created_by_id,
        )
        db.session.add(active_terms)
        db.session.commit()
        return active_terms

    @staticmethod
    def publish_new_terms(title, content, admin_id):
        InventoryRollbackTerms.query.filter_by(is_active=True).update({'is_active': False})

        latest_terms = InventoryRollbackTerms.query\
            .order_by(InventoryRollbackTerms.version.desc(), InventoryRollbackTerms.id.desc())\
            .first()
        next_version = (latest_terms.version + 1) if latest_terms else 1

        terms = InventoryRollbackTerms(
            version=next_version,
            title=title.strip() or DEFAULT_ROLLBACK_TERMS_TITLE,
            content=RollbackTermsService.sanitize_terms_content(content),
            is_active=True,
            created_by_id=admin_id,
        )
        db.session.add(terms)
        db.session.commit()
        return terms

    @staticmethod
    def get_seller_decision(seller_id, terms_id):
        return InventoryRollbackTermsDecision.query.filter_by(
            seller_id=seller_id,
            terms_id=terms_id
        ).first()

    @staticmethod
    def seller_has_accepted_current_terms(seller_id):
        active_terms = RollbackTermsService.ensure_active_terms()
        decision = RollbackTermsService.get_seller_decision(seller_id, active_terms.id)
        return bool(decision and decision.decision == RollbackTermsDecision.ACCEPTED.value)

    @staticmethod
    def record_seller_decision(seller_id, terms_id, decision, request_obj=None):
        existing_decision = RollbackTermsService.get_seller_decision(seller_id, terms_id)
        if not existing_decision:
            existing_decision = InventoryRollbackTermsDecision(
                seller_id=seller_id,
                terms_id=terms_id,
            )
            db.session.add(existing_decision)

        existing_decision.decision = decision
        existing_decision.decided_at = datetime.utcnow()

        if request_obj:
            forwarded_for = request_obj.headers.get('X-Forwarded-For', '')
            remote_addr = forwarded_for.split(',')[0].strip() if forwarded_for else request_obj.remote_addr
            existing_decision.ip_address = (remote_addr or '')[:50] or None
            existing_decision.user_agent = (request_obj.headers.get('User-Agent') or '')[:255] or None

        db.session.commit()
        return existing_decision

    @staticmethod
    def content_looks_like_html(content):
        return bool(content and '<' in content and '>' in content)

    @staticmethod
    def sanitize_terms_content(content):
        content = (content or '').strip()
        if not content:
            return ''

        if not RollbackTermsService.content_looks_like_html(content):
            return RollbackTermsService.plain_text_to_html(content)

        soup = BeautifulSoup(content, 'html.parser')
        for tag in list(soup.find_all(True)):
            tag_name = tag.name.lower()
            if tag_name in BLOCKED_TERMS_TAGS:
                tag.decompose()
                continue

            if tag_name not in ALLOWED_TERMS_TAGS:
                tag.unwrap()
                continue

            allowed_attrs = ALLOWED_TERMS_ATTRS.get(tag_name, set())
            for attr in list(tag.attrs):
                if attr.lower().startswith('on') or attr not in allowed_attrs:
                    del tag.attrs[attr]
                    continue

                if attr == 'style':
                    style_value = str(tag.attrs.get(attr) or '')
                    lowered_style = style_value.lower()
                    if any(blocked in lowered_style for blocked in ('javascript:', 'expression(', 'url(')):
                        del tag.attrs[attr]
                    else:
                        tag.attrs[attr] = style_value[:500]

            if tag_name == 'a':
                href = (tag.attrs.get('href') or '').strip()
                if href and not href.startswith(('http://', 'https://', 'mailto:', '#')):
                    del tag.attrs['href']
                if tag.attrs.get('href'):
                    tag.attrs['target'] = '_blank'
                    tag.attrs['rel'] = 'noopener noreferrer'

        if soup.body:
            return ''.join(str(child) for child in soup.body.contents).strip()
        return str(soup).strip()

    @staticmethod
    def plain_text_to_html(content):
        soup = BeautifulSoup('', 'html.parser')
        for line in (content or '').splitlines():
            clean_line = line.strip()
            if not clean_line:
                continue
            paragraph = soup.new_tag('p')
            paragraph.string = clean_line
            soup.append(paragraph)
        return str(soup)

    @staticmethod
    def render_terms_content(content):
        return RollbackTermsService.sanitize_terms_content(content)
