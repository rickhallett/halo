"""SQLite storage layer for journal entries.

Schema mirrors trackctl's simplicity: one table, timestamped entries,
freeform text. No pruning, no scoring — permanent record.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .config import DB_PATH


def _resolve_db(db_path: Optional[Path] = None) -> Path:
    return db_path if db_path is not None else DB_PATH


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    db_path = _resolve_db(db_path)
    """Open (and initialise if needed) the journal database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'text',
            mood TEXT NOT NULL DEFAULT '',
            energy TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_timestamp
        ON entries(timestamp)
    """)
    conn.commit()
    return conn


def add_entry(
    raw_text: str,
    tags: str = "",
    source: str = "text",
    mood: str = "",
    energy: str = "",
    timestamp: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Add a journal entry. Returns the created row as a dict."""
    if not raw_text.strip():
        raise ValueError("raw_text must not be empty")

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO entries (timestamp, raw_text, tags, source, mood, energy) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp, raw_text.strip(), tags, source, mood, energy),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM entries WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(row)


def list_entries(
    days: Optional[int] = 7,
    tags: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List journal entries, newest first.

    Args:
        days: Number of days to look back. None = all entries.
        tags: Comma-separated tag filter (any match).
    """
    conn = _connect(db_path)
    query = "SELECT * FROM entries"
    params: list = []
    clauses: list[str] = []

    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        clauses.append("timestamp >= ?")
        params.append(cutoff)

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tag_clauses = []
        for tag in tag_list:
            tag_clauses.append("(',' || tags || ',' LIKE ?)")
            params.append(f"%,{tag},%")
        if tag_clauses:
            clauses.append(f"({' OR '.join(tag_clauses)})")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_entries(db_path: Optional[Path] = None) -> int:
    """Total number of journal entries."""
    conn = _connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    conn.close()
    return count
