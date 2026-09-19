"""Draper domain projection — interview feedback, observations, positioning decisions."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class DraperProjectionHandler(ProjectionHandler):
    """Projects draper.* events into a queryable local table.

    Covers:
    - draper.observation.* — positioning corrections, pattern discoveries
    - draper.interview.* — interview feedback, post-mortems
    - draper.decision.* — strategic positioning decisions
    """

    tables = ["draper_events"]

    def handles(self) -> list[str]:
        return [
            "draper.observation.correction",
            "draper.interview.feedback",
            "draper.decision.positioning",
            "draper.decision.storage",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS draper_events (
                source_event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                category TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'draper',
                timestamp TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_draper_type_ts "
            "ON draper_events(event_type, timestamp DESC)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_draper_category "
            "ON draper_events(category, timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        import json

        p = event.payload
        # Derive category from event type: draper.interview.feedback -> interview
        parts = event.type.split(".")
        category = parts[1] if len(parts) > 1 else "unknown"

        db.execute(
            """
            INSERT OR IGNORE INTO draper_events
                (source_event_id, event_type, category, subject, detail,
                 payload_json, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.type,
                category,
                p.get("subject", ""),
                p.get("detail", ""),
                json.dumps(p),
                event.source,
                event.timestamp,
            ),
        )
