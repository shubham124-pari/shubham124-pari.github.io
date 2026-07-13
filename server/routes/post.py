from flask import Blueprint, request, jsonify, g

from models.post import (
    create_post, find_post_by_id, update_post, delete_post,
    list_posts_by_user, list_feed_candidates, list_public_posts,
)
from models.social import find_by_username
from models.interaction import has_liked, has_bookmarked, count_likes, count_comments, count_shares
from utils.security import token_required, optional_token
from utils.privacy import can_view_post, can_view_profile
from utils.serializers import post_public

post_bp = Blueprint("post", __name__, url_prefix="/api/posts")

VISIBILITY_LEVELS = {"public", "connections_only", "private"}
POST_TYPES = {"text", "image", "video"}


def _hydrate(post: dict) -> dict:
    """Attach counts + viewer-specific like/bookmark state. Kept as one
    helper so every route returns posts in the exact same shape."""
    liked = g.user_id is not None and has_liked(post["id"], g.user_id)
    bookmarked = g.user_id is not None and has_bookmarked(post["id"], g.user_id)
    return post_public(
        post, liked=liked, bookmarked=bookmarked,
        likes=count_likes(post["id"]), comments=count_comments(post["id"]),
        shares=count_shares(post["id"]),
    )


# ---------------------------------------------------
# Create / Edit / Delete
# ---------------------------------------------------

@post_bp.post("")
@token_required
def create():
    data = request.get_json(silent=True) or {}
    post_type = (data.get("post_type") or "text").strip().lower()
    content = (data.get("content") or "").strip()
    media_url = (data.get("media_url") or "").strip() or None
    visibility = (data.get("visibility") or "public").strip().lower()

    if post_type not in POST_TYPES:
        return jsonify({"error": "post_type must be text, image, or video."}), 400
    if visibility not in VISIBILITY_LEVELS:
        return jsonify({"error": "visibility must be public, connections_only, or private."}), 400
    if post_type == "text" and not content:
        return jsonify({"error": "Text posts need content."}), 400
    if post_type in ("image", "video") and not media_url:
        return jsonify({"error": f"{post_type} posts need media_url (upload the file first via /api/posts/upload)."}), 400
    if len(content) > 5000:
        return jsonify({"error": "Post content must be under 5000 characters."}), 400

    post = create_post(g.user_id, post_type, content or None, media_url, visibility)
    return jsonify({"post": _hydrate(post)}), 201


@post_bp.put("/<int:post_id>")
@token_required
def edit(post_id):
    post = find_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found."}), 404
    if post["user_id"] != g.user_id:
        return jsonify({"error": "You can only edit your own posts."}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    visibility = (data.get("visibility") or post["visibility"]).strip().lower()

    if visibility not in VISIBILITY_LEVELS:
        return jsonify({"error": "visibility must be public, connections_only, or private."}), 400
    if post["post_type"] == "text" and not content:
        return jsonify({"error": "Text posts need content."}), 400
    if len(content) > 5000:
        return jsonify({"error": "Post content must be under 5000 characters."}), 400

    updated = update_post(post_id, content or post.get("content"), visibility)
    return jsonify({"post": _hydrate(updated)}), 200


@post_bp.delete("/<int:post_id>")
@token_required
def delete(post_id):
    ok = delete_post(post_id, g.user_id)
    if not ok:
        return jsonify({"error": "Post not found or not yours."}), 404
    return jsonify({"message": "Post deleted."}), 200


# ---------------------------------------------------
# Reading: single post, per-user posts, feed, explore
# ---------------------------------------------------

@post_bp.get("/<int:post_id>")
@optional_token
def get_post(post_id):
    post = find_post_by_id(post_id)
    if not post or not can_view_post(g.user_id, post):
        return jsonify({"error": "Post not found."}), 404
    return jsonify({"post": _hydrate(post)}), 200


@post_bp.get("/user/<username>")
@optional_token
def posts_by_user(username):
    author = find_by_username(username)
    if not author:
        return jsonify({"error": "User not found."}), 404
    # If the profile itself isn't visible to this viewer, none of their
    # posts are either — regardless of individual post visibility.
    if not can_view_profile(g.user_id, author):
        return jsonify({"error": "This profile is private."}), 403

    limit = min(int(request.args.get("limit", 20)), 50)
    offset = max(int(request.args.get("offset", 0)), 0)
    rows = list_posts_by_user(author["id"], limit=limit, offset=offset)
    visible = [p for p in rows if can_view_post(g.user_id, p)]
    return jsonify({"posts": [_hydrate(p) for p in visible]}), 200


@post_bp.get("/feed")
@token_required
def feed():
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = max(int(request.args.get("offset", 0)), 0)
    candidates = list_feed_candidates(g.user_id, limit=limit, offset=offset)
    visible = [p for p in candidates if can_view_post(g.user_id, p)]
    return jsonify({"feed": [_hydrate(p) for p in visible]}), 200


@post_bp.get("/explore")
@optional_token
def explore():
    """Signed-out-friendly public feed — only ever public posts, so this
    route doesn't need a per-row can_view_post check (list_public_posts
    already filters to visibility='public' at the SQL level)."""
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = max(int(request.args.get("offset", 0)), 0)
    rows = list_public_posts(limit=limit, offset=offset)
    return jsonify({"posts": [_hydrate(p) for p in rows]}), 200
