"""
Raw parameterized-SQL data access for private one-to-one chat:
conversations, conversation_participants, messages, plus the
is_online/last_seen presence columns on users.
"""

from database.db import get_db_connection


# ---------------------------------------------------
# Conversations
# ---------------------------------------------------

def get_or_create_direct_conversation(user_a: int, user_b: int) -> int:
    """Returns the id of the direct conversation between these two users,
    creating one if it doesn't exist yet. Order-independent."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cp1.conversation_id AS id
                FROM conversation_participants cp1
                JOIN conversation_participants cp2
                  ON cp1.conversation_id = cp2.conversation_id
                JOIN conversations c ON c.id = cp1.conversation_id
                WHERE cp1.user_id = %s AND cp2.user_id = %s AND c.type = 'direct'
                LIMIT 1
                """,
                (user_a, user_b),
            )
            row = cur.fetchone()
            if row:
                return row["id"]

            cur.execute("INSERT INTO conversations (type) VALUES ('direct')")
            conversation_id = cur.lastrowid
            cur.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) "
                "VALUES (%s, %s), (%s, %s)",
                (conversation_id, user_a, conversation_id, user_b),
            )
        conn.commit()
        return conversation_id
    finally:
        conn.close()


def is_participant(conversation_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM conversation_participants "
                "WHERE conversation_id = %s AND user_id = %s",
                (conversation_id, user_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def get_other_participant(conversation_id: int, user_id: int):
    """The other user in a direct conversation, with presence fields."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.name, u.email, u.profile_photo, u.is_online, u.last_seen
                FROM conversation_participants cp
                JOIN users u ON u.id = cp.user_id
                WHERE cp.conversation_id = %s AND cp.user_id != %s
                LIMIT 1
                """,
                (conversation_id, user_id),
            )
            return cur.fetchone()
    finally:
        conn.close()


def list_conversations_for_user(user_id: int):
    """Every conversation this user is in, with the other participant's
    info, the last message, and an unread count — everything the chat
    sidebar needs in one query per piece."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conversation_id, last_read_message_id FROM conversation_participants "
                "WHERE user_id = %s",
                (user_id,),
            )
            rows = cur.fetchall()
            results = []
            for row in rows:
                conversation_id = row["conversation_id"]
                last_read = row["last_read_message_id"] or 0

                cur.execute(
                    """
                    SELECT u.id, u.name, u.email, u.profile_photo, u.is_online, u.last_seen
                    FROM conversation_participants cp
                    JOIN users u ON u.id = cp.user_id
                    WHERE cp.conversation_id = %s AND cp.user_id != %s
                    LIMIT 1
                    """,
                    (conversation_id, user_id),
                )
                other = cur.fetchone()
                if not other:
                    continue

                cur.execute(
                    "SELECT id, conversation_id, sender_id, message_type, body, "
                    "attachment_url, attachment_name, created_at, deleted_at "
                    "FROM messages WHERE conversation_id = %s "
                    "ORDER BY id DESC LIMIT 1",
                    (conversation_id,),
                )
                last_message = cur.fetchone()

                cur.execute(
                    "SELECT COUNT(*) AS total FROM messages "
                    "WHERE conversation_id = %s AND id > %s AND sender_id != %s "
                    "AND deleted_at IS NULL",
                    (conversation_id, last_read, user_id),
                )
                unread = cur.fetchone()["total"]

                results.append(
                    {
                        "conversation_id": conversation_id,
                        "other_user": other,
                        "last_message": last_message,
                        "unread_count": unread,
                    }
                )

            results.sort(
                key=lambda r: (r["last_message"] or {}).get("created_at")
                or r["conversation_id"],
                reverse=True,
            )
            return results
    finally:
        conn.close()


def list_chat_candidates(exclude_user_id: int, search: str = "", limit: int = 30):
    """Users available to start a new conversation with (for the 'new
    chat' picker)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if search:
                cur.execute(
                    "SELECT id, name, email, profile_photo, is_online, last_seen "
                    "FROM users WHERE id != %s AND is_banned = 0 "
                    "AND (name LIKE %s OR email LIKE %s) "
                    "ORDER BY name ASC LIMIT %s",
                    (exclude_user_id, f"%{search}%", f"%{search}%", limit),
                )
            else:
                cur.execute(
                    "SELECT id, name, email, profile_photo, is_online, last_seen "
                    "FROM users WHERE id != %s AND is_banned = 0 "
                    "ORDER BY name ASC LIMIT %s",
                    (exclude_user_id, limit),
                )
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------
# Messages
# ---------------------------------------------------

def create_message(conversation_id: int, sender_id: int, message_type: str,
                    body: str = None, attachment_url: str = None, attachment_name: str = None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender_id, message_type, "
                "body, attachment_url, attachment_name) VALUES (%s, %s, %s, %s, %s, %s)",
                (conversation_id, sender_id, message_type, body, attachment_url, attachment_name),
            )
            new_id = cur.lastrowid
        conn.commit()
        return get_message(new_id)
    finally:
        conn.close()


def get_message(message_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, conversation_id, sender_id, message_type, body, "
                "attachment_url, attachment_name, created_at, deleted_at "
                "FROM messages WHERE id = %s",
                (message_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def list_messages(conversation_id: int, before_id: int = None, limit: int = 30):
    """Paginated message history, newest-first page, oldest-first once
    returned to the caller (so the UI can just append it above what's
    already rendered)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if before_id:
                cur.execute(
                    "SELECT id, conversation_id, sender_id, message_type, body, "
                    "attachment_url, attachment_name, created_at, deleted_at "
                    "FROM messages WHERE conversation_id = %s AND id < %s "
                    "ORDER BY id DESC LIMIT %s",
                    (conversation_id, before_id, limit),
                )
            else:
                cur.execute(
                    "SELECT id, conversation_id, sender_id, message_type, body, "
                    "attachment_url, attachment_name, created_at, deleted_at "
                    "FROM messages WHERE conversation_id = %s "
                    "ORDER BY id DESC LIMIT %s",
                    (conversation_id, limit),
                )
            rows = cur.fetchall()
            return list(reversed(rows))
    finally:
        conn.close()


def search_messages(user_id: int, query: str, limit: int = 50):
    """Search message bodies across every conversation this user is in."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.conversation_id, m.sender_id, m.message_type, m.body,
                       m.attachment_name, m.created_at
                FROM messages m
                JOIN conversation_participants cp
                  ON cp.conversation_id = m.conversation_id AND cp.user_id = %s
                WHERE m.deleted_at IS NULL AND m.body LIKE %s
                ORDER BY m.id DESC
                LIMIT %s
                """,
                (user_id, f"%{query}%", limit),
            )
            return cur.fetchall()
    finally:
        conn.close()


def soft_delete_message(message_id: int, user_id: int) -> bool:
    """Only the sender can delete their own message. Returns False if the
    message doesn't exist, isn't theirs, or is already deleted."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE messages SET body = NULL, attachment_url = NULL, "
                "attachment_name = NULL, deleted_at = NOW() "
                "WHERE id = %s AND sender_id = %s AND deleted_at IS NULL",
                (message_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------
# Read receipts
# ---------------------------------------------------

def mark_read(conversation_id: int, user_id: int, message_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversation_participants SET last_read_message_id = %s "
                "WHERE conversation_id = %s AND user_id = %s "
                "AND (last_read_message_id IS NULL OR last_read_message_id < %s)",
                (message_id, conversation_id, user_id, message_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_read_state(conversation_id: int):
    """user_id -> last_read_message_id for every participant — lets the
    UI show a double-tick up to the right message for each side."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, last_read_message_id FROM conversation_participants "
                "WHERE conversation_id = %s",
                (conversation_id,),
            )
            return {row["user_id"]: row["last_read_message_id"] for row in cur.fetchall()}
    finally:
        conn.close()


# ---------------------------------------------------
# Presence
# ---------------------------------------------------

def set_online_status(user_id: int, is_online: bool):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_online = %s, last_seen = NOW() WHERE id = %s",
                (1 if is_online else 0, user_id),
            )
        conn.commit()
    finally:
        conn.close()
