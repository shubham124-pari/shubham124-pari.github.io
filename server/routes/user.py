"""
routes/user.py
=====================================================
Signed-in member's own account: profile, settings (theme /
privacy / notifications / password), account deletion, skills,
education, experience, the notification center, the activity
timeline, and a personal dashboard-analytics summary.

(File uploads — photo/cover/resume/certificate — live in
routes/upload.py; private chat lives in routes/chat.py.)
=====================================================
"""

from flask import Blueprint, request, jsonify, g

from models.user import (
    find_by_id, find_by_email, update_profile, update_password,
    update_settings, delete_user,
)
import models.profile_extras as extras
import models.project as project_model
import models.chatbot as chatbot_model
import models.contact as contact_model
import models.chat as chat_model
from utils.security import token_required, hash_password, verify_password
from utils.serializers import (
    user_public, skill_public, education_public, experience_public,
    notification_public, activity_public,
)

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


# ---------------------------------------------------
# Profile
# ---------------------------------------------------

@user_bp.get("/profile")
@token_required
def get_profile():
    user = find_by_id(g.user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user_public(user)}), 200


@user_bp.put("/profile")
@token_required
def edit_profile():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    bio = (data.get("bio") or "").strip()

    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters."}), 400
    if len(bio) > 1000:
        return jsonify({"error": "Bio must be under 1000 characters."}), 400

    user = update_profile(g.user_id, name, bio)
    if not user:
        return jsonify({"error": "User not found."}), 404

    extras.log_activity(g.user_id, "profile_update", "Updated name/bio")
    return jsonify({"user": user_public(user)}), 200


# ---------------------------------------------------
# Settings: theme / privacy / notifications / password
# ---------------------------------------------------

@user_bp.put("/settings/theme")
@token_required
def update_theme():
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").strip().lower()
    if theme not in ("dark", "light"):
        return jsonify({"error": "Theme must be 'dark' or 'light'."}), 400

    user = update_settings(g.user_id, theme=theme)
    extras.log_activity(g.user_id, "settings_update", f"Theme set to {theme}")
    return jsonify({"user": user_public(user)}), 200


@user_bp.put("/settings/privacy")
@token_required
def update_privacy():
    data = request.get_json(silent=True) or {}
    visibility = (data.get("profile_visibility") or "").strip().lower()
    if visibility not in ("public", "private"):
        return jsonify({"error": "Visibility must be 'public' or 'private'."}), 400

    user = update_settings(g.user_id, profile_visibility=visibility)
    extras.log_activity(g.user_id, "settings_update", f"Profile visibility set to {visibility}")
    return jsonify({"user": user_public(user)}), 200


@user_bp.put("/settings/notifications")
@token_required
def update_notification_prefs():
    data = request.get_json(silent=True) or {}
    fields = {}
    if "notify_email" in data:
        fields["notify_email"] = 1 if data.get("notify_email") else 0
    if "notify_chat" in data:
        fields["notify_chat"] = 1 if data.get("notify_chat") else 0
    if not fields:
        return jsonify({"error": "Nothing to update."}), 400

    user = update_settings(g.user_id, **fields)
    extras.log_activity(g.user_id, "settings_update", "Updated notification preferences")
    return jsonify({"user": user_public(user)}), 200


