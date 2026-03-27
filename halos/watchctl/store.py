"""SQLite store for watchctl — seen videos, evaluations, failures, costs."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_conn: Optional[sqlite3.Connection] = None


def _get_conn(db_path: Path) -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(db_path))
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen_videos (
            video_id     TEXT PRIMARY KEY,
            channel_id   TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            title        TEXT NOT NULL,
            published    TEXT NOT NULL,
            url          TEXT NOT NULL,
            first_seen   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id     TEXT NOT NULL REFERENCES seen_videos(video_id),
            rubric_name  TEXT NOT NULL,
            rubric_ver   INTEGER NOT NULL,
            scores       TEXT NOT NULL,       -- JSON
            overall      REAL NOT NULL,
            verdict      TEXT NOT NULL,
            summary      TEXT NOT NULL,
            goodies      TEXT NOT NULL,       -- JSON
            tags         TEXT NOT NULL,       -- JSON
            model        TEXT NOT NULL,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd     REAL DEFAULT 0.0,
            evaluated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(video_id, rubric_name, rubric_ver)
        );

        CREATE TABLE IF NOT EXISTS failures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id     TEXT,
            channel_id   TEXT,
            error_type   TEXT NOT NULL,
            error_msg    TEXT NOT NULL,
            occurred_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)


def init(db_path: Path) -> None:
    """Initialise the database connection."""
    _get_conn(db_path)


def is_seen(db_path: Path, video_id: str) -> bool:
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT 1 FROM seen_videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    return row is not None


def mark_seen(db_path: Path, video_id: str, channel_id: str,
              channel_name: str, title: str, published: str, url: str) -> None:
    conn = _get_conn(db_path)
    conn.execute(
        """INSERT OR IGNORE INTO seen_videos
           (video_id, channel_id, channel_name, title, published, url)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (video_id, channel_id, channel_name, title, published, url),
    )
    conn.commit()


def save_evaluation(
    db_path: Path,
    video_id: str,
    rubric_name: str,
    rubric_ver: int,
    scores: dict,
    overall: float,
    verdict: str,
    summary: str,
    goodies: list,
    tags: list,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> int:
    conn = _get_conn(db_path)
    cur = conn.execute(
        """INSERT OR REPLACE INTO evaluations
           (video_id, rubric_name, rubric_ver, scores, overall, verdict,
            summary, goodies, tags, model, input_tokens, output_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            video_id, rubric_name, rubric_ver,
            json.dumps(scores), overall, verdict,
            summary, json.dumps(goodies), json.dumps(tags),
            model, input_tokens, output_tokens, cost_usd,
        ),
    )
    conn.commit()
    return cur.lastrowid


def log_failure(db_path: Path, error_type: str, error_msg: str,
                video_id: Optional[str] = None,
                channel_id: Optional[str] = None) -> None:
    conn = _get_conn(db_path)
    conn.execute(
        """INSERT INTO failures (video_id, channel_id, error_type, error_msg)
           VALUES (?, ?, ?, ?)""",
        (video_id, channel_id, error_type, error_msg),
    )
    conn.commit()


def recent_evaluations(db_path: Path, days: int = 7,
                       limit: int = 50) -> list[dict]:
    conn = _get_conn(db_path)
    rows = conn.execute(
        """SELECT e.*, s.title, s.channel_name, s.url, s.published
           FROM evaluations e
           JOIN seen_videos s ON e.video_id = s.video_id
           WHERE e.evaluated_at >= datetime('now', ?)
           ORDER BY e.evaluated_at DESC
           LIMIT ?""",
        (f"-{days} days", limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats(db_path: Path) -> dict:
    """Cost tracking and score distributions."""
    conn = _get_conn(db_path)

    totals = conn.execute(
        """SELECT COUNT(*) as count,
                  SUM(cost_usd) as total_cost,
                  AVG(overall) as avg_score,
                  SUM(input_tokens) as total_input,
                  SUM(output_tokens) as total_output
           FROM evaluations"""
    ).fetchone()

    verdicts = conn.execute(
        """SELECT verdict, COUNT(*) as count
           FROM evaluations GROUP BY verdict"""
    ).fetchall()

    failures = conn.execute(
        """SELECT error_type, COUNT(*) as count
           FROM failures GROUP BY error_type"""
    ).fetchall()

    return {
        "evaluations": dict(totals) if totals else {},
        "verdicts": {r["verdict"]: r["count"] for r in verdicts},
        "failures": {r["error_type"]: r["count"] for r in failures},
    }


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
