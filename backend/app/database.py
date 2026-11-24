import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("lyftr.database")


def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to SQLite with row factory and thread safety."""
    db_path = settings.sqlite_db_path
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes tables and indexes automatically on startup."""
    conn = get_db_connection()
    try:
        with conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
            except Exception:
                pass
            conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);")
        logger.info(f"Database initialized successfully at {settings.sqlite_db_path}")
    finally:
        conn.close()


def save_message(session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    """
    Saves a message to SQLite.
    Metadata is stored as a JSON string (assistant messages only).
    """
    created_at = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata) if metadata is not None else None
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, meta_json, created_at)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def session_exists(session_id: str) -> bool:
    """Checks whether any messages exist for this session."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1;",
            (session_id,)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_messages_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all stored messages for a given session, ordered oldest first.
    System prompts are excluded.
    Returns list of dicts with role, content, and optional metadata.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT role, content, metadata
            FROM messages
            WHERE session_id = ? AND role != 'system'
            ORDER BY id ASC
            """,
            (session_id,)
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            meta = None
            if row["metadata"]:
                try:
                    meta = json.loads(row["metadata"])
                except Exception:
                    meta = row["metadata"]
            item = {
                "role": row["role"],
                "content": row["content"]
            }
            if meta is not None:
                item["metadata"] = meta
            results.append(item)
        return results
    finally:
        conn.close()


def check_db_health() -> bool:
    """Verifies SQLite read/write capability."""
    try:
        conn = get_db_connection()
        try:
            cursor = conn.execute("SELECT 1;")
            row = cursor.fetchone()
            return row is not None and row[0] == 1
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
