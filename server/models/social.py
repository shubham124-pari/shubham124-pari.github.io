"""
Raw parameterized-SQL data access for follows, connection requests, and
privacy-aware profile/user lookups.
"""

from database.db import get_db_connection

PROFILE_COLUMNS = (
    "id, name, username, profile_photo, bio, profile_visibility, role, created_at"
)


# ---------------------------------------------------
# Profile lookup
# ---------------------------------------------------

def find_by_username(username: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {PROFILE_COLUMNS} FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def set_username(user_id: int, username: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
        conn.commit()
    finally:
        conn.close()


def set_profile_visibility(user_id: int, visibility: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET profile_visibility = %s WHERE id = %s",
                (visibility, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def search_users(query: str, viewer_id: int, limit: int = 20):
    """Name/username search. Never exposes email or any private field —
    that's why this selects PROFILE_COLUMNS, not SELECT *."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            like = f"%{query}%"
            cur.execute(
                f"SELECT {PROFILE_COLUMNS} FROM users "
                "WHERE (name LIKE %s OR username LIKE %s) AND id != %s "
                "ORDER BY name ASC LIMIT %s",
                (like, like, viewer_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------
# Follows (one-directional, no approval)
# ---------------------------------------------------

def follow_user(follower_id: int, followee_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO follows (follower_id, followee_id) VALUES (%s, %s)",
                (follower_id, followee_id),
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def unfollow_user(follower_id: int, followee_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s",
                (follower_id, followee_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def is_following(follower_id: int, followee_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM follows WHERE follower_id = %s AND followee_id = %s",
                (follower_id, followee_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def list_followers(user_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT u.{PROFILE_COLUMNS.replace(', ', ', u.')} "
                "FROM follows f JOIN users u ON u.id = f.follower_id "
                "WHERE f.followee_id = %s ORDER BY f.created_at DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_following(user_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT u.{PROFILE_COLUMNS.replace(', ', ', u.')} "
                "FROM follows f JOIN users u ON u.id = f.followee_id "
                "WHERE f.follower_id = %s ORDER BY f.created_at DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def count_followers(user_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM follows WHERE followee_id = %s", (user_id,))
            return cur.fetchone()["total"]
    finally:
        conn.close()


def count_following(user_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM follows WHERE follower_id = %s", (user_id,))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------
# Connections (two-directional, requires accept)
# ---------------------------------------------------

def create_connection_request(requester_id: int, addressee_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO connection_requests (requester_id, addressee_id) "
                "VALUES (%s, %s)",
                (requester_id, addressee_id),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_connection_by_id(new_id)
    finally:
        conn.close()


def find_connection_between(user_a: int, user_b: int):
    """Either direction — a connection is symmetric once accepted."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM connection_requests WHERE "
                "(requester_id = %s AND addressee_id = %s) OR "
                "(requester_id = %s AND addressee_id = %s)",
                (user_a, user_b, user_b, user_a),
            )
            return cur.fetchone()
    finally:
        conn.close()


def find_connection_by_id(request_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM connection_requests WHERE id = %s", (request_id,))
            return cur.fetchone()
    finally:
        conn.close()


def respond_to_connection(request_id: int, addressee_id: int, accept: bool):
    """Only the addressee may respond — caller must check request['addressee_id']
    == the authenticated user before calling this, but we re-check here too."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE connection_requests SET status = %s, responded_at = NOW() "
                "WHERE id = %s AND addressee_id = %s AND status = 'pending'",
                ("accepted" if accept else "rejected", request_id, addressee_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def are_connected(user_a: int, user_b: int) -> bool:
    row = find_connection_between(user_a, user_b)
    return bool(row and row["status"] == "accepted")


def list_pending_requests(addressee_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cr.id, cr.created_at, "
                f"u.{PROFILE_COLUMNS.replace(', ', ', u.')} "
                "FROM connection_requests cr JOIN users u ON u.id = cr.requester_id "
                "WHERE cr.addressee_id = %s AND cr.status = 'pending' "
                "ORDER BY cr.created_at DESC LIMIT %s",
                (addressee_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_connections(user_id: int, limit: int = 100):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.name, u.username, u.profile_photo, u.bio, "
                "u.profile_visibility, u.role, u.created_at FROM connection_requests cr "
                "JOIN users u ON u.id = "
                "  CASE WHEN cr.requester_id = %s THEN cr.addressee_id ELSE cr.requester_id END "
                "WHERE (cr.requester_id = %s OR cr.addressee_id = %s) AND cr.status = 'accepted' "
                "LIMIT %s",
                (user_id, user_id, user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()
