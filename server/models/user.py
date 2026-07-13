"""
Raw parameterized-SQL data access for the `users` table.
(Deliberately not an ORM — keeps it simple and transparent to read/extend.)
Every query uses %s placeholders, so user input can never break out into SQL
(this is what stops SQL Injection).
"""

from database.db import get_db_connection

PUBLIC_COLUMNS = (
    "id, name, username, email, profile_photo, cover_photo, bio, resume, certificate, "
    "role, theme, profile_visibility, notify_email, notify_chat, "
    "is_banned, created_at"
)


def find_by_email(email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()
    finally:
        conn.close()


def find_by_id(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()
    finally:
        conn.close()


def create_user(name: str, email: str, password_hash: str, role: str = "user"):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password_hash, role),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_by_id(new_id)
    finally:
        conn.close()


def find_by_google_id(google_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
            return cur.fetchone()
    finally:
        conn.close()
        conn.close()


def create_google_user(name: str, email: str, google_id: str, role: str = "user"):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, email, google_id, password, role) "
                "VALUES (%s, %s, %s, NULL, %s)",
                (name, email, google_id, role),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_by_id(new_id)
    finally:
        conn.close()


def link_google_id(user_id: int, google_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, user_id))
        conn.commit()
        return find_by_id(user_id)
    finally:
        conn.close()


def update_profile(user_id: int, name: str, bio: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET name = %s, bio = %s WHERE id = %s",
                (name, bio, user_id),
            )
        conn.commit()
        return find_by_id(user_id)
    finally:
        conn.close()


# Only these columns may ever be written by update_file_field — this is a
# safety allow-list so a bug elsewhere can never turn a request into an
# arbitrary-column SQL update.
_ALLOWED_FILE_COLUMNS = {"profile_photo", "cover_photo", "resume", "certificate"}


def update_file_field(user_id: int, column: str, file_path: str):
    if column not in _ALLOWED_FILE_COLUMNS:
        raise ValueError(f"'{column}' is not an allowed file column")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {column} = %s WHERE id = %s",
                (file_path, user_id),
            )
        conn.commit()
        return find_by_id(user_id)
    finally:
        conn.close()


# Allow-list mirroring _ALLOWED_FILE_COLUMNS above, for the same reason:
# keeps update_settings from ever being turned into an arbitrary-column
# SQL update by a bug elsewhere.
_ALLOWED_SETTING_COLUMNS = {"theme", "profile_visibility", "notify_email", "notify_chat"}


def update_settings(user_id: int, **fields):
    """update_settings(user_id, theme='light', notify_chat=False) — only
    updates the keys actually passed in, and only from the allow-list."""
    updates = {k: v for k, v in fields.items() if k in _ALLOWED_SETTING_COLUMNS and v is not None}
    if not updates:
        return find_by_id(user_id)

    set_clause = ", ".join(f"{col} = %s" for col in updates)
    values = list(updates.values()) + [user_id]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
        conn.commit()
        return find_by_id(user_id)
    finally:
        conn.close()


def update_password(user_id: int, password_hash: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password = %s, reset_token = NULL, "
                "reset_token_expiry = NULL WHERE id = %s",
                (password_hash, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Password reset
# ---------------------------------------------------

def set_reset_token(email: str, token: str, expiry):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET reset_token = %s, reset_token_expiry = %s "
                "WHERE email = %s",
                (token, expiry, email),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def find_by_reset_token(token: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE reset_token = %s "
                "AND reset_token_expiry > NOW()",
                (token,),
            )
            return cur.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------
# Admin
# ---------------------------------------------------

def list_all_users(limit: int = 200):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {PUBLIC_COLUMNS} FROM users ORDER BY created_at DESC LIMIT %s",
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
                "UPDATE users SET is_banned = %s WHERE id = %s",
                (1 if is_banned else 0, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def count_users():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM users")
            return cur.fetchone()["total"] # type: ignore
    finally:
        conn.close()


def count_signups_last_days(days: int = 7):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DATE(created_at) AS day, COUNT(*) AS total "
                "FROM users WHERE created_at >= NOW() - INTERVAL %s DAY "
                "GROUP BY DATE(created_at) ORDER BY day ASC",
                (days,),
            )
            return cur.fetchall()
    finally:
        conn.close()
