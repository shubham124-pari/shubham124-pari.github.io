"""
Sends real emails (password reset link).

Two paths, tried in order:
1. Brevo HTTPS API (recommended) — works everywhere, including hosts that
   block outbound SMTP ports (Render free tier does this since Sept 2025).
   Uses only urllib (stdlib) — no `sib-api-v3-sdk` pip package needed,
   matching the same minimal-dependency approach already used for
   Gemini/OpenAI in services/ai_provider.py.
2. Plain SMTP — kept as a fallback for local development where port
   blocks don't apply.

If neither is configured, the email is printed to the server console
instead — so local dev/testing still work without any mailbox at all.
"""

import json
import logging
import smtplib
import ssl
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config

logger = logging.getLogger("portfolio")

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def _send_via_brevo(to_email: str, subject: str, html_body: str) -> bool:
    payload = {
        "sender": {"name": Config.BREVO_SENDER_NAME, "email": Config.BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }
    req = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": Config.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="ignore")
        logger.error("[email] Brevo send failed (%s): %s", err.code, detail[:300])
        return False
    except urllib.error.URLError as err:
        logger.error("[email] Could not reach Brevo: %s", err.reason)
        return False


def _send_via_smtp(to_email: str, subject: str, html_body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM or Config.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
            server.starttls(context=context)
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True
    except Exception as err:  # pragma: no cover
        logger.exception("[email] SMTP send failed to %s: %s", to_email, err)
        return False


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    if Config.BREVO_API_KEY and Config.BREVO_SENDER_EMAIL:
        return _send_via_brevo(to_email, subject, html_body)

    if Config.SMTP_USER and Config.SMTP_PASSWORD:
        return _send_via_smtp(to_email, subject, html_body)

    logger.info(
        "[email] No email provider configured — skipping real send. To: %s | Subject: %s",
        to_email, subject,
    )
    logger.debug("[email] Body: %s", html_body)
    return False


def send_reset_email(to_email: str, name: str, reset_link: str) -> bool:
    subject = "Reset your password — Shubham Kumar Portfolio"
    body = f"""
    <div style="font-family:sans-serif;background:#0b0f1a;color:#fff;padding:24px;border-radius:12px;">
        <h2 style="color:#00ff80;">Reset your password</h2>
        <p>Hi {name},</p>
        <p>Click the link below to set a new password. This link expires in 30 minutes.</p>
        <p><a href="{reset_link}" style="color:#38bdf8;">{reset_link}</a></p>
        <p>If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    return send_email(to_email, subject, body)
