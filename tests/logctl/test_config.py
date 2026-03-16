"""Tests for logctl config loading."""

import tempfile
from pathlib import Path

from halos.logctl.config import Config, load


class TestConfigDefaults:
    def test_default_values(self):
        cfg = Config()
        assert cfg.log_dir == "./logs"
        assert cfg.format == "pino"
        assert cfg.tail_lines == 50
        assert "nanoclaw" in cfg.sources

    def test_default_sources(self):
        cfg = Config()
        assert cfg.sources["nanoclaw"] == "./logs/nanoclaw.log"
        assert cfg.sources["nanoclaw_error"] == "./logs/nanoclaw.error.log"


class TestConfigLoad:
    def test_load_missing_file_returns_defaults(self):
        cfg = load("/nonexistent/logctl.yaml")
        assert cfg.log_dir == "./logs"
        assert cfg.tail_lines == 50

    def test_load_valid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("log_dir: /var/log\n")
            f.write("format: jsonl\n")
            f.write("tail_lines: 100\n")
            f.write("sources:\n")
            f.write("  app: /var/log/app.log\n")
            f.flush()
            cfg = load(f.name)
        assert cfg.log_dir == "/var/log"
        assert cfg.format == "jsonl"
        assert cfg.tail_lines == 100
        assert cfg.sources["app"] == "/var/log/app.log"
        Path(f.name).unlink()

    def test_load_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            cfg = load(f.name)
        assert cfg.log_dir == "./logs"
        Path(f.name).unlink()

    def test_load_partial_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("tail_lines: 200\n")
            f.flush()
            cfg = load(f.name)
        assert cfg.tail_lines == 200
        assert cfg.format == "pino"  # default
        Path(f.name).unlink()
