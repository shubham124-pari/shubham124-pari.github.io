"""
routes/chatbot.py
=====================================================
AI chatbot endpoint. Works for both logged-in and
anonymous visitors — if a valid Bearer token is sent,
the Q&A pair is linked to that user; otherwise it's
saved with user_id = NULL.
=====================================================
"""

import time
from collections import defaultdict, deque

from flask import Blueprint, request, jsonify, g

from models.chatbot import create_entry, list_by_user
from services.ai_provider import ask_ai, AIProviderError
from utils.security import token_required, decode_token
from utils.serializers import chatbot_entry_public

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")

MAX_QUESTION_LEN = 500

# Small extra rate limit specifically for the chatbot (AI calls cost money),
# on top of app.py's general /api/ limiter.
_CHAT_LIMIT = 15
_CHAT_WINDOW = 300
_hits = defaultdict(deque)


def _optional_user_id():
    """Returns the caller's user id if they sent a valid Bearer token,
    otherwise None (anonymous chat is allowed)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        payload = decode_token(auth_header.split(" ", 1)[1].strip())
        return payload["sub"]
    except Exception:
        return None


@chatbot_bp.post("/ask")
def ask():
    key = request.remote_addr or "unknown"
    now = time.time()
    window = _hits[key]
    while window and now - window[0] > _CHAT_WINDOW:
        window.popleft()
    if len(window) >= _CHAT_LIMIT:
        return jsonify({"error": "Too many questions. Please wait a bit and try again."}), 429
    window.append(now)

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    # Client-sent history covers signed-out visitors (nothing is stored
    # server-side for them); signed-in users' history comes from the DB
    # instead, below, so their memory survives across sessions/devices.
    client_history = data.get("history") or []

    if len(question) < 2:
        return jsonify({"error": "Please type a question."}), 400
    if len(question) > MAX_QUESTION_LEN:
        return jsonify({"error": f"Please keep questions under {MAX_QUESTION_LEN} characters."}), 400

    user_id = _optional_user_id()

    if user_id:
        history = list(reversed(list_by_user(user_id, limit=6)))
    else:
        # Trust only the shape, not arbitrary content, from the client.
        history = [
            {"question": str(t.get("question", ""))[:MAX_QUESTION_LEN], "answer": str(t.get("answer", ""))[:2000]}
            for t in client_history[-6:]
            if isinstance(t, dict)
        ]

    try:
        result = ask_ai(question, history=history)
    except AIProviderError as err:
        return jsonify({"error": str(err)}), 503

    create_entry(user_id, question, result["answer"])

    return jsonify({
        "answer": result["answer"],
        "language": result["language"],
        "language_name": result["language_name"],
    }), 200


@chatbot_bp.get("/history")
@token_required
def history():
    items = list_by_user(g.user_id)
    return jsonify({"history": [chatbot_entry_public(h) for h in items]}), 200
