"""Concrete provider adapters. Each function performs a real API call and raises on failure."""

import base64
import html as html_lib
import json
import re
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

import httpx

from app.core.security import hmac_sha256_hex, constant_time_equals
from app.integrations.registry import ProviderConfig

TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class ProviderError(Exception):
    pass


# ----------------------------------------------------------------------------- email


def send_email(cfg: ProviderConfig, to: str, subject: str, body: str, html: str | None = None) -> str:
    c, s = cfg.config, cfg.secrets
    html_body = html or _notification_email_html(subject, body)
    if cfg.provider == "brevo":
        try:
            response = httpx.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": s["api_key"], "accept": "application/json", "content-type": "application/json"},
                json={
                    "sender": {"name": c.get("from_name") or "Source Point", "email": c["from_address"]},
                    "to": [{"email": to}],
                    "subject": subject,
                    "textContent": body,
                    "htmlContent": html_body,
                },
                timeout=TIMEOUT,
            )
            if response.status_code >= 300:
                raise ProviderError(f"Brevo delivery failed: HTTP {response.status_code}")
            return str(response.json().get("messageId", ""))
        except httpx.RequestError as exc:
            raise ProviderError(f"Brevo delivery failed: {type(exc).__name__}") from exc

    msg = EmailMessage()
    msg["From"] = c.get("from_address")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    msg.add_alternative(html_body, subtype="html")
    port = int(c.get("port") or 587)
    use_tls = str(c.get("use_tls", True)).lower() in {"1", "true", "yes"}
    try:
        if port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(c["host"], port, context=ssl.create_default_context(), timeout=20)
        else:
            server = smtplib.SMTP(c["host"], port, timeout=20)
            if use_tls:
                server.starttls(context=ssl.create_default_context())
        with server:
            if c.get("username"):
                server.login(c["username"], s.get("password") or "")
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise ProviderError(f"SMTP delivery failed: {type(exc).__name__}") from exc
    return msg.get("Message-ID") or ""


def _notification_email_html(subject: str, body: str) -> str:
    safe_subject = html_lib.escape(subject)
    safe_body = html_lib.escape(body)
    safe_body = re.sub(
        r"(https?://[^\s<]+)",
        lambda match: f'<a href="{match.group(1)}" style="color:#1769aa;">{match.group(1)}</a>',
        safe_body,
    ).replace("\n", "<br>")
    return (
        "<!doctype html><html><body style=\"margin:0;background:#f3f5f8;font-family:Arial,sans-serif;color:#172033;\">"
        "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"padding:32px 12px;\"><tr><td align=\"center\">"
        "<table role=\"presentation\" width=\"600\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:600px;width:100%;background:#fff;border:1px solid #e3e8ef;border-radius:10px;overflow:hidden;\">"
        "<tr><td style=\"padding:18px 26px;background:#143c69;color:#fff;font-size:14px;font-weight:700;\">SourcePoint <span style=\"font-weight:400;opacity:.86;\">· Institute Management System</span></td></tr>"
        f"<tr><td style=\"padding:28px 26px 8px;font-size:21px;font-weight:700;\">{safe_subject}</td></tr>"
        f"<tr><td style=\"padding:12px 26px 30px;font-size:15px;line-height:1.65;color:#3c4657;\">{safe_body}</td></tr>"
        "<tr><td style=\"padding:15px 26px;border-top:1px solid #e9edf2;color:#7a8493;font-size:12px;\">This is an automated Institute Management System notification.</td></tr>"
        "</table></td></tr></table></body></html>"
    )


# ----------------------------------------------------------------------------- sms


def send_sms(cfg: ProviderConfig, to: str, body: str, template_id: str | None = None) -> str:
    if cfg.provider == "twilio":
        sid = cfg.config["account_sid"]
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data={"To": to, "From": cfg.config["from_number"], "Body": body},
            auth=(sid, cfg.secrets["auth_token"]),
            timeout=TIMEOUT,
        )
        if r.status_code >= 300:
            raise ProviderError(f"Twilio error {r.status_code}")
        return r.json().get("sid", "")
    if cfg.provider == "msg91":
        flow = template_id or cfg.config.get("flow_id")
        if not flow:
            raise ProviderError("MSG91 requires a DLT flow/template id")
        r = httpx.post(
            "https://control.msg91.com/api/v5/flow/",
            headers={"authkey": cfg.secrets["auth_key"], "content-type": "application/json"},
            json={"template_id": flow, "sender": cfg.config.get("sender_id"), "recipients": [{"mobiles": to.lstrip("+"), "message": body}]},
            timeout=TIMEOUT,
        )
        if r.status_code >= 300 or r.json().get("type") == "error":
            raise ProviderError(f"MSG91 error {r.status_code}")
        return str(r.json().get("message", ""))
    raise ProviderError(f"Unsupported SMS provider {cfg.provider}")


# ----------------------------------------------------------------------------- whatsapp


