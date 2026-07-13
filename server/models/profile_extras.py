"""
Raw parameterized-SQL data access for the expanded dashboard:
skills, education, experience, the notification center, and the
activity timeline. Kept in one module since they're all small,
single-table, per-user CRUD — same pattern as models/user.py, just
grouped together instead of one file each.
"""

from database.db import get_db_connection


# ---------------------------------------------------
# Skills
# ---------------------------------------------------

def list_skills(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, level, created_at FROM user_skills "
                "WHERE user_id = %s ORDER BY level DESC, name ASC",
                (user_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def add_skill(user_id: int, name: str, level: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_skills (user_id, name, level) VALUES (%s, %s, %s)",
                (user_id, name, level),
            )
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def update_skill(skill_id: int, user_id: int, name: str, level: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_skills SET name = %s, level = %s "
                "WHERE id = %s AND user_id = %s",
                (name, level, skill_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_skill(skill_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_skills WHERE id = %s AND user_id = %s",
                (skill_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Education
# ---------------------------------------------------

def list_education(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, school, degree, field, start_year, end_year, "
                "description, created_at FROM user_education "
                "WHERE user_id = %s ORDER BY start_year DESC",
                (user_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def add_education(user_id: int, school, degree, field, start_year, end_year, description):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_education (user_id, school, degree, field, "
                "start_year, end_year, description) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, school, degree, field, start_year, end_year, description),
            )
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def update_education(entry_id, user_id, school, degree, field, start_year, end_year, description) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_education SET school=%s, degree=%s, field=%s, "
                "start_year=%s, end_year=%s, description=%s "
                "WHERE id = %s AND user_id = %s",
                (school, degree, field, start_year, end_year, description, entry_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_education(entry_id, user_id) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_education WHERE id = %s AND user_id = %s",
                (entry_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Experience
# ---------------------------------------------------

def list_experience(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, company, role, start_date, end_date, is_current, "
                "description, created_at FROM user_experience "
                "WHERE user_id = %s ORDER BY is_current DESC, start_date DESC",
                (user_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def add_experience(user_id, company, role, start_date, end_date, is_current, description):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_experience (user_id, company, role, start_date, "
                "end_date, is_current, description) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, company, role, start_date, end_date, is_current, description),
            )
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def update_experience(entry_id, user_id, company, role, start_date, end_date, is_current, description) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_experience SET company=%s, role=%s, start_date=%s, "
                "end_date=%s, is_current=%s, description=%s "
                "WHERE id = %s AND user_id = %s",
                (company, role, start_date, end_date, is_current, description, entry_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_experience(entry_id, user_id) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_experience WHERE id = %s AND user_id = %s",
                (entry_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Notifications
# ---------------------------------------------------

def create_notification(user_id: int, type_: str, title: str, body: str = None, link: str = None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notifications (user_id, type, title, body, link) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, type_, title, body, link),
            )
        conn.commit()
    finally:
        conn.close()


def list_notifications(user_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, type, title, body, link, is_read, created_at "
                "FROM notifications WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def count_unread_notifications(user_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
            return cur.fetchone()["total"]
    finally:
        conn.close()


def mark_notification_read(notification_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
                (notification_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def mark_all_notifications_read(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------
# Activity log
# ---------------------------------------------------

def log_activity(user_id: int, action: str, meta: str = None):
    """Best-effort: a logging failure should never break the request
    that triggered it, so callers can fire-and-forget this."""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO activity_log (user_id, action, meta) VALUES (%s, %s, %s)",
                    (user_id, action, meta),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def list_activity(user_id: int, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, action, meta, created_at FROM activity_log "
                "WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()
    finally:
        conn.close()
