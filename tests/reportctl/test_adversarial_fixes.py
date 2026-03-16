"""Tests for adversarial review fixes in reportctl."""
from pathlib import Path

import yaml

from halos.reportctl.collectors import collect_nightctl


class TestStatusVsOutcome:
    """H17: collect_nightctl should check 'outcome' not 'status' for run records."""

    def test_outcome_field_used(self, tmp_path):
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        runs_dir = queue_dir / "runs"
        runs_dir.mkdir()

        manifest = {
            "jobs": [
                {"id": "j1", "status": "done", "created": "2026-03-15T10:00:00Z"},
            ],
        }
        (queue_dir / "MANIFEST.yaml").write_text(
            yaml.dump(manifest, default_flow_style=False)
        )

        # Run record uses "outcome" field (matching executor output)
        (runs_dir / "run-j1.yaml").write_text(
            yaml.dump({"id": "j1", "outcome": "failed", "exit_code": 1})
        )

        config = tmp_path / "nightctl.yaml"
        config.write_text(yaml.dump({
            "manifest_file": str(queue_dir / "MANIFEST.yaml"),
            "runs_dir": str(runs_dir),
        }))

        result = collect_nightctl(config)
        assert result["recent_failures"] == 1

    def test_status_field_not_counted(self, tmp_path):
        """If run record uses 'status' instead of 'outcome', should NOT count as failure."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        runs_dir = queue_dir / "runs"
        runs_dir.mkdir()

        manifest = {"jobs": []}
        (queue_dir / "MANIFEST.yaml").write_text(
            yaml.dump(manifest, default_flow_style=False)
        )

        # Old-style run record with "status" field should not match
        (runs_dir / "run-j1.yaml").write_text(
            yaml.dump({"id": "j1", "status": "failed", "exit_code": 1})
        )

        config = tmp_path / "nightctl.yaml"
        config.write_text(yaml.dump({
            "manifest_file": str(queue_dir / "MANIFEST.yaml"),
            "runs_dir": str(runs_dir),
        }))

        result = collect_nightctl(config)
        assert result["recent_failures"] == 0
