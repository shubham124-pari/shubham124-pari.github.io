"""
Raw parameterized-SQL data access for the `projects` table.
Every query is scoped by user_id where it matters, so one user can never
read, edit, or delete another user's project through this layer.
"""

from database.db import get_db_connection


def list_by_user(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, title, description, image, github, demo, created_at "
                "FROM projects WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def find_by_id(project_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, title, description, image, github, demo, created_at "
                "FROM projects WHERE id = %s",
                (project_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def create_project(user_id: int, title: str, description: str, image: str, github: str, demo: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO projects (user_id, title, description, image, github, demo) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, title, description, image, github, demo),
            )
            new_id = cur.lastrowid
        conn.commit()
        return find_by_id(new_id)
    finally:
        conn.close()


def update_project(project_id: int, user_id: int, title: str, description: str, image: str, github: str, demo: str):
    """Scoped to (id AND user_id) so this can never edit someone else's row."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE projects SET title = %s, description = %s, image = %s, "
                "github = %s, demo = %s WHERE id = %s AND user_id = %s",
                (title, description, image, github, demo, project_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return find_by_id(project_id) if affected else None
    finally:
        conn.close()


def delete_project(project_id: int, user_id: int) -> bool:
    """Scoped to (id AND user_id) so this can never delete someone else's row."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM projects WHERE id = %s AND user_id = %s",
                (project_id, user_id),
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def count_total():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM projects")
            return cur.fetchone()["total"]
    finally:
        conn.close()


def list_all(limit: int = 50):
    """Every project across every user, newest first — used by the AI
    assistant to answer portfolio questions with real project data
    instead of guessing."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, title, description, github, demo, created_at "
                "FROM projects ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()
