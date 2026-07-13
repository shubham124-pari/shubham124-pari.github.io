from flask import Blueprint, request, jsonify, g

from models.post import find_post_by_id
from models.interaction import (
    like_post, unlike_post, add_comment, list_comments, delete_comment,
    share_post, bookmark_post, remove_bookmark, list_bookmarks,
)
from utils.security import token_required, optional_token
from utils.privacy import can_view_post
from utils.serializers import comment_public, post_public

interaction_bp = Blueprint("interaction", __name__, url_prefix="/api/posts")


def _get_visible_post_or_404(post_id, viewer_id):
    """Shared guard: every interaction (like/comment/share/bookmark)
    requires the post to actually be visible to the acting user first —
    otherwise a private post's existence/content could be probed just by
    trying to like or comment on guessed IDs."""
    post = find_post_by_id(post_id)
    if not post or not can_view_post(viewer_id, post):
        return None
    return post


# ---------------------------------------------------
# Likes
# ---------------------------------------------------

@interaction_bp.post("/<int:post_id>/like")
@token_required
def like(post_id):
    if not _get_visible_post_or_404(post_id, g.user_id):
        return jsonify({"error": "Post not found."}), 404
    like_post(post_id, g.user_id)
    return jsonify({"liked": True}), 200


@interaction_bp.delete("/<int:post_id>/like")
@token_required
def unlike(post_id):
    unlike_post(post_id, g.user_id)
    return jsonify({"liked": False}), 200


# ---------------------------------------------------
# Comments
# ---------------------------------------------------

@interaction_bp.post("/<int:post_id>/comments")
@token_required
def comment(post_id):
    if not _get_visible_post_or_404(post_id, g.user_id):
        return jsonify({"error": "Post not found."}), 404

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Comment can't be empty."}), 400
    if len(content) > 1000:
        return jsonify({"error": "Comment must be under 1000 characters."}), 400

    created = add_comment(post_id, g.user_id, content)
    return jsonify({"comment": comment_public(created)}), 201


@interaction_bp.get("/<int:post_id>/comments")
@optional_token
def get_comments(post_id):
    post = _get_visible_post_or_404(post_id, g.user_id)
    if not post:
        return jsonify({"error": "Post not found."}), 404
    rows = list_comments(post_id)
    return jsonify({"comments": [comment_public(c) for c in rows]}), 200


@interaction_bp.delete("/comments/<int:comment_id>")
@token_required
def remove_comment(comment_id):
    ok = delete_comment(comment_id, g.user_id)
    if not ok:
        return jsonify({"error": "Comment not found or not yours."}), 404
    return jsonify({"message": "Comment deleted."}), 200


# ---------------------------------------------------
# Shares
# ---------------------------------------------------

@interaction_bp.post("/<int:post_id>/share")
@token_required
def share(post_id):
    if not _get_visible_post_or_404(post_id, g.user_id):
        return jsonify({"error": "Post not found."}), 404

    data = request.get_json(silent=True) or {}
    note = (data.get("comment") or "").strip() or None
    if note and len(note) > 500:
        return jsonify({"error": "Share comment must be under 500 characters."}), 400

    shared = share_post(post_id, g.user_id, note)
    if not shared:
        return jsonify({"error": "You already shared this post."}), 409
    return jsonify({"message": "Shared."}), 201


# ---------------------------------------------------
# Bookmarks — always private to the bookmarking user
# ---------------------------------------------------

@interaction_bp.post("/<int:post_id>/bookmark")
@token_required
def bookmark(post_id):
    if not _get_visible_post_or_404(post_id, g.user_id):
        return jsonify({"error": "Post not found."}), 404
    bookmark_post(post_id, g.user_id)
    return jsonify({"bookmarked": True}), 200


@interaction_bp.delete("/<int:post_id>/bookmark")
@token_required
def unbookmark(post_id):
    remove_bookmark(post_id, g.user_id)
    return jsonify({"bookmarked": False}), 200


@interaction_bp.get("/bookmarks")
@token_required
def my_bookmarks():
    rows = list_bookmarks(g.user_id)
    return jsonify({"bookmarks": [post_public(p) for p in rows]}), 200
