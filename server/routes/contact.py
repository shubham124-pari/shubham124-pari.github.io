import re
import json
import urllib.request

from flask import Blueprint, request, jsonify

from config import Config
from models.contact import create_message, list_by_user
from utils.security import decode_token
from utils.serializers import message_public

contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _optional_user_id():
    """If the caller sent a valid Bearer token, links the message to that
    account so it shows up in their dashboard's 'My Messages' history.
    Anonymous contact-form submissions (no token) are still accepted."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        payload = decode_token(auth_header.split(" ", 1)[1].strip())
        return payload["sub"]
    except Exception:
        return None


def _notify_owner(name, email, subject, message):
    """Best-effort email notification via Web3Forms. If it fails or no key
    is configured, we simply skip it — the message is already safely saved
    in MySQL by the time this is called, so a delivery failure here must
    never fail the API request."""
    if not Config.WEB3FORMS_ACCESS_KEY:
        return

    payload = json.dumps({
        "access_key": Config.WEB3FORMS_ACCESS_KEY,
        "name": name,
        "email": email,
        "subject": f"[Portfolio Contact] {subject or 'New message'}",
        "message": message,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.web3forms.com/submit",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # swallow — the message is already saved in MySQL either way


@contact_bp.post("")
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if len(name) < 2 or len(name) > 120:
        return jsonify({"error": "Please enter your full name."}), 400
    if not EMAIL_RE.match(email) or len(email) > 190:
        return jsonify({"error": "Please enter a valid email address."}), 400
    if subject and len(subject) > 200:
        return jsonify({"error": "Subject must be under 200 characters."}), 400
    if len(message) < 10 or len(message) > 3000:
        return jsonify({"error": "Message must be between 10 and 3000 characters."}), 400

    user_id = _optional_user_id()
    saved = create_message(name, email, subject or None, message, user_id=user_id)
    _notify_owner(name, email, subject, message)

    return jsonify({
        "message": "Your message has been sent. Thank you!",
        "data": message_public(saved),
    }), 201


@contact_bp.get("/mine")
def my_messages():
    user_id = _optional_user_id()
    if not user_id:
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    items = list_by_user(user_id)
    return jsonify({"messages": [message_public(m) for m in items]}), 200
