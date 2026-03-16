"""Tests for logctl log line parsers."""

from halos.logctl.parser import (
    LogEntry,
    format_entry,
    parse_halos_structured,
    parse_line,
    parse_pino_json,
    parse_pino_pretty,
    parse_plain,
    strip_ansi,
)


class TestStripAnsi:
    def test_removes_color_codes(self):
        raw = "\x1b[32mINFO\x1b[39m"
        assert strip_ansi(raw) == "INFO"

    def test_noop_on_clean_text(self):
        assert strip_ansi("hello world") == "hello world"


class TestPinoPretty:
    def test_parse_basic_line(self):
        line = "[16:03:37.233] INFO (30081): Database initialized"
        entry = parse_pino_pretty(line)
        assert entry is not None
        assert entry.timestamp == "16:03:37.233"
        assert entry.level == "info"
        assert entry.message == "Database initialized"
        assert entry.data["pid"] == 30081

    def test_parse_with_ansi(self):
        line = "[16:03:37.233] \x1b[32mINFO\x1b[39m (30081): \x1b[36mDatabase initialized\x1b[39m"
        entry = parse_pino_pretty(line)
        assert entry is not None
        assert entry.level == "info"
        assert entry.message == "Database initialized"

    def test_parse_warn_level(self):
        line = "[10:00:00.000] WARN (1234): something sketchy"
        entry = parse_pino_pretty(line)
        assert entry is not None
        assert entry.level == "warn"

    def test_returns_none_for_non_pino(self):
        assert parse_pino_pretty("just some text") is None

    def test_returns_none_for_empty(self):
        assert parse_pino_pretty("") is None

    def test_returns_none_for_continuation_line(self):
        line = "    groupCount: 1"
        assert parse_pino_pretty(line) is None


class TestPinoJson:
    def test_parse_json_line(self):
        line = '{"level":30,"time":1710000000000,"msg":"hello","pid":123}'
        entry = parse_pino_json(line)
        assert entry is not None
        assert entry.level == "info"
        assert entry.message == "hello"

    def test_parse_error_level(self):
        line = '{"level":50,"time":1710000000000,"msg":"oh no","pid":1}'
        entry = parse_pino_json(line)
        assert entry is not None
        assert entry.level == "error"

    def test_returns_none_for_non_json(self):
        assert parse_pino_json("not json") is None

    def test_returns_none_for_unrelated_json(self):
        assert parse_pino_json('{"foo": "bar"}') is None


class TestHalosStructured:
    def test_parse_json_halos(self):
        line = '{"ts": "2026-03-16T09:00:00Z", "level": "info", "source": "memctl", "event": "note_created", "data": {"id": "123"}}'
        entry = parse_halos_structured(line)
        assert entry is not None
        assert entry.source == "memctl"
        assert entry.message == "note_created"
        assert entry.level == "info"
        assert entry.data == {"id": "123"}

    def test_returns_none_for_non_structured(self):
        assert parse_halos_structured("just text") is None

    def test_returns_none_for_empty(self):
        assert parse_halos_structured("") is None
        assert parse_halos_structured("   ") is None


class TestParsePlain:
    def test_wraps_raw_text(self):
        entry = parse_plain("some log message")
        assert entry is not None
        assert entry.message == "some log message"

    def test_returns_none_for_empty(self):
        assert parse_plain("") is None
        assert parse_plain("   ") is None


class TestParseLine:
    def test_pino_format_prefers_pretty(self):
        line = "[16:03:37.233] INFO (30081): hello"
        entry = parse_line(line, fmt="pino")
        assert entry is not None
        assert entry.timestamp == "16:03:37.233"

    def test_pino_format_falls_back_to_json(self):
        line = '{"level":30,"time":1710000000000,"msg":"hello","pid":1}'
        entry = parse_line(line, fmt="pino")
        assert entry is not None
        assert entry.message == "hello"

    def test_plain_fallback(self):
        entry = parse_line("just text", fmt="pino")
        assert entry is not None
        assert entry.message == "just text"

    def test_malformed_graceful(self):
        # Should not raise, should return a plain entry
        entry = parse_line("{malformed json", fmt="jsonl")
        assert entry is not None


class TestFormatEntry:
    def test_full_entry(self):
        e = LogEntry(timestamp="10:00:00.000", level="error", source="memctl", message="boom")
        result = format_entry(e)
        assert "[10:00:00.000]" in result
        assert "ERROR" in result
        assert "(memctl)" in result
        assert "boom" in result

    def test_minimal_entry(self):
        e = LogEntry(message="hello")
        result = format_entry(e)
        assert "hello" in result
        assert "INFO" in result