@user_bp.put("/settings/password")
@token_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm = data.get("confirm") or ""

    full_user = find_by_email(g.user_email)
    if not full_user or not verify_password(current_password, full_user["password"]):
        return jsonify({"error": "Current password is incorrect."}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400
    if new_password != confirm:
        return jsonify({"error": "New passwords do not match."}), 400

    update_password(g.user_id, hash_password(new_password))
    extras.log_activity(g.user_id, "password_change", None)
    extras.create_notification(
        g.user_id, "account", "Password changed",
        "Your password was changed. If this wasn't you, contact support immediately.",
    )
    return jsonify({"message": "Password changed successfully."}), 200


@user_bp.delete("/account")
@token_required
def delete_account():
    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    full_user = find_by_email(g.user_email)
    if not full_user or not verify_password(password, full_user["password"]):
        return jsonify({"error": "Incorrect password. Account not deleted."}), 400

    delete_user(g.user_id)
    return jsonify({"message": "Account deleted."}), 200


# ---------------------------------------------------
# Skills
# ---------------------------------------------------

@user_bp.get("/skills")
@token_required
def list_skills():
    return jsonify({"skills": [skill_public(s) for s in extras.list_skills(g.user_id)]}), 200


@user_bp.post("/skills")
@token_required
def add_skill():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    level = data.get("level", 3)

    if len(name) < 1 or len(name) > 80:
        return jsonify({"error": "Skill name must be 1-80 characters."}), 400
    try:
        level = max(1, min(5, int(level)))
    except (TypeError, ValueError):
        level = 3

    skill_id = extras.add_skill(g.user_id, name, level)
    extras.log_activity(g.user_id, "skill_add", name)
    return jsonify({"id": skill_id, "name": name, "level": level}), 201


@user_bp.put("/skills/<int:skill_id>")
@token_required
def edit_skill(skill_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    level = data.get("level", 3)

    if len(name) < 1 or len(name) > 80:
        return jsonify({"error": "Skill name must be 1-80 characters."}), 400
    try:
        level = max(1, min(5, int(level)))
    except (TypeError, ValueError):
        level = 3

    ok = extras.update_skill(skill_id, g.user_id, name, level)
    if not ok:
        return jsonify({"error": "Skill not found."}), 404
    return jsonify({"id": skill_id, "name": name, "level": level}), 200


@user_bp.delete("/skills/<int:skill_id>")
@token_required
def remove_skill(skill_id):
    ok = extras.delete_skill(skill_id, g.user_id)
    if not ok:
        return jsonify({"error": "Skill not found."}), 404
    return jsonify({"deleted": True}), 200


# ---------------------------------------------------
# Education
# ---------------------------------------------------

def _parse_education(data):
    school = (data.get("school") or "").strip()
    degree = (data.get("degree") or "").strip() or None
    field = (data.get("field") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    start_year = data.get("start_year") or None
    end_year = data.get("end_year") or None
    try:
        start_year = int(start_year) if start_year else None
        end_year = int(end_year) if end_year else None
    except (TypeError, ValueError):
        return None, "Years must be numbers."
    if len(school) < 1 or len(school) > 150:
        return None, "School name must be 1-150 characters."
    return {
        "school": school, "degree": degree, "field": field,
        "start_year": start_year, "end_year": end_year, "description": description,
    }, None


@user_bp.get("/education")
@token_required
def list_education():
    return jsonify({"education": [education_public(e) for e in extras.list_education(g.user_id)]}), 200


@user_bp.post("/education")
@token_required
def add_education():
    parsed, error = _parse_education(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    new_id = extras.add_education(g.user_id, **parsed)
    extras.log_activity(g.user_id, "education_add", parsed["school"])
    return jsonify({"id": new_id, **parsed}), 201


@user_bp.put("/education/<int:entry_id>")
@token_required
def edit_education(entry_id):
    parsed, error = _parse_education(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    ok = extras.update_education(entry_id, g.user_id, **parsed)
    if not ok:
        return jsonify({"error": "Education entry not found."}), 404
    return jsonify({"id": entry_id, **parsed}), 200


@user_bp.delete("/education/<int:entry_id>")
@token_required
def remove_education(entry_id):
    ok = extras.delete_education(entry_id, g.user_id)
    if not ok:
        return jsonify({"error": "Education entry not found."}), 404
    return jsonify({"deleted": True}), 200


# ---------------------------------------------------
# Experience
# ---------------------------------------------------

def _parse_experience(data):
    company = (data.get("company") or "").strip()
    role = (data.get("role") or "").strip()
    description = (data.get("description") or "").strip() or None
    start_date = data.get("start_date") or None
    end_date = data.get("end_date") or None
    is_current = bool(data.get("is_current"))
    if is_current:
        end_date = None

    if len(company) < 1 or len(company) > 150:
        return None, "Company must be 1-150 characters."
    if len(role) < 1 or len(role) > 150:
        return None, "Role must be 1-150 characters."
    return {
        "company": company, "role": role, "start_date": start_date,
        "end_date": end_date, "is_current": is_current, "description": description,
    }, None


@user_bp.get("/experience")
@token_required
def list_experience():
    return jsonify({"experience": [experience_public(e) for e in extras.list_experience(g.user_id)]}), 200


@user_bp.post("/experience")
@token_required
def add_experience():
    parsed, error = _parse_experience(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    new_id = extras.add_experience(g.user_id, **parsed)
    extras.log_activity(g.user_id, "experience_add", f"{parsed['role']} at {parsed['company']}")
    return jsonify({"id": new_id, **parsed}), 201


@user_bp.put("/experience/<int:entry_id>")
@token_required
def edit_experience(entry_id):
    parsed, error = _parse_experience(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    ok = extras.update_experience(entry_id, g.user_id, **parsed)
    if not ok:
        return jsonify({"error": "Experience entry not found."}), 404
    return jsonify({"id": entry_id, **parsed}), 200


@user_bp.delete("/experience/<int:entry_id>")
@token_required
def remove_experience(entry_id):
    ok = extras.delete_experience(entry_id, g.user_id)
    if not ok:
        return jsonify({"error": "Experience entry not found."}), 404
    return jsonify({"deleted": True}), 200


# ---------------------------------------------------
# Notification center
# ---------------------------------------------------

@user_bp.get("/notifications")
@token_required
def list_notifications():
    notifications = extras.list_notifications(g.user_id)
    return jsonify({
        "notifications": [notification_public(n) for n in notifications],
        "unread_count": extras.count_unread_notifications(g.user_id),
    }), 200


@user_bp.put("/notifications/<int:notification_id>/read")
@token_required
def mark_notification_read(notification_id):
    ok = extras.mark_notification_read(notification_id, g.user_id)
    if not ok:
        return jsonify({"error": "Notification not found."}), 404
    return jsonify({"ok": True}), 200


@user_bp.put("/notifications/read-all")
@token_required
def mark_all_notifications_read():
    extras.mark_all_notifications_read(g.user_id)
    return jsonify({"ok": True}), 200


# ---------------------------------------------------
# Activity timeline
# ---------------------------------------------------

@user_bp.get("/activity")
@token_required
def get_activity():
    return jsonify({"activity": [activity_public(a) for a in extras.list_activity(g.user_id)]}), 200


# ---------------------------------------------------
# Dashboard analytics (personal, not admin-wide)
# ---------------------------------------------------

@user_bp.get("/dashboard/summary")
@token_required
def dashboard_summary():
    user = find_by_id(g.user_id)
    return jsonify({
        "projects": len(project_model.list_by_user(g.user_id)),
        "skills": len(extras.list_skills(g.user_id)),
        "support_messages": len(contact_model.list_by_user(g.user_id)),
        "ai_conversations": len(chatbot_model.list_by_user(g.user_id)),
        "chat_conversations": len(chat_model.list_conversations_for_user(g.user_id)),
        "unread_notifications": extras.count_unread_notifications(g.user_id),
        "member_since": user["created_at"].isoformat() if user and user.get("created_at") else None,
        "profile_complete": bool(user and user.get("bio") and user.get("profile_photo")) if user else False,
    }), 200
