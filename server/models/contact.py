"""
Raw parameterized-SQL data access for the `contact_messages` table.
"""

from database.db import get_db_connection


def create_message(name: str, email: str, subject: str, message: str, user_id=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO contact_messages (user_id, name, email, subject, message) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, name, email, subject, message),
            )
            new_id = cur.lastrowid
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, email, subject, message, status, date "
                "FROM contact_messages WHERE id = %s",
                (new_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def list_by_user(user_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, email, subject, message, status, date "
                "FROM contact_messages WHERE user_id = %s ORDER BY date DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------
# Admin
# ---------------------------------------------------

def list_all(limit: int = 200):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, email, subject, message, status, date "
                "FROM contact_messages ORDER BY date DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def set_status(message_id: int, status: str) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE contact_messages SET status = %s WHERE id = %s",
                (status, message_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_message(message_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contact_messages WHERE id = %s", (message_id,))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def count_total():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM contact_messages")
            return cur.fetchone()["total"]
    finally:
        conn.close()


def count_new():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM contact_messages WHERE status = 'new'"
            )
            return cur.fetchone()["total"]
    finally:
        conn.close()
