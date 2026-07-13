import os
import time
import logging
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import Config
from routes.auth import auth_bp
from routes.user import user_bp
from routes.upload import upload_bp, UPLOAD_ROOT
from routes.project import project_bp
from routes.contact import contact_bp
from routes.chatbot import chatbot_bp
from routes.admin import admin_bp
from routes.chat import chat_bp
from routes.social import social_bp
from routes.post import post_bp
from routes.interaction import interaction_bp
from sockets import socketio

Config.validate()

# -----------------------------------------------------
# Logging — replaces scattered print() calls with proper,
# timestamped, leveled log output. In production this goes
# to stdout, which Render/Railway capture automatically;
# for local dev it just prints to your terminal the same way
# print() did, but with a timestamp and level attached.
# -----------------------------------------------------
logging.basicConfig(
    level=logging.INFO if Config.FLASK_ENV == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("portfolio")

app = Flask(__name__)
CORS(app, origins=[Config.FRONTEND_ORIGIN] if Config.FRONTEND_ORIGIN != "*" else "*")

# Hard cap on request body size (10MB) so an oversized upload is rejected
# immediately instead of being fully read into memory first.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(project_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(social_bp)
app.register_blueprint(post_bp)
app.register_blueprint(interaction_bp)

# Attaches Socket.IO's own routes (the /socket.io/ handshake endpoint) to
# this same Flask app/port — the frontend talks to one origin for both
# the REST API and the chat websocket. cors_allowed_origins mirrors the
# CORS() setup above so both are governed by the same FRONTEND_ORIGIN.
socketio.init_app(
    app,
    cors_allowed_origins=[Config.FRONTEND_ORIGIN] if Config.FRONTEND_ORIGIN != "*" else "*",
)


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Max size is 10MB."}), 413


@app.errorhandler(404)
def not_found(e):
    # Keep API responses consistent JSON instead of Flask's default HTML
    # 404 page — the frontend's fetch() calls expect JSON everywhere.
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    # Log the real exception server-side (with traceback) but never leak
    # internals (stack traces, file paths, SQL) to the client response.
    logger.exception("Unhandled server error on %s %s", request.method, request.path)
    return jsonify({"error": "Something went wrong. Please try again later."}), 500


@app.after_request
def set_secure_headers(response):
    # Baseline security headers — cheap to set, closes off a handful of
    # common browser-side attack classes (clickjacking, MIME-sniffing,
    # referrer leakage) regardless of what any individual route does.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if Config.FLASK_ENV == "production":
        # Only sent over HTTPS deployments — forces browsers to remember
        # to always use HTTPS for this domain for the next 2 years.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.before_request
def log_request():
    logger.info("%s %s from %s", request.method, request.path, request.remote_addr)


@app.get("/uploads/<subfolder>/<filename>")
def serve_upload(subfolder, filename):
    # send_from_directory itself blocks '..' path traversal, but we also
    # only ever allow the exact subfolders we create uploads in.
    if subfolder not in ("resumes", "certificates", "photos", "projects", "chat", "posts"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(os.path.join(UPLOAD_ROOT, subfolder), filename)


# -----------------------------------------------------
# Very small in-memory rate limiter for public, unauthenticated
# write endpoints (auth + contact form).
# Good enough for a single-process/dev deployment; if you
# scale to multiple workers/servers later, swap this for
# Flask-Limiter + Redis instead.
# -----------------------------------------------------
RATE_LIMIT = 10          # requests
RATE_WINDOW = 60         # seconds
_hits = defaultdict(deque)
_RATE_LIMITED_PREFIXES = ("/api/auth/", "/api/contact")


@app.before_request
def rate_limit_public_endpoints():
    if app.config.get("TESTING"):
        return
    if not request.path.startswith(_RATE_LIMITED_PREFIXES):
        return
    key = request.remote_addr or "unknown"
    now = time.time()
    window = _hits[key]
    while window and now - window[0] > RATE_WINDOW:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        return jsonify({"error": "Too many requests. Please try again in a minute."}), 429
    window.append(now)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # socketio.run() (not app.run()) — it wraps Flask's dev server so
    # WebSocket upgrade requests for the chat feature are handled
    # correctly. In production, run via the same call behind a
    # WSGI-aware process (see server/SETUP.md).
    socketio.run(app, debug=Config.FLASK_ENV != "production", port=5000, allow_unsafe_werkzeug=True)
