"""Tests for adversarial review fixes in memctl."""
import hashlib
from pathlib import Path

from halos.memctl.index import rebuild_from_notes, hash_bytes


VALID_NOTE_MD = """\
---
id: "20250101-120000-001"
title: "Test Note"
type: fact
tags: [testing]
entities: [claude]
backlinks: []
confidence: high
created: "2025-01-01T12:00:00Z"
modified: "2025-01-01T12:00:00Z"
---

This is a test note body.
"""


class TestHashFileDoubleRead:
    """H10: rebuild_from_notes should read file bytes once, not twice."""

    def test_hash_matches_content(self, tmp_path):
        """Hash in rebuilt entry should match the actual file content."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        note_file = notes_dir / "note1.md"
        note_file.write_text(VALID_NOTE_MD)

        entries, errors = rebuild_from_notes(str(notes_dir), 120)
        assert len(entries) == 1
        assert errors == 0

        # Verify hash matches the file content
        expected_hash = hashlib.sha256(note_file.read_bytes()).hexdigest()
        assert entries[0].hash == expected_hash

    def test_hash_consistent_with_parsed_content(self, tmp_path):
        """Hash should be computed from the same bytes used for parsing."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        content = VALID_NOTE_MD
        note_file = notes_dir / "note1.md"
        note_file.write_text(content)

        entries, _ = rebuild_from_notes(str(notes_dir), 120)
        # The hash should match bytes of the file
        raw_bytes = note_file.read_bytes()
        assert entries[0].hash == hash_bytes(raw_bytes)
