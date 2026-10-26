"""Database access helpers shared by every route."""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_transaction():
    """Open a connection, commit if the block succeeds, roll back if it raises, always close.

    Usage:
        with db_transaction() as conn:
            conn.execute(...)
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
