import re
from flask import Blueprint, request, jsonify, g

from models.social import (
    find_by_username, set_username, set_profile_visibility, search_users,
    follow_user, unfollow_user, is_following, list_followers, list_following,
    count_followers, count_following,
    create_connection_request, find_connection_between, respond_to_connection,
    are_connected, list_pending_requests, list_connections,
)
from utils.security import token_required, optional_token
from utils.privacy import can_view_profile, VISIBILITY_LEVELS
from utils.serializers import profile_public

social_bp = Blueprint("social", __name__, url_prefix="/api/social")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


# ---------------------------------------------------
# Profile URL: GET /api/social/profile/<username>
# Works for signed-out visitors too (optional_token) — this is the
# endpoint the public "/u/<username>" frontend page calls.
# ---------------------------------------------------

@social_bp.get("/profile/<username>")
@optional_token
def get_profile_by_username(username):
    user = find_by_username(username)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if not can_view_profile(g.user_id, user):
        # Deliberately the same 404 as "doesn't exist" — a private
        # account's existence at this exact username isn't leaked either.
        return jsonify({"error": "This profile is private."}), 403

    viewer_id = g.user_id
    is_owner = viewer_id is not None and viewer_id == user["id"]
    following = viewer_id is not None and is_following(viewer_id, user["id"])
    connected = viewer_id is not None and are_connected(viewer_id, user["id"])

    data = profile_public(
        user, is_owner=is_owner, is_following=following, is_connected=connected,
        followers=count_followers(user["id"]), following=count_following(user["id"]),
    )
    return jsonify({"profile": data}), 200


@social_bp.put("/profile/settings")
@token_required
def update_profile_settings():
    data = request.get_json(silent=True) or {}
    updated = {}

    if "username" in data:
        username = (data.get("username") or "").strip().lower()
        if not USERNAME_RE.match(username):
            return jsonify({"error": "Username must be 3-30 characters: letters, numbers, underscore."}), 400
        existing = find_by_username(username)
        if existing and existing["id"] != g.user_id:
            return jsonify({"error": "That username is already taken."}), 409
        set_username(g.user_id, username)
        updated["username"] = username

    if "profile_visibility" in data:
        visibility = (data.get("profile_visibility") or "").strip().lower()
        if visibility not in VISIBILITY_LEVELS:
            return jsonify({"error": "Visibility must be public, connections_only, or private."}), 400
        set_profile_visibility(g.user_id, visibility)
        updated["profile_visibility"] = visibility

    if not updated:
        return jsonify({"error": "Nothing to update."}), 400

    return jsonify({"updated": updated}), 200


# ---------------------------------------------------
# Search — only ever returns name/username/photo, never email or files.
# ---------------------------------------------------

@social_bp.get("/search")
@token_required
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters."}), 400
    results = search_users(query, viewer_id=g.user_id)
    return jsonify({"results": [
        profile_public(u, is_following=is_following(g.user_id, u["id"]),
                        is_connected=are_connected(g.user_id, u["id"]))
        for u in results
    ]}), 200


# ---------------------------------------------------
# Follow system (one-directional, no approval)
# ---------------------------------------------------

@social_bp.post("/follow/<int:user_id>")
@token_required
def follow(user_id):
    if user_id == g.user_id:
        return jsonify({"error": "You can't follow yourself."}), 400
    from models.user import find_by_id
    if not find_by_id(user_id):
        return jsonify({"error": "User not found."}), 404
    follow_user(g.user_id, user_id)
    return jsonify({"message": "Followed.", "following": True}), 200


@social_bp.delete("/follow/<int:user_id>")
@token_required
def unfollow(user_id):
    unfollow_user(g.user_id, user_id)
    return jsonify({"message": "Unfollowed.", "following": False}), 200


@social_bp.get("/followers/<username>")
@optional_token
def followers(username):
    user = find_by_username(username)
    if not user or not can_view_profile(g.user_id, user):
        return jsonify({"error": "User not found."}), 404
    return jsonify({"followers": [profile_public(u) for u in list_followers(user["id"])]}), 200


@social_bp.get("/following/<username>")
@optional_token
def following(username):
    user = find_by_username(username)
    if not user or not can_view_profile(g.user_id, user):
        return jsonify({"error": "User not found."}), 404
    return jsonify({"following": [profile_public(u) for u in list_following(user["id"])]}), 200


# ---------------------------------------------------
# Connection requests (two-directional, requires accept)
# ---------------------------------------------------

@social_bp.post("/connections/request/<int:user_id>")
@token_required
def send_connection_request(user_id):
    if user_id == g.user_id:
        return jsonify({"error": "You can't connect with yourself."}), 400

    from models.user import find_by_id
    if not find_by_id(user_id):
        return jsonify({"error": "User not found."}), 404

    existing = find_connection_between(g.user_id, user_id)
    if existing:
        if existing["status"] == "accepted":
            return jsonify({"error": "You're already connected."}), 409
        if existing["status"] == "pending":
            return jsonify({"error": "A request is already pending."}), 409
        if existing["status"] == "rejected":
            return jsonify({"error": "This request was previously declined."}), 409

    req = create_connection_request(g.user_id, user_id)
    return jsonify({"request": {"id": req["id"], "status": req["status"]}}), 201


@social_bp.post("/connections/<int:request_id>/accept")
@token_required
def accept_connection(request_id):
    ok = respond_to_connection(request_id, g.user_id, accept=True)
    if not ok:
        return jsonify({"error": "Request not found, already handled, or not addressed to you."}), 404
    return jsonify({"message": "Connection accepted."}), 200


@social_bp.post("/connections/<int:request_id>/reject")
@token_required
def reject_connection(request_id):
    ok = respond_to_connection(request_id, g.user_id, accept=False)
    if not ok:
        return jsonify({"error": "Request not found, already handled, or not addressed to you."}), 404
    return jsonify({"message": "Connection rejected."}), 200


@social_bp.get("/connections/pending")
@token_required
def pending_requests():
    rows = list_pending_requests(g.user_id)
    return jsonify({"pending": [
        {"request_id": r["id"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
         "requester": profile_public(r)}
        for r in rows
    ]}), 200


@social_bp.get("/connections")
@token_required
def my_connections():
    return jsonify({"connections": [profile_public(u) for u in list_connections(g.user_id)]}), 200
