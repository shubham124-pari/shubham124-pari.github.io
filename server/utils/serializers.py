"""
Shared response-shaping helpers.
Kept separate so every route that returns a user object (auth, profile,
admin later) uses the exact same "never leak the password hash" logic.
"""

import datetime


def _iso(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return str(value) if value is not None else None


def user_public(user: dict) -> dict:
    """Never send the password hash back to the client."""
    return {
        "id": user["id"],
        "name": user["name"],
        "username": user.get("username"),
        "email": user["email"],
        "profile_photo": user.get("profile_photo"),
        "cover_photo": user.get("cover_photo"),
        "bio": user.get("bio"),
        "resume": user.get("resume"),
        "certificate": user.get("certificate"),
        "role": user.get("role", "user"),
        "theme": user.get("theme", "dark"),
        "profile_visibility": user.get("profile_visibility", "public"),
        "notify_email": bool(user.get("notify_email", 1)),
        "notify_chat": bool(user.get("notify_chat", 1)),
        "created_at": _iso(user.get("created_at")),
    }


def user_admin_view(user: dict) -> dict:
    """Extra fields only the admin panel is allowed to see."""
    data = user_public(user)
    data["is_banned"] = bool(user.get("is_banned"))
    return data


def project_public(project: dict) -> dict:
    return {
        "id": project["id"],
        "title": project["title"],
        "description": project.get("description"),
        "image": project.get("image"),
        "github": project.get("github"),
        "demo": project.get("demo"),
        "created_at": _iso(project.get("created_at")),
    }


def message_public(msg: dict) -> dict:
    return {
        "id": msg["id"],
        "user_id": msg.get("user_id"),
        "name": msg["name"],
        "email": msg["email"],
        "subject": msg.get("subject"),
        "message": msg["message"],
        "status": msg.get("status", "new"),
        "date": _iso(msg.get("date")),
    }


def skill_public(row: dict) -> dict:
    return {"id": row["id"], "name": row["name"], "level": row["level"]}


def education_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "school": row["school"],
        "degree": row.get("degree"),
        "field": row.get("field"),
        "start_year": row.get("start_year"),
        "end_year": row.get("end_year"),
        "description": row.get("description"),
    }


def experience_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "company": row["company"],
        "role": row["role"],
        "start_date": _iso(row.get("start_date")),
        "end_date": _iso(row.get("end_date")),
        "is_current": bool(row.get("is_current")),
        "description": row.get("description"),
    }


def notification_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "body": row.get("body"),
        "link": row.get("link"),
        "is_read": bool(row.get("is_read")),
        "created_at": _iso(row.get("created_at")),
    }


def activity_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "action": row["action"],
        "meta": row.get("meta"),
        "created_at": _iso(row.get("created_at")),
    }


def chatbot_entry_public(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "question": entry["question"],
        "answer": entry["answer"],
        "time": _iso(entry.get("time")),
    }


def chat_user_public(user: dict) -> dict:
    """Minimal public profile used inside chat payloads (conversation
    list, 'new chat' picker, presence updates)."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user.get("email"),
        "profile_photo": user.get("profile_photo"),
        "is_online": bool(user.get("is_online")),
        "last_seen": _iso(user.get("last_seen")),
    }


def chat_message_public(msg: dict) -> dict:
    deleted = bool(msg.get("deleted_at"))
    return {
        "id": msg["id"],
        "conversation_id": msg["conversation_id"],
        "sender_id": msg["sender_id"],
        "message_type": msg.get("message_type", "text"),
        "body": None if deleted else msg.get("body"),
        "attachment_url": None if deleted else msg.get("attachment_url"),
        "attachment_name": None if deleted else msg.get("attachment_name"),
        "created_at": _iso(msg.get("created_at")),
        "deleted": deleted,
    }


def conversation_summary_public(conv: dict) -> dict:
    last = conv.get("last_message")
    return {
        "conversation_id": conv["conversation_id"],
        "other_user": chat_user_public(conv["other_user"]),
        "last_message": chat_message_public(last) if last else None,
        "unread_count": conv.get("unread_count", 0),
    }


def profile_public(user: dict, *, is_owner: bool = False, is_following: bool = False,
                    is_connected: bool = False, followers: int = 0, following: int = 0) -> dict:
    """Public-facing profile card (used by the social/follow/connections
    endpoints). Never includes email or password — only the fields a
    visitor is allowed to see. `is_owner` is set by the route after it has
    already decided the viewer may see this profile at all; this function
    never makes that decision itself."""
    return {
        "id": user["id"],
        "name": user["name"],
        "username": user.get("username"),
        "profile_photo": user.get("profile_photo"),
        "bio": user.get("bio"),
        "profile_visibility": user.get("profile_visibility", "public"),
        "followers_count": followers,
        "following_count": following,
        "is_owner": is_owner,
        "is_following": is_following,
        "is_connected": is_connected,
        "created_at": _iso(user.get("created_at")),
    }


def post_public(post: dict, *, liked: bool = False, bookmarked: bool = False,
                 likes: int = 0, comments: int = 0, shares: int = 0) -> dict:
    data = {
        "id": post["id"],
        "user_id": post["user_id"],
        "post_type": post.get("post_type", "text"),
        "content": post.get("content"),
        "media_url": post.get("media_url"),
        "visibility": post.get("visibility", "public"),
        "is_edited": bool(post.get("is_edited")),
        "created_at": _iso(post.get("created_at")),
        "updated_at": _iso(post.get("updated_at")),
        "likes_count": likes,
        "comments_count": comments,
        "shares_count": shares,
        "liked_by_viewer": liked,
        "bookmarked_by_viewer": bookmarked,
    }
    # Feed/explore queries join in the author's public info directly on
    # the post row — attach it as a nested object when present.
    if "username" in post:
        data["author"] = {
            "id": post["user_id"],
            "name": post.get("name"),
            "username": post.get("username"),
            "profile_photo": post.get("profile_photo"),
        }
    return data


def comment_public(comment: dict) -> dict:
    return {
        "id": comment["id"],
        "post_id": comment["post_id"],
        "content": comment["content"],
        "created_at": _iso(comment.get("created_at")),
        "author": {
            "id": comment["user_id"],
            "name": comment.get("name"),
            "username": comment.get("username"),
            "profile_photo": comment.get("profile_photo"),
        },
    }
