"""Tests for the halos structured log emitter."""

import json
import os
import stat
import tempfile

import pytest

from halos.logctl.parser import parse_halos_structured


class TestHlogWritesToFile:
    def test_writes_json_line_to_file(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("memctl", "info", "note_created", {"id": "20260316-abc", "title": "test"})

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["source"] == "memctl"
        assert entry["level"] == "info"
        assert entry["event"] == "note_created"
        assert entry["data"]["id"] == "20260316-abc"
        assert "ts" in entry

    def test_appends_multiple_lines(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("memctl", "info", "note_created", {"id": "1"})
        hlog("todoctl", "info", "item_created", {"id": "2"})

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2


class TestHlogFallsBackToStderr:
    def test_writes_to_stderr_when_no_file(self, monkeypatch, capsys):
        monkeypatch.setattr("halos.common.log._LOG_FILE", "")

        from halos.common.log import hlog
        hlog("memctl", "info", "note_created", {"id": "123"})

        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["event"] == "note_created"


class TestHlogHandlesOSError:
    def test_falls_back_to_stderr_on_oserror(self, tmp_path, monkeypatch, capsys):
        # Point to a read-only directory so open() fails
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        log_file = readonly_dir / "test.log"
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("memctl", "error", "boom", {"detail": "something"})

        # Restore permissions for cleanup
        readonly_dir.chmod(stat.S_IRWXU)

        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["event"] == "boom"
        assert entry["level"] == "error"


class TestHlogJsonFormat:
    def test_output_is_parseable_json_with_required_fields(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("nightctl", "warn", "job_enqueued", {"id": "abc"})

        line = log_file.read_text().strip()
        entry = json.loads(line)

        # Required fields
        assert "ts" in entry
        assert "level" in entry
        assert "source" in entry
        assert "event" in entry
        assert "data" in entry

        # Correct values
        assert entry["source"] == "nightctl"
        assert entry["level"] == "warn"
        assert entry["event"] == "job_enqueued"

    def test_no_data_key_when_data_is_none(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("cronctl", "info", "job_toggled")

        entry = json.loads(log_file.read_text().strip())
        assert "data" not in entry

    def test_timestamp_is_utc_iso_format(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("memctl", "info", "test")

        entry = json.loads(log_file.read_text().strip())
        ts = entry["ts"]
        assert ts.endswith("Z")
        assert "T" in ts


class TestLogctlCanParseHlogOutput:
    def test_logctl_parser_reads_hlog_output(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))

        from halos.common.log import hlog
        hlog("memctl", "info", "note_created", {"id": "20260316-xyz", "title": "test note"})

        line = log_file.read_text().strip()
        parsed = parse_halos_structured(line)

        assert parsed is not None
        assert parsed.source == "memctl"
        assert parsed.level == "info"
        assert parsed.message == "note_created"
        assert parsed.data["id"] == "20260316-xyz"
        assert parsed.timestamp == "2026-03-16T"[:10] or parsed.timestamp.startswith("20")
