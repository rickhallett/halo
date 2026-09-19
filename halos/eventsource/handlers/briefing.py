"""Client briefing projection — roundtable-wide status updates."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class BriefingProjectionHandler(ProjectionHandler):
    """Handles client.briefing.published events → briefing_notes table.

    These are roundtable-wide broadcasts — every advisor projects them
    into their local read model for context during conversations.
    """

    tables = ["briefing_notes"]

    def handles(self) -> list[str]:
        return [
            "client.briefing.published",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS briefing_notes (
                source_event_id TEXT PRIMARY KEY,
                client_slug TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                classification TEXT NOT NULL DEFAULT 'roundtable',
                timestamp TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_briefing_ts "
            "ON briefing_notes(timestamp DESC)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_briefing_client "
            "ON briefing_notes(client_slug)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        db.execute(
            """
            INSERT OR IGNORE INTO briefing_notes
                (source_event_id, client_slug, title, body, classification, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                p.get("client_slug", ""),
                p.get("title", ""),
                p.get("body", ""),
                p.get("classification", "roundtable"),
                event.timestamp,
            ),
        )
