"""
routes/admin.py
=====================================================
Hidden admin panel API. Every route here requires
role == 'admin' (checked fresh from the DB on each
request by the admin_required decorator).

There's no separate "/admin login" — an admin just
signs in through the normal /api/auth/login like anyone
else; the frontend's admin.html page checks user.role
after login and only then shows the panel.
=====================================================
"""

from flask import Blueprint, request, jsonify, g

from models.user import (
    list_all_users,
    find_by_id,
    set_ban_status,
    delete_user,
    count_users,
    count_signups_last_days,
)
from models.contact import (
    list_all as list_all_messages,
    set_status as set_message_status,
    delete_message,
    count_total as count_total_messages,
    count_new as count_new_messages,
)
from models.project import count_total as count_total_projects
from models.chatbot import count_total as count_total_chats, count_last_days as count_chats_last_days
from utils.security import admin_required
from utils.serializers import user_admin_view, message_public

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------------------------------------------------
# Users
# ---------------------------------------------------

@admin_bp.get("/users")
@admin_required
def get_users():
    users = list_all_users()
    return jsonify({"users": [user_admin_view(u) for u in users]}), 200


@admin_bp.put("/users/<int:user_id>/ban")
@admin_required
def ban_user(user_id):
    data = request.get_json(silent=True) or {}
    is_banned = bool(data.get("is_banned", True))

    if user_id == g.user_id and is_banned:
        return jsonify({"error": "You can't ban your own account."}), 400

    ok = set_ban_status(user_id, is_banned)
    if not ok:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"message": "Banned." if is_banned else "Unbanned."}), 200


@admin_bp.delete("/users/<int:user_id>")
@admin_required
def remove_user(user_id):
    if user_id == g.user_id:
        return jsonify({"error": "You can't delete your own admin account here."}), 400

    ok = delete_user(user_id)
    if not ok:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"message": "User deleted."}), 200


# ---------------------------------------------------
# Contact messages
# ---------------------------------------------------

@admin_bp.get("/messages")
@admin_required
def get_messages():
    messages = list_all_messages()
    return jsonify({"messages": [message_public(m) for m in messages]}), 200


@admin_bp.put("/messages/<int:message_id>/status")
@admin_required
def update_message_status(message_id):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in ("new", "read", "resolved"):
        return jsonify({"error": "Status must be one of: new, read, resolved."}), 400

    ok = set_message_status(message_id, status)
    if not ok:
        return jsonify({"error": "Message not found."}), 404
    return jsonify({"message": "Status updated."}), 200


@admin_bp.delete("/messages/<int:message_id>")
@admin_required
def remove_message(message_id):
    ok = delete_message(message_id)
    if not ok:
        return jsonify({"error": "Message not found."}), 404
    return jsonify({"message": "Message deleted."}), 200


# ---------------------------------------------------
# Analytics
# ---------------------------------------------------

@admin_bp.get("/analytics")
@admin_required
def analytics():
    return jsonify({
        "total_users": count_users(),
        "total_projects": count_total_projects(),
        "total_messages": count_total_messages(),
        "new_messages": count_new_messages(),
        "total_chatbot_conversations": count_total_chats(),
        "signups_last_7_days": count_signups_last_days(7),
        "chats_last_7_days": count_chats_last_days(7),
    }), 200
