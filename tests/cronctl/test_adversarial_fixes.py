"""Tests for adversarial review fixes in cronctl."""
import os
from pathlib import Path

import pytest
import yaml

from halos.cronctl.cron import CronJob, ValidationError, validate_schedule


class TestAtomicWrite:
    """H1/H29: save() should use atomic write."""

    def test_save_no_tmp_leftover(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path, title="Atomic test",
            schedule="0 0 * * *", command="echo hi",
        )
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_save_writes_correct_content(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path, title="Content check",
            schedule="0 0 * * *", command="echo hi",
        )
        reloaded = CronJob.from_file(job.file_path)
        assert reloaded.title == "Content check"


class TestIdCollisionGuard:
    """H4: create() should refuse to overwrite an existing job file."""

    def test_duplicate_id_raises(self, tmp_path):
        CronJob.create(
            jobs_dir=tmp_path, title="First job",
            schedule="0 0 * * *", command="echo first",
            job_id="my-job",
        )
        with pytest.raises(ValidationError, match="already exists"):
            CronJob.create(
                jobs_dir=tmp_path, title="Second job",
                schedule="0 1 * * *", command="echo second",
                job_id="my-job",
            )


class TestCrontabPercentEscaping:
    """H5: % must be escaped as \\% in crontab lines."""

    def test_percent_escaped(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path, title="Date logger",
            schedule="0 0 * * *",
            command='date +%Y-%m-%d',
        )
        line = job.to_crontab_line("/project")
        assert "\\%" in line
        assert "+\\%Y-\\%m-\\%d" in line


class TestCrontabPathQuoting:
    """H28: cd path should be quoted for spaces."""

    def test_path_with_spaces_quoted(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path, title="Space path test",
            schedule="0 0 * * *", command="echo hi",
        )
        line = job.to_crontab_line("/path/with spaces/project")
        # shlex.quote wraps in single quotes
        assert "'/path/with spaces/project'" in line


class TestValidationOnLoad:
    """H2: from_file() should validate and reject corrupt YAML."""

    def test_missing_id_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({
            "title": "no id", "command": "echo", "schedule": "0 0 * * *",
        }))
        with pytest.raises(ValueError, match="id is required"):
            CronJob.from_file(p)

    def test_missing_title_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({
            "id": "x", "command": "echo", "schedule": "0 0 * * *",
        }))
        with pytest.raises(ValueError, match="title is required"):
            CronJob.from_file(p)

    def test_missing_command_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({
            "id": "x", "title": "T", "schedule": "0 0 * * *",
        }))
        with pytest.raises(ValueError, match="command is required"):
            CronJob.from_file(p)

    def test_missing_schedule_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({
            "id": "x", "title": "T", "command": "echo",
        }))
        with pytest.raises(ValueError, match="schedule is required"):
            CronJob.from_file(p)

    def test_valid_file_passes(self, tmp_path):
        p = tmp_path / "good.yaml"
        p.write_text(yaml.dump({
            "id": "x", "title": "Good Job",
            "schedule": "0 0 * * *", "command": "echo hi",
        }))
        job = CronJob.from_file(p)
        assert job.id == "x"


class TestLoadAllWarnings:
    """H14: _load_all_jobs should warn on stderr, not swallow silently."""

    def test_corrupt_file_warns_on_stderr(self, tmp_path, capsys):
        # Write a valid job
        CronJob.create(
            jobs_dir=tmp_path, title="Valid job",
            schedule="0 0 * * *", command="echo valid",
        )
        # Write a corrupt job
        (tmp_path / "zzz-corrupt.yaml").write_text("not: valid\nno_id: true\n")

        from halos.cronctl.cli import _load_all_jobs
        jobs = _load_all_jobs(tmp_path)
        captured = capsys.readouterr()
        assert "WARN" in captured.err
        assert len(jobs) == 1


class TestCrontabInstallAtomic:
    """H29: cmd_install crontab write should be atomic."""

    def test_install_no_tmp_leftover(self, tmp_path):
        from halos.cronctl.cli import cmd_install
        import argparse

        jobs_dir = tmp_path / "jobs"
        jobs_dir.mkdir()
        CronJob.create(
            jobs_dir=jobs_dir, title="Install test",
            schedule="0 0 * * *", command="echo test",
        )

        output_file = tmp_path / "crontab.generated"

        class FakeCfg:
            base_dir = tmp_path
            install_method = "file"

        cfg = FakeCfg()
        cfg.jobs_dir = jobs_dir
        cfg.output_file = output_file

        args = argparse.Namespace(json=False, execute=False)
        cmd_install(args, cfg)

        assert output_file.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
