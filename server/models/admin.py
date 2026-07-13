"""
Raw parameterized-SQL data access for admin-only operations:
user management, contact message moderation, and basic analytics.
"""

from database.db import get_db_connection


# ---------------------------------------------------
# Users
# ---------------------------------------------------

def list_all_users(limit: int = 200):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, role, is_banned, profile_photo, bio, "
                "resume, certificate, created_at FROM users "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def set_ban_status(user_id: int, is_banned: bool):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_banned = %s WHERE id = %s AND role != 'admin'",
                (1 if is_banned else 0, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_user(user_id: int):
    """Cascades to projects/chatbot_history via FK ON DELETE CASCADE.
    Refuses to delete admin accounts as a safety guard."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s AND role != 'admin'", (user_id,))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def promote_to_admin(email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE email = %s AND role != 'admin'",
                (email,),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------
# Contact messages
# ---------------------------------------------------

def list_all_messages(limit: int = 200):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, subject, message, date FROM contact_messages "
                "ORDER BY date DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def delete_message(message_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contact_messages WHERE id = %s", (message_id,))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Analytics
# ---------------------------------------------------

def get_analytics():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users")
            total_users = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM users WHERE is_banned = 1")
            banned_users = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM projects")
            total_projects = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM contact_messages")
            total_messages = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM chatbot_history")
            total_chats = cur.fetchone()["c"]

            cur.execute(
                "SELECT DATE(created_at) AS day, COUNT(*) AS c FROM users "
                "GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 14"
            )
            signups_last_14_days = cur.fetchall()

            return {
                "total_users": total_users,
                "banned_users": banned_users,
                "total_projects": total_projects,
                "total_messages": total_messages,
                "total_chats": total_chats,
                "signups_last_14_days": [
                    {"day": str(row["day"]), "count": row["c"]} for row in signups_last_14_days
                ],
            }
    finally:
        conn.close()
