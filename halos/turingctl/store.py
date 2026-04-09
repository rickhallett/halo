"""SQLite storage for Turing drill sessions.

Two tables:
- drill_sessions: metadata, scores, drill description
- drill_turns: sanitised Q&A pairs per session

Schema is append-only. No pruning, no expiry. The corpus compounds.
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from halos.common.paths import store_dir


DB_NAME = "turing_sessions.db"
VALID_MACHINES = ("collaboration", "verification", "architecture", "recovery", "imitation")
VALID_FORMATS = ("terminal", "telegram", "diagnostic")
VALID_SCORES = ("fluent", "functional", "fragile", "foreign")


def _db_path() -> Path:
    return store_dir() / DB_NAME


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drill_sessions (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            machine TEXT NOT NULL,
            format TEXT NOT NULL,
            duration_mins INTEGER,
            drill_description TEXT NOT NULL DEFAULT '',
            scores TEXT NOT NULL DEFAULT '{}',
            session_source TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drill_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES drill_sessions(id),
            turn_number INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tools_used TEXT NOT NULL DEFAULT '[]',
            UNIQUE(session_id, turn_number)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_timestamp
        ON drill_sessions(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_machine
        ON drill_sessions(machine)
    """)
    conn.commit()
    return conn


def create_session(
    session_id: str,
    machine: str,
    fmt: str,
    drill_description: str,
    turns: list[dict],
    duration_mins: Optional[int] = None,
    scores: Optional[dict] = None,
    session_source: str = "",
    notes: str = "",
    timestamp: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Create a drill session with its conversation turns.

    Args:
        session_id: unique ID (suggest ULID or date-based)
        machine: one of VALID_MACHINES
        fmt: one of VALID_FORMATS
        drill_description: what the drill was about
        turns: list of {"role", "text", "tools_used", "turn_number"} dicts
        duration_mins: how long the drill took
        scores: dict of dimension -> score (e.g. {"control": "functional"})
        session_source: path to source JSONL or reference
        notes: Turing's post-drill observations
        timestamp: ISO 8601, defaults to now
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _connect(db_path)
    conn.execute(
        "INSERT INTO drill_sessions "
        "(id, timestamp, machine, format, duration_mins, drill_description, "
        "scores, session_source, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            timestamp,
            machine,
            fmt,
            duration_mins,
            drill_description,
            json.dumps(scores or {}),
            session_source,
            notes,
        ),
    )
    for turn in turns:
        conn.execute(
            "INSERT INTO drill_turns "
            "(session_id, turn_number, role, content, tools_used) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                turn["turn_number"],
                turn["role"],
                turn.get("text", ""),
                json.dumps(turn.get("tools_used", [])),
            ),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM drill_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row)


def list_sessions(
    machine: Optional[str] = None,
    days: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List drill sessions, newest first."""
    conn = _connect(db_path)
    query = "SELECT * FROM drill_sessions"
    params: list = []
    clauses: list[str] = []

    if machine:
        clauses.append("machine = ?")
        params.append(machine)
    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        clauses.append("timestamp >= ?")
        params.append(cutoff)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """Get a session with its turns."""
    conn = _connect(db_path)
    session = conn.execute(
        "SELECT * FROM drill_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return None

    turns = conn.execute(
        "SELECT * FROM drill_turns WHERE session_id = ? ORDER BY turn_number",
        (session_id,),
    ).fetchall()
    conn.close()

    result = dict(session)
    result["scores"] = json.loads(result["scores"])
    result["turns"] = [dict(t) for t in turns]
    for t in result["turns"]:
        t["tools_used"] = json.loads(t["tools_used"])
    return result


def session_count(db_path: Optional[Path] = None) -> int:
    conn = _connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM drill_sessions").fetchone()[0]
    conn.close()
    return count


def machine_summary(db_path: Optional[Path] = None) -> dict:
    """Count sessions per machine."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT machine, COUNT(*) as count FROM drill_sessions GROUP BY machine"
    ).fetchall()
    conn.close()
    return {r["machine"]: r["count"] for r in rows}
