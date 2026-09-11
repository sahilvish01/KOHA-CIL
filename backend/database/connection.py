"""
KOHA-CIL — Database Connection Manager
Provides thread-safe SQLite connections with WAL mode enabled.
"""
import sqlite3
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Thread-local storage so each thread gets its own connection
_local = threading.local()


def get_db_path() -> str:
    """Resolve database path from environment or default."""
    path = os.getenv("DATABASE_PATH", str(Path(__file__).parents[2] / ".." / "data" / "koha_cil.db"))
    return os.path.abspath(path)


def _open_connection(db_path: str) -> sqlite3.Connection:
    """Open a new SQLite connection configured for production use."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating one if needed."""
    db_path = get_db_path()
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _open_connection(db_path)
    return _local.conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a database connection.
    
    Commits on clean exit; rolls back on exception.
    Does NOT close the connection (connections are thread-local and reused).
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    """Initialize the database by running schema.sql if tables do not exist."""
    db_path = get_db_path()
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(__file__).parent / "schema.sql"
    conn = _open_connection(db_path)
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
    
    # Now set the thread-local connection to the initialized DB
    _local.conn = _open_connection(db_path)


def close_connection() -> None:
    """Close the thread-local connection if open."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
