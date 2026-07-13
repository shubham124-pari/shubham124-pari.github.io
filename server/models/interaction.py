"""
Raw parameterized-SQL data access for post interactions: likes, comments,
shares, bookmarks.
"""

from database.db import get_db_connection


# ---------------------------------------------------
# Likes
# ---------------------------------------------------

def like_post(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO post_likes (post_id, user_id) VALUES (%s, %s)",
                (post_id, user_id),
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def unlike_post(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM post_likes WHERE post_id = %s AND user_id = %s",
                (post_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def has_liked(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM post_likes WHERE post_id = %s AND user_id = %s",
                (post_id, user_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def count_likes(post_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM post_likes WHERE post_id = %s", (post_id,))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------
# Comments
# ---------------------------------------------------

def add_comment(post_id: int, user_id: int, content: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO post_comments (post_id, user_id, content) VALUES (%s, %s, %s)",
                (post_id, user_id, content),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_comment_by_id(new_id)
    finally:
        conn.close()


def find_comment_by_id(comment_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.*, u.name, u.username, u.profile_photo FROM post_comments c "
                "JOIN users u ON u.id = c.user_id WHERE c.id = %s",
                (comment_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def list_comments(post_id: int, limit: int = 100):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.*, u.name, u.username, u.profile_photo FROM post_comments c "
                "JOIN users u ON u.id = c.user_id "
                "WHERE c.post_id = %s ORDER BY c.created_at ASC LIMIT %s",
                (post_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def delete_comment(comment_id: int, user_id: int) -> bool:
    """Scoped to user_id: only the comment's author may delete it."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM post_comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def count_comments(post_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM post_comments WHERE post_id = %s", (post_id,))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------
# Shares
# ---------------------------------------------------

def share_post(post_id: int, user_id: int, comment: str = None) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO post_shares (post_id, user_id, comment) VALUES (%s, %s, %s)",
                (post_id, user_id, comment),
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def count_shares(post_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM post_shares WHERE post_id = %s", (post_id,))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------
# Bookmarks
# ---------------------------------------------------

def bookmark_post(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO post_bookmarks (post_id, user_id) VALUES (%s, %s)",
                (post_id, user_id),
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def has_bookmarked(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM post_bookmarks WHERE post_id = %s AND user_id = %s",
                (post_id, user_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def remove_bookmark(post_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM post_bookmarks WHERE post_id = %s AND user_id = %s",
                (post_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def list_bookmarks(user_id: int, limit: int = 50):
    """Bookmarks are always private to the bookmarking user — there is no
    route that lets one user list another user's bookmarks."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.id, p.user_id, p.post_type, p.content, p.media_url, p.visibility, "
                "p.created_at, u.name, u.username, u.profile_photo, b.created_at AS bookmarked_at "
                "FROM post_bookmarks b JOIN posts p ON p.id = b.post_id "
                "JOIN users u ON u.id = p.user_id "
                "WHERE b.user_id = %s ORDER BY b.created_at DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()
