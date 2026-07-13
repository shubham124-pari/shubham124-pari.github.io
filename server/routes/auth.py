import re
import datetime
from flask import Blueprint, request, jsonify, g

import google.oauth2
from google.auth.transport import requests as google_requests

from config import Config
import models.user
from utils.security import (
    hash_password,
    verify_password,
    generate_token,
    token_required,
    generate_reset_token,
)
from utils.serializers import user_public as _user_public
from utils.email import send_reset_email
from models.profile_extras import log_activity

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # ---- Input validation ----
    if len(name) < 2:
        return jsonify({"error": "Please enter your full name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if models.user.find_by_email(email):
        return jsonify({"error": "An account with this email already exists."}), 409

    password_hash = hash_password(password)

    # The email configured as ADMIN_EMAIL in server/.env is auto-promoted
    # to the "admin" role the moment it signs up — this is the "hidden
    # admin login" bootstrap: no separate admin-creation step needed.
    role = "admin" if Config.ADMIN_EMAIL and email == Config.ADMIN_EMAIL.strip().lower() else "user"

    user = models.user.create_user(name, email, password_hash, role=role)

    token = generate_token(user["id"], user["email"]) # type: ignore
    log_activity(user["id"], "signup", None) # type: ignore
    return jsonify({"token": token, "user": _user_public(user)}), 201 # type: ignore


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not EMAIL_RE.match(email) or not password:
        return jsonify({"error": "Please enter a valid email and password."}), 400

    user = models.user.find_by_email(email)
    # Same error message whether the email doesn't exist or the password is
    # wrong — avoids leaking which emails are registered.
    if not user or not verify_password(password, user["password"]):
        return jsonify({"error": "Incorrect email or password."}), 401

    if user.get("is_banned"):
        return jsonify({"error": "This account has been suspended. Contact support."}), 403

    token = generate_token(user["id"], user["email"])
    log_activity(user["id"], "login", None) # type: ignore
    return jsonify({"token": token, "user": _user_public(user)}), 200


@auth_bp.post("/google")
def google_login():
    data = request.get_json(silent=True) or {}
    credential = data.get("credential")

    if not credential:
        return jsonify({"error": "Missing Google credential."}), 400

    try:
        idinfo = google.oauth2.id_token.verify_oauth2_token( # type: ignore
            credential, google_requests.Request(), Config.GOOGLE_CLIENT_ID
        )
    except ValueError:
        return jsonify({"error": "Invalid Google token."}), 401

    google_id = idinfo["sub"]
    email = (idinfo.get("email") or "").strip().lower()
    name = idinfo.get("name") or email.split("@")[0]

    if not email:
        return jsonify({"error": "Google account has no email."}), 400

    user = models.user.find_by_google_id(google_id)

    if not user:
        user = models.user.find_by_email(email)
        if user:
            user = models.user.link_google_id(user["id"], google_id)
        else:
            role = "admin" if Config.ADMIN_EMAIL and email == Config.ADMIN_EMAIL.strip().lower() else "user"
            user = models.user.create_google_user(name, email, google_id, role=role)

    if user.get("is_banned"): # type: ignore
        return jsonify({"error": "This account has been suspended. Contact support."}), 403

    token = generate_token(user["id"], user["email"]) # type: ignore
    log_activity(user["id"], "login", None) # type: ignore
    return jsonify({"token": token, "user": _user_public(user)}), 200 # type: ignore


@auth_bp.get("/me")
@token_required
def me():
    user = models.user.find_by_id(g.user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": _user_public(user)}), 200


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    # Always the same response whether or not the account exists —
    # avoids letting someone probe which emails are registered.
    generic = jsonify({"message": "If an account exists for that email, a reset link has been sent."})

    if not EMAIL_RE.match(email):
        return generic, 200

    user = models.user.find_by_email(email)
    if not user:
        return generic, 200

    token = generate_reset_token()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    models.user.set_reset_token(email, token, expiry)

    reset_link = f"{Config.FRONTEND_URL}/reset-password.html?token={token}"
    send_reset_email(user["email"], user["name"], reset_link)

    return generic, 200


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""

    if not token:
        return jsonify({"error": "Missing reset token."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400

    user = models.user.find_by_reset_token(token)
    if not user:
        return jsonify({"error": "This reset link is invalid or has expired."}), 400

    models.user.update_password(user["id"], hash_password(password))
    return jsonify({"message": "Password updated. You can now sign in."}), 200
