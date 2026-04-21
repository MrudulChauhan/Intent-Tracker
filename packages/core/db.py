"""Database connection — canonical location, single source of truth.

Fixes the split-brain bug in v1 where `config.settings.DB_PATH` and
`database.db.get_db_path()` pointed at different files.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.config import settings
from core.paths import PACKAGES_DIR


DB_PATH: Path = settings.db_path
SCHEMA_PATH: Path = PACKAGES_DIR / "core" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory, WAL mode, and FK enforcement."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Read schema.sql and execute it to (idempotently) initialize the database."""
    schema_sql = SCHEMA_PATH.read_text()
    with db_connection() as conn:
        conn.executescript(schema_sql)


@contextmanager
def db_connection():
    """Context manager that yields a connection and handles commit/rollback/close."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
