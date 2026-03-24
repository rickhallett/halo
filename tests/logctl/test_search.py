"""Tests for logctl search and filter logic."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from halos.logctl.parser import LogEntry
from halos.logctl.search import (
    compute_stats,
    filter_entries,
    matches_level,
    matches_since,
    matches_source,
    matches_text,
    parse_duration,
    read_log_file,
    read_log_tail,
)


class TestMatchesLevel:
    def test_matches_exact(self):
        e = LogEntry(level="error", message="x")
        assert matches_level(e, "error")

    def test_case_insensitive(self):
        e = LogEntry(level="error", message="x")
        assert matches_level(e, "ERROR")

    def test_no_filter(self):
        e = LogEntry(level="info", message="x")
        assert matches_level(e, None)
        assert matches_level(e, "")

    def test_mismatch(self):
        e = LogEntry(level="info", message="x")
        assert not matches_level(e, "error")


class TestMatchesSource:
    def test_matches(self):
        e = LogEntry(source="memctl", message="x")
        assert matches_source(e, "memctl")

    def test_case_insensitive(self):
        e = LogEntry(source="memctl", message="x")
        assert matches_source(e, "MEMCTL")

    def test_no_filter(self):
        e = LogEntry(source="memctl", message="x")
        assert matches_source(e, None)
        assert matches_source(e, "")

    def test_mismatch(self):
        e = LogEntry(source="memctl", message="x")
        assert not matches_source(e, "nightctl")


class TestMatchesText:
    def test_matches_message(self):
        e = LogEntry(message="Database initialized")
        assert matches_text(e, "database")

    def test_matches_data_values(self):
        e = LogEntry(message="started", data={"port": "3001"})
        assert matches_text(e, "3001")

    def test_no_filter(self):
        e = LogEntry(message="x")
        assert matches_text(e, None)
        assert matches_text(e, "")

    def test_mismatch(self):
        e = LogEntry(message="hello")
        assert not matches_text(e, "goodbye")


class TestParseDuration:
    def test_hours(self):
        d = parse_duration("1h")
        assert d == timedelta(hours=1)

    def test_days(self):
        d = parse_duration("7d")
        assert d == timedelta(days=7)

    def test_minutes(self):
        d = parse_duration("30m")
        assert d == timedelta(minutes=30)

    def test_invalid(self):
        assert parse_duration("abc") is None
        assert parse_duration("") is None

    def test_with_spaces(self):
        d = parse_duration(" 24h ")
        assert d == timedelta(hours=24)


class TestMatchesSince:
    def test_within_window(self):
        now = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
        e = LogEntry(timestamp="11:30:00.000", message="x")
        assert matches_since(e, "1h", now=now)

    def test_outside_window(self):
        now = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
        e = LogEntry(timestamp="10:00:00.000", message="x")
        assert not matches_since(e, "1h", now=now)

    def test_iso_timestamp(self):
        now = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
        e = LogEntry(timestamp="2026-03-16T11:30:00Z", message="x")
        assert matches_since(e, "1h", now=now)

    def test_no_filter(self):
        e = LogEntry(timestamp="10:00:00.000", message="x")
        assert matches_since(e, None)
        assert matches_since(e, "")

    def test_no_timestamp_included(self):
        e = LogEntry(message="x")
        assert matches_since(e, "1h")


class TestFilterEntries:
    def test_combined_filters(self):
        entries = [
            LogEntry(level="error", source="memctl", message="bad thing"),
            LogEntry(level="info", source="memctl", message="good thing"),
            LogEntry(level="error", source="nightctl", message="other error"),
        ]
        result = filter_entries(entries, level="error", source="memctl")
        assert len(result) == 1
        assert result[0].message == "bad thing"

    def test_no_filters(self):
        entries = [LogEntry(message="a"), LogEntry(message="b")]
        assert len(filter_entries(entries)) == 2

    def test_text_filter(self):
        entries = [
            LogEntry(message="Database initialized"),
            LogEntry(message="Scheduler started"),
        ]
        result = filter_entries(entries, text="database")
        assert len(result) == 1


class TestReadLogFile:
    def test_read_pino_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("[10:00:00.000] INFO (1): line one\n")
            f.write("[10:00:01.000] WARN (1): line two\n")
            f.write("[10:00:02.000] ERROR (1): line three\n")
            f.flush()
            entries = read_log_file(f.name, fmt="pino")
        assert len(entries) == 3
        assert entries[2].level == "error"
        Path(f.name).unlink()

    def test_read_nonexistent_file(self):
        entries = read_log_file("/nonexistent/file.log")
        assert entries == []


class TestReadLogTail:
    def test_tail_limits_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            for i in range(100):
                f.write(f"[10:00:{i:02d}.000] INFO (1): line {i}\n")
            f.flush()
            entries = read_log_tail(f.name, n=5, fmt="pino")
        assert len(entries) == 5
        assert "line 99" in entries[-1].message
        Path(f.name).unlink()


class TestComputeStats:
    def test_basic_stats(self):
        entries = [
            LogEntry(level="info", source="halo", message="a"),
            LogEntry(level="info", source="halo", message="b"),
            LogEntry(level="error", source="memctl", message="c"),
            LogEntry(level="warn", source="memctl", message="d"),
        ]
        stats = compute_stats(entries)
        assert stats["total"] == 4
        assert stats["by_source"]["halo"] == 2
        assert stats["by_source"]["memctl"] == 2
        assert stats["by_level"]["info"] == 2
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 25.0

    def test_empty_entries(self):
        stats = compute_stats([])
        assert stats["total"] == 0
        assert stats["error_rate"] == 0.0
