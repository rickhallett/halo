"""Tests for journalctl — store, CLI, and window caching."""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.journalctl.store import add_entry, list_entries, count_entries
from halos.journalctl.window import _content_hash, window
from halos.journalctl.cli import main as cli_main


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path."""
    return tmp_path / "test_journal.db"


@pytest.fixture
def tmp_cache(tmp_path):
    """Provide a temporary cache directory."""
    d = tmp_path / "journal-cache"
    d.mkdir()
    return d


# ── Store tests ──────────────────────────────────────────────


class TestStore:
    def test_add_entry(self, tmp_db):
        entry = add_entry("test entry", db_path=tmp_db)
        assert entry["id"] == 1
        assert entry["raw_text"] == "test entry"
        assert entry["source"] == "text"
        assert entry["tags"] == ""

    def test_add_entry_with_metadata(self, tmp_db):
        entry = add_entry(
            "feeling good",
            tags="movement,body",
            source="voice",
            mood="high",
            energy="4",
            db_path=tmp_db,
        )
        assert entry["tags"] == "movement,body"
        assert entry["source"] == "voice"
        assert entry["mood"] == "high"
        assert entry["energy"] == "4"

    def test_add_entry_strips_whitespace(self, tmp_db):
        entry = add_entry("  padded text  ", db_path=tmp_db)
        assert entry["raw_text"] == "padded text"

    def test_add_entry_empty_raises(self, tmp_db):
        with pytest.raises(ValueError, match="empty"):
            add_entry("", db_path=tmp_db)

    def test_add_entry_whitespace_only_raises(self, tmp_db):
        with pytest.raises(ValueError, match="empty"):
            add_entry("   ", db_path=tmp_db)

    def test_list_entries_default(self, tmp_db):
        add_entry("one", db_path=tmp_db)
        add_entry("two", db_path=tmp_db)
        entries = list_entries(days=7, db_path=tmp_db)
        assert len(entries) == 2
        # Newest first
        assert entries[0]["raw_text"] == "two"

    def test_list_entries_tag_filter(self, tmp_db):
        add_entry("tagged", tags="movement", db_path=tmp_db)
        add_entry("untagged", db_path=tmp_db)
        entries = list_entries(tags="movement", db_path=tmp_db)
        assert len(entries) == 1
        assert entries[0]["raw_text"] == "tagged"

    def test_list_entries_multi_tag_filter(self, tmp_db):
        add_entry("a", tags="movement,body", db_path=tmp_db)
        add_entry("b", tags="work", db_path=tmp_db)
        add_entry("c", tags="body,zen", db_path=tmp_db)
        entries = list_entries(tags="body", db_path=tmp_db)
        assert len(entries) == 2

    def test_count_entries(self, tmp_db):
        assert count_entries(db_path=tmp_db) == 0
        add_entry("one", db_path=tmp_db)
        add_entry("two", db_path=tmp_db)
        assert count_entries(db_path=tmp_db) == 2

    def test_custom_timestamp(self, tmp_db):
        entry = add_entry(
            "backdated", timestamp="2026-01-01T00:00:00Z", db_path=tmp_db
        )
        assert entry["timestamp"] == "2026-01-01T00:00:00Z"
        # Should not appear in 7-day window
        entries = list_entries(days=7, db_path=tmp_db)
        assert len(entries) == 0


# ── Window tests ─────────────────────────────────────────────


class TestWindow:
    def test_content_hash_deterministic(self):
        entries = [
            {"id": 1, "timestamp": "2026-04-01T00:00:00Z", "raw_text": "hello"},
            {"id": 2, "timestamp": "2026-04-02T00:00:00Z", "raw_text": "world"},
        ]
        assert _content_hash(entries) == _content_hash(entries)

    def test_content_hash_changes_with_content(self):
        e1 = [{"id": 1, "timestamp": "2026-04-01T00:00:00Z", "raw_text": "hello"}]
        e2 = [{"id": 1, "timestamp": "2026-04-01T00:00:00Z", "raw_text": "goodbye"}]
        assert _content_hash(e1) != _content_hash(e2)

    def test_window_empty_db(self, tmp_db, tmp_cache):
        """Window with no entries returns a 'no entries' message without calling LLM."""
        with patch("halos.journalctl.window.CACHE_DIR", tmp_cache):
            result = window(days=7, db_path=tmp_db)
        assert "no journal entries" in result.lower() or "No journal entries" in result

    def test_window_caching(self, tmp_db, tmp_cache):
        """Second call with same content returns cached summary."""
        add_entry("test entry", db_path=tmp_db)

        with patch("halos.journalctl.window.CACHE_DIR", tmp_cache), \
             patch("halos.journalctl.window._synthesise") as mock_synth:
            mock_synth.return_value = "Mocked summary of the week."

            # First call — synthesises
            result1 = window(days=7, db_path=tmp_db)
            assert mock_synth.call_count == 1
            assert result1 == "Mocked summary of the week."

            # Second call — cache hit
            result2 = window(days=7, db_path=tmp_db)
            assert mock_synth.call_count == 1  # No additional call
            assert result2 == result1

    def test_window_cache_invalidation(self, tmp_db, tmp_cache):
        """New entry invalidates cache."""
        add_entry("first", db_path=tmp_db)

        with patch("halos.journalctl.window.CACHE_DIR", tmp_cache), \
             patch("halos.journalctl.window._synthesise") as mock_synth:
            mock_synth.return_value = "Summary v1."
            window(days=7, db_path=tmp_db)
            assert mock_synth.call_count == 1

            # Add new entry — hash changes
            add_entry("second", db_path=tmp_db)
            mock_synth.return_value = "Summary v2."
            result = window(days=7, db_path=tmp_db)
            assert mock_synth.call_count == 2
            assert result == "Summary v2."

    def test_window_no_cache_flag(self, tmp_db, tmp_cache):
        """--no-cache forces regeneration."""
        add_entry("entry", db_path=tmp_db)

        with patch("halos.journalctl.window.CACHE_DIR", tmp_cache), \
             patch("halos.journalctl.window._synthesise") as mock_synth:
            mock_synth.return_value = "Summary."
            window(days=7, db_path=tmp_db)
            window(days=7, no_cache=True, db_path=tmp_db)
            assert mock_synth.call_count == 2


# ── CLI tests ────────────────────────────────────────────────


class TestCLI:
    @staticmethod
    def _patch_db(tmp_db):
        """Patch DB_PATH so CLI functions use the temp database."""
        return patch("halos.journalctl.store.DB_PATH", tmp_db)

    def test_add_via_cli(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["add", "hello", "from", "cli"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Added entry #1" in captured.out

    def test_add_empty_fails(self, capsys):
        ret = cli_main(["add"])
        assert ret == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_recent_empty(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["recent"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "No journal entries" in captured.out

    def test_stats_via_cli(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["add", "one"])
            ret = cli_main(["stats"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Total entries: 1" in captured.out

    def test_help_returns_zero(self, capsys):
        ret = cli_main([])
        assert ret == 0
