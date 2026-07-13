import pymysql
import pymysql.cursors
from config import Config


def get_db_connection():
    """Open a fresh MySQL connection.

    Using a short-lived connection per request (instead of one shared
    global connection) avoids 'MySQL server has gone away' errors and
    is safe with Flask's threaded dev server / gunicorn workers.
    Call conn.close() (or use it in a `with` block) when you're done.
    """
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
