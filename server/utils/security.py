"""
Password hashing + JWT helpers used across the app.

Password hashing: uses Werkzeug's generate_password_hash / check_password_hash
(scrypt under the hood). This ships with Flask itself — no extra C-extension
dependency like bcrypt is required, and it's just as secure.
"""

import datetime
import secrets
import jwt
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config


# ---------------------------------------------------
# Passwords
# ---------------------------------------------------

def hash_password(plain_password: str) -> str:
    return generate_password_hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, plain_password)


# ---------------------------------------------------
# JWT
# ---------------------------------------------------

def generate_token(user_id: int, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(hours=Config.JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])


def generate_reset_token() -> str:
    """URL-safe, unguessable token for the password-reset link."""
    return secrets.token_urlsafe(32)


def token_required(f):
    """Route decorator: requires 'Authorization: Bearer <token>' header.
    On success, sets g.user_id / g.user_email for the route to use.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired, please sign in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        g.user_id = payload["sub"]
        g.user_email = payload["email"]
        return f(*args, **kwargs)

    return wrapper


def admin_required(f):
    """Route decorator: requires a valid token AND role == 'admin'.
    Looks the role up fresh from the database on every request (not from
    the JWT) so a demotion/ban takes effect immediately instead of only
    after the token expires.
    """

    @wraps(f)
    @token_required
    def wrapper(*args, **kwargs):
        # Local import avoids a circular import (models.user imports
        # nothing from utils, but keeping this lazy is cheap insurance).
        from models.user import find_by_id

        user = find_by_id(g.user_id)
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required."}), 403
        if user.get("is_banned"):
            return jsonify({"error": "This account has been suspended."}), 403
        return f(*args, **kwargs)

    return wrapper


def optional_token(f):
    """Route decorator for endpoints that behave differently for signed-in
    vs. anonymous visitors (public profiles, public posts) but never
    *require* sign-in. Sets g.user_id = None (not missing) when no valid
    token is present, so routes can just do `if g.user_id == ...` without
    an extra hasattr check. An expired/invalid token is treated the same
    as "no token" here — this endpoint never 401s on a bad token, it just
    falls back to the anonymous view.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        g.user_id = None
        g.user_email = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = decode_token(token)
                g.user_id = payload["sub"]
                g.user_email = payload["email"]
            except jwt.PyJWTError:
                pass
        return f(*args, **kwargs)

    return wrapper
