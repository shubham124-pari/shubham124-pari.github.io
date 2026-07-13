"""
Raw parameterized-SQL data access for the `chatbot_history` table.
user_id is nullable — anonymous (signed-out) visitors can use the
chatbot widget too, their rows just have user_id = NULL.
"""

from database.db import get_db_connection


def create_entry(user_id, question: str, answer: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chatbot_history (user_id, question, answer) "
                "VALUES (%s, %s, %s)",
                (user_id, question, answer),
            )
            new_id = cur.lastrowid
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, question, answer, time FROM chatbot_history WHERE id = %s",
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
                "SELECT id, question, answer, time FROM chatbot_history "
                "WHERE user_id = %s ORDER BY time DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def count_total():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM chatbot_history")
            return cur.fetchone()["total"]
    finally:
        conn.close()


def count_last_days(days: int = 7):
    """Chats per calendar day for the last N days — mirrors
    models/user.py's count_signups_last_days so the admin overview
    can chart both series the same way."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DATE(time) AS day, COUNT(*) AS total "
                "FROM chatbot_history WHERE time >= NOW() - INTERVAL %s DAY "
                "GROUP BY DATE(time) ORDER BY day ASC",
                (days,),
            )
            return cur.fetchall()
    finally:
        conn.close()