def send_whatsapp(cfg: ProviderConfig, to: str, body: str, template_name: str | None = None) -> str:
    url = f"https://graph.facebook.com/v20.0/{cfg.config['phone_number_id']}/messages"
    template = template_name or cfg.config.get("default_template")
    if template:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": cfg.config.get("template_language") or "en"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": body[:1000]}]}],
            },
        }
    else:
        payload = {"messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "text", "text": {"body": body[:4096]}}
    r = httpx.post(url, headers={"Authorization": f"Bearer {cfg.secrets['access_token']}"}, json=payload, timeout=TIMEOUT)
    if r.status_code >= 300:
        raise ProviderError(f"WhatsApp API error {r.status_code}")
    msgs = r.json().get("messages") or [{}]
    return msgs[0].get("id", "")


# ----------------------------------------------------------------------------- push


def send_push(cfg: ProviderConfig, subscription: dict[str, Any], title: str, body: str, link: str | None) -> str:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body, "url": link or "/"}),
            vapid_private_key=cfg.secrets["vapid_private_key"],
            vapid_claims={"sub": cfg.config.get("vapid_subject") or "mailto:admin@example.com"},
            timeout=15,
        )
    except WebPushException as exc:
        raise ProviderError(f"Web push failed: {exc.response.status_code if exc.response else 'error'}") from exc
    return ""


# ----------------------------------------------------------------------------- payments (Razorpay)


def razorpay_create_order(cfg: ProviderConfig, amount_paise: int, currency: str, receipt: str, notes: dict) -> dict:
    r = httpx.post(
        "https://api.razorpay.com/v1/orders",
        auth=(cfg.config["key_id"], cfg.secrets["key_secret"]),
        json={"amount": amount_paise, "currency": currency, "receipt": receipt[:40], "notes": notes},
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise ProviderError(f"Razorpay order creation failed ({r.status_code})")
    return r.json()


def razorpay_fetch_payment(cfg: ProviderConfig, payment_id: str) -> dict:
    r = httpx.get(
        f"https://api.razorpay.com/v1/payments/{payment_id}",
        auth=(cfg.config["key_id"], cfg.secrets["key_secret"]),
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise ProviderError(f"Razorpay payment lookup failed ({r.status_code})")
    return r.json()


def razorpay_verify_checkout(cfg: ProviderConfig, order_id: str, payment_id: str, signature: str) -> bool:
    expected = hmac_sha256_hex(cfg.secrets["key_secret"], f"{order_id}|{payment_id}".encode())
    return constant_time_equals(expected, signature)


def razorpay_verify_webhook(cfg: ProviderConfig, body: bytes, signature: str) -> bool:
    secret = cfg.secrets.get("webhook_secret")
    if not secret:
        return False
    return constant_time_equals(hmac_sha256_hex(secret, body), signature)


# ----------------------------------------------------------------------------- AI


def ai_complete(cfg: ProviderConfig, system: str, prompt: str, max_tokens: int = 1200) -> dict:
    base = (cfg.config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    r = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.secrets['api_key']}"},
        json={
            "model": cfg.config.get("model") or "gpt-4o-mini",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        },
        timeout=httpx.Timeout(90.0, connect=10.0),
    )
    if r.status_code >= 300:
        raise ProviderError(f"AI provider error {r.status_code}")
    data = r.json()
    usage = data.get("usage") or {}
    return {
        "text": data["choices"][0]["message"]["content"],
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "model": data.get("model"),
    }


# ----------------------------------------------------------------------------- video meetings


def zoom_create_meeting(cfg: ProviderConfig, topic: str, start: datetime, duration_minutes: int, timezone_name: str) -> dict:
    basic = base64.b64encode(f"{cfg.config['client_id']}:{cfg.secrets['client_secret']}".encode()).decode()
    tok = httpx.post(
        "https://zoom.us/oauth/token",
        params={"grant_type": "account_credentials", "account_id": cfg.config["account_id"]},
        headers={"Authorization": f"Basic {basic}"},
        timeout=TIMEOUT,
    )
    if tok.status_code >= 300:
        raise ProviderError("Zoom authentication failed")
    access = tok.json()["access_token"]
    user = cfg.config.get("host_user") or "me"
    r = httpx.post(
        f"https://api.zoom.us/v2/users/{user}/meetings",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "topic": topic[:200],
            "type": 2,
            "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": timezone_name,
            "duration": duration_minutes,
            "settings": {"join_before_host": False, "waiting_room": True},
        },
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise ProviderError(f"Zoom meeting creation failed ({r.status_code})")
    d = r.json()
    return {"external_id": str(d.get("id")), "join_url": d.get("join_url"), "host_url": d.get("start_url"), "raw": {"id": d.get("id")}}


def google_meet_create(cfg: ProviderConfig, topic: str, start: datetime, duration_minutes: int, timezone_name: str) -> dict:
    tok = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": cfg.config["client_id"],
            "client_secret": cfg.secrets["client_secret"],
            "refresh_token": cfg.secrets["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    if tok.status_code >= 300:
        raise ProviderError("Google authentication failed")
    access = tok.json()["access_token"]
    cal = cfg.config.get("calendar_id") or "primary"
    end = start + timedelta(minutes=duration_minutes)
    r = httpx.post(
        f"https://www.googleapis.com/calendar/v3/calendars/{cal}/events",
        params={"conferenceDataVersion": 1},
        headers={"Authorization": f"Bearer {access}"},
        json={
            "summary": topic[:200],
            "start": {"dateTime": start.isoformat(), "timeZone": timezone_name},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone_name},
            "conferenceData": {"createRequest": {"requestId": f"cf-{int(start.timestamp())}-{abs(hash(topic)) % 10**8}"}},
        },
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise ProviderError(f"Google Calendar error ({r.status_code})")
    d = r.json()
    return {"external_id": d.get("id"), "join_url": d.get("hangoutLink"), "host_url": d.get("htmlLink"), "raw": {"id": d.get("id")}}
