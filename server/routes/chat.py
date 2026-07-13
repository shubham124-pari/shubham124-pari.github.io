"""
routes/chat.py
=====================================================
REST side of private one-to-one chat. The real-time half
(typing indicators, live message delivery, presence) lives
in sockets.py over Socket.IO — this blueprint covers
everything a page-load / refresh / search needs: conversation
list, paginated history, search, delete, and a REST fallback
for marking messages read.
=====================================================
"""

from flask import Blueprint, request, jsonify, g

import models.chat as chat_model
from models.user import find_by_id
from utils.security import token_required
from utils.serializers import (
    chat_user_public,
    chat_message_public,
    conversation_summary_public,
)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

MAX_MESSAGE_LEN = 4000
MAX_SEARCH_LEN = 200


@chat_bp.get("/users")
@token_required
def list_chat_users():
    """Users available to start a new conversation with."""
    search = (request.args.get("search") or "").strip()[:100]
    users = chat_model.list_chat_candidates(g.user_id, search)
    return jsonify({"users": [chat_user_public(u) for u in users]}), 200


@chat_bp.get("/conversations")
@token_required
def list_conversations():
    conversations = chat_model.list_conversations_for_user(g.user_id)
    return jsonify(
        {"conversations": [conversation_summary_public(c) for c in conversations]}
    ), 200


@chat_bp.post("/conversations")
@token_required
def start_conversation():
    data = request.get_json(silent=True) or {}
    other_user_id = data.get("user_id")

    if not other_user_id:
        return jsonify({"error": "user_id is required."}), 400
    if int(other_user_id) == g.user_id:
        return jsonify({"error": "You can't start a conversation with yourself."}), 400

    other_user = find_by_id(other_user_id)
    if not other_user:
        return jsonify({"error": "User not found."}), 404

    conversation_id = chat_model.get_or_create_direct_conversation(g.user_id, other_user_id)
    return jsonify({
        "conversation_id": conversation_id,
        "other_user": chat_user_public(other_user),
    }), 200


@chat_bp.get("/conversations/<int:conversation_id>/messages")
@token_required
def get_messages(conversation_id):
    if not chat_model.is_participant(conversation_id, g.user_id):
        return jsonify({"error": "Conversation not found."}), 404

    before_id = request.args.get("before", type=int)
    limit = min(request.args.get("limit", 30, type=int), 100)

    messages = chat_model.list_messages(conversation_id, before_id=before_id, limit=limit) # type: ignore
    read_state = chat_model.get_read_state(conversation_id)

    return jsonify({
        "messages": [chat_message_public(m) for m in messages],
        "read_state": read_state,
        "has_more": len(messages) == limit,
    }), 200


@chat_bp.get("/search")
@token_required
def search_messages():
    query = (request.args.get("q") or "").strip()[:MAX_SEARCH_LEN]
    if len(query) < 2:
        return jsonify({"error": "Type at least 2 characters to search."}), 400

    results = chat_model.search_messages(g.user_id, query)
    return jsonify({"results": [chat_message_public(m) for m in results]}), 200


@chat_bp.delete("/messages/<int:message_id>")
@token_required
def delete_message(message_id):
    deleted = chat_model.soft_delete_message(message_id, g.user_id)
    if not deleted:
        return jsonify({"error": "Message not found or you can't delete it."}), 404
    return jsonify({"deleted": True, "message_id": message_id}), 200


@chat_bp.post("/conversations/<int:conversation_id>/read")
@token_required
def mark_read(conversation_id):
    if not chat_model.is_participant(conversation_id, g.user_id):
        return jsonify({"error": "Conversation not found."}), 404

    data = request.get_json(silent=True) or {}
    message_id = data.get("message_id")
    if not message_id:
        return jsonify({"error": "message_id is required."}), 400

    chat_model.mark_read(conversation_id, g.user_id, message_id)
    return jsonify({"ok": True}), 200
