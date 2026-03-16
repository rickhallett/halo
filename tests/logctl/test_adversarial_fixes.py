"""Tests for adversarial review fixes in logctl."""
import tempfile
from pathlib import Path

from halos.logctl.search import read_log_file, read_log_tail


class TestStreamingRead:
    """C4: read_log_file and read_log_tail should use streaming I/O."""

    def test_read_log_file_streaming(self, tmp_path):
        """read_log_file should work correctly with streaming approach."""
        log = tmp_path / "test.log"
        lines = [f"[10:00:{i:02d}.000] INFO (1): line {i}" for i in range(20)]
        log.write_text("\n".join(lines) + "\n")
        entries = read_log_file(str(log), fmt="pino")
        assert len(entries) == 20

    def test_read_log_tail_streaming(self, tmp_path):
        """read_log_tail should return last N lines without loading entire file."""
        log = tmp_path / "test.log"
        lines = [f"[10:00:{i:02d}.000] INFO (1): line {i}" for i in range(100)]
        log.write_text("\n".join(lines) + "\n")
        entries = read_log_tail(str(log), n=5, fmt="pino")
        assert len(entries) == 5
        assert "line 99" in entries[-1].message

    def test_read_log_file_encoding_errors(self, tmp_path):
        """Should handle encoding errors gracefully with errors='replace'."""
        log = tmp_path / "test.log"
        # Write bytes with invalid UTF-8
        log.write_bytes(b"[10:00:00.000] INFO (1): good line\n"
                       b"[10:00:01.000] INFO (1): bad \xff\xfe bytes\n")
        entries = read_log_file(str(log), fmt="pino")
        assert len(entries) == 2

    def test_read_log_file_permission_error(self, tmp_path, capsys):
        """Should return empty list and warn on permission error."""
        log = tmp_path / "test.log"
        log.write_text("[10:00:00.000] INFO (1): test\n")
        log.chmod(0o000)
        try:
            entries = read_log_file(str(log), fmt="pino")
            assert entries == []
            captured = capsys.readouterr()
            assert "WARN" in captured.err
        finally:
            log.chmod(0o644)

    def test_read_log_tail_permission_error(self, tmp_path, capsys):
        """Should return empty list and warn on permission error."""
        log = tmp_path / "test.log"
        log.write_text("[10:00:00.000] INFO (1): test\n")
        log.chmod(0o000)
        try:
            entries = read_log_tail(str(log), n=5, fmt="pino")
            assert entries == []
            captured = capsys.readouterr()
            assert "WARN" in captured.err
        finally:
            log.chmod(0o644)

    def test_read_log_file_nonexistent(self):
        entries = read_log_file("/nonexistent/file.log")
        assert entries == []

    def test_read_log_tail_nonexistent(self):
        entries = read_log_tail("/nonexistent/file.log")
        assert entries == []
