"""
Raw parameterized-SQL data access for posts.

Privacy note: this module never decides *who is allowed to see* a post —
that decision lives in routes/post.py (can_view_post), which is the single
place that combines a post's `visibility` with the viewer's relationship
to the author. Keeping that logic in one place (not scattered across every
query here) is what stops a new query from accidentally forgetting a check.
"""

from database.db import get_db_connection

POST_COLUMNS = (
    "p.id, p.user_id, p.post_type, p.content, p.media_url, p.visibility, "
    "p.is_edited, p.created_at, p.updated_at"
)


def create_post(user_id: int, post_type: str, content: str, media_url: str, visibility: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO posts (user_id, post_type, content, media_url, visibility) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, post_type, content, media_url, visibility),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_post_by_id(new_id)
    finally:
        conn.close()


def find_post_by_id(post_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {POST_COLUMNS} FROM posts p WHERE p.id = %s", (post_id,))
            return cur.fetchone()
    finally:
        conn.close()


def update_post(post_id: int, content: str, visibility: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE posts SET content = %s, visibility = %s, is_edited = 1 WHERE id = %s",
                (content, visibility, post_id),
            )
        conn.commit()
        return find_post_by_id(post_id)
    finally:
        conn.close()


def delete_post(post_id: int, user_id: int) -> bool:
    """Scoped to user_id so a route can never delete someone else's post
    just by forgetting an ownership check — the WHERE clause enforces it."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM posts WHERE id = %s AND user_id = %s", (post_id, user_id))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def list_posts_by_user(user_id: int, limit: int = 50, offset: int = 0):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {POST_COLUMNS} FROM posts p WHERE p.user_id = %s "
                "ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
                (user_id, limit, offset),
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_feed_candidates(viewer_id: int, limit: int = 50, offset: int = 0):
    """Posts from people the viewer follows OR is connected with, plus the
    viewer's own posts. This is a *candidate* set only — routes/post.py
    still runs can_view_post() on each row before returning it, so a
    visibility downgrade after the follow/connection was made is still
    respected."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {POST_COLUMNS}, u.name, u.username, u.profile_photo "
                "FROM posts p JOIN users u ON u.id = p.user_id "
                "WHERE p.user_id = %s "
                "   OR p.user_id IN (SELECT followee_id FROM follows WHERE follower_id = %s) "
                "   OR p.user_id IN ("
                "        SELECT CASE WHEN requester_id = %s THEN addressee_id ELSE requester_id END "
                "        FROM connection_requests "
                "        WHERE (requester_id = %s OR addressee_id = %s) AND status = 'accepted'"
                "     ) "
                "ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
                (viewer_id, viewer_id, viewer_id, viewer_id, viewer_id, limit, offset),
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_public_posts(limit: int = 50, offset: int = 0):
    """Used for signed-out / explore-style browsing — only ever public posts."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {POST_COLUMNS}, u.name, u.username, u.profile_photo "
                "FROM posts p JOIN users u ON u.id = p.user_id "
                "WHERE p.visibility = 'public' "
                "ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            return cur.fetchall()
    finally:
        conn.close()
