"""Tests for adversarial review fixes in agentctl."""
import pytest

from halos.agentctl.ingest import _determine_status, _parse_log_field, parse_log
from halos.agentctl.alerts import detect_error_streaks
from halos.agentctl.session import Session


# ── H25: int() guards ────────────────────────────────────────────


class TestIntGuards:
    """H25: Malformed duration/exit_code/prompt_length should not crash."""

    def test_malformed_duration(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text(
            "=== Container Run Log ===\n"
            "Timestamp: 2026-03-16T09:00:00.000Z\n"
            "Group: Test\n"
            "Duration: NOT_A_NUMBER\n"
            "Exit Code: 0\n"
        )
        session = parse_log(str(log))
        assert session is not None
        assert session.duration_secs == 0

    def test_malformed_exit_code(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text(
            "=== Container Run Log ===\n"
            "Timestamp: 2026-03-16T09:00:00.000Z\n"
            "Group: Test\n"
            "Duration: 5000ms\n"
            "Exit Code: BOGUS\n"
        )
        session = parse_log(str(log))
        assert session is not None
        assert session.exit_code == 1  # default on parse failure

    def test_malformed_prompt_length(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text(
            "=== Container Run Log ===\n"
            "Timestamp: 2026-03-16T09:00:00.000Z\n"
            "Group: Test\n"
            "Duration: 5000ms\n"
            "Exit Code: 0\n"
            "Prompt length: BOGUS chars\n"
        )
        session = parse_log(str(log))
        assert session is not None
        assert session.prompt_length == 0


# ── H24: Had Streaming Output ────────────────────────────────────


class TestHadStreamingOutput:
    """H24: Timeout with streaming output should be treated as success."""

    def test_timeout_with_streaming_output_is_success(self):
        log_text = (
            "=== Container Run Log (TIMEOUT) ===\n"
            "Had Streaming Output: true\n"
        )
        status = _determine_status(137, log_text)
        assert status == "success"

    def test_timeout_without_streaming_output_is_timeout(self):
        log_text = (
            "=== Container Run Log (TIMEOUT) ===\n"
            "Had Streaming Output: false\n"
        )
        status = _determine_status(137, log_text)
        assert status == "timeout"

    def test_timeout_no_streaming_field_is_timeout(self):
        log_text = "=== Container Run Log (TIMEOUT) ===\n"
        status = _determine_status(137, log_text)
        assert status == "timeout"


# ── H23: Timeout detection precision ─────────────────────────────


class TestTimeoutDetection:
    """H23: Only detect TIMEOUT when the log starts with the exact header."""

    def test_exact_timeout_header(self):
        log_text = "=== Container Run Log (TIMEOUT) ===\nDuration: 900000ms\n"
        status = _determine_status(137, log_text)
        assert status == "timeout"

    def test_timeout_in_body_not_detected(self):
        log_text = (
            "=== Container Run Log ===\n"
            "Some line about TIMEOUT in the body\n"
        )
        status = _determine_status(1, log_text)
        # Should be "error" (exit code != 0), NOT "timeout"
        assert status == "error"

    def test_normal_log_success(self):
        log_text = "=== Container Run Log ===\nAll good\n"
        status = _determine_status(0, log_text)
        assert status == "success"


# ── Error streaks count timeouts ──────────────────────────────────


def _session(id, group="g1", status="success", started="2026-03-16T09:00:00+00:00"):
    return Session(
        id=id, group=group, started=started,
        finished="2026-03-16T09:01:00+00:00",
        duration_secs=60, exit_code=1 if status != "success" else 0,
        prompt_length=100, result_length=0,
        status=status, source="container",
    )


class TestErrorStreaksCountTimeouts:
    """Error streaks should include timeout status alongside error."""

    def test_timeout_counted_in_streak(self):
        sessions = [
            _session("s1", status="success", started="2026-03-16T09:00:00+00:00"),
            _session("s2", status="error", started="2026-03-16T09:01:00+00:00"),
            _session("s3", status="timeout", started="2026-03-16T09:02:00+00:00"),
            _session("s4", status="error", started="2026-03-16T09:03:00+00:00"),
        ]
        streaks = detect_error_streaks(sessions, streak_threshold=3)
        assert "g1" in streaks
        assert len(streaks["g1"]) == 3

    def test_timeout_only_streak(self):
        sessions = [
            _session("s1", status="success", started="2026-03-16T09:00:00+00:00"),
            _session("s2", status="timeout", started="2026-03-16T09:01:00+00:00"),
            _session("s3", status="timeout", started="2026-03-16T09:02:00+00:00"),
            _session("s4", status="timeout", started="2026-03-16T09:03:00+00:00"),
        ]
        streaks = detect_error_streaks(sessions, streak_threshold=3)
        assert "g1" in streaks
