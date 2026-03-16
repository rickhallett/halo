"""Cron job model: parse, validate, marshal."""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml


VALID_FIELDS = {"id", "title", "schedule", "command", "enabled", "tags", "created"}
SCHEDULE_REGEX = re.compile(
    r"^("
    r"(\*|[0-9]+(/[0-9]+)?)\s+"   # minute
    r"(\*|[0-9]+(/[0-9]+)?)\s+"   # hour
    r"(\*|[0-9]+(/[0-9]+)?)\s+"   # day of month
    r"(\*|[0-9]+(/[0-9]+)?)\s+"   # month
    r"(\*|[0-9]+(/[0-9]+)?)"      # day of week
    r")$"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


class ValidationError(Exception):
    pass


class CronJob:
    def __init__(self, data: dict, file_path: Path | None = None):
        self.data = data
        self.file_path = file_path

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def title(self) -> str:
        return self.data["title"]

    @property
    def schedule(self) -> str:
        return self.data["schedule"]

    @property
    def command(self) -> str:
        return self.data["command"]

    @property
    def enabled(self) -> bool:
        return self.data.get("enabled", True)

    @property
    def tags(self) -> list:
        return self.data.get("tags", [])

    @property
    def created(self) -> str:
        return self.data.get("created", "")

    def to_yaml(self) -> str:
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False)

    def save(self):
        if not self.file_path:
            raise RuntimeError("No file path set")
        self.file_path.write_text(self.to_yaml())

    @classmethod
    def from_file(cls, path: Path) -> "CronJob":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(data, file_path=path)

    @classmethod
    def create(cls, jobs_dir: Path, title: str, schedule: str, command: str,
               enabled: bool = True, tags: list | None = None,
               job_id: str | None = None) -> "CronJob":
        title = title.strip()
        command = command.strip()

        if not title:
            raise ValidationError("--title is required")
        if not command:
            raise ValidationError("--command is required")
        if not schedule.strip():
            raise ValidationError("--schedule is required")

        validate_schedule(schedule)

        if job_id is None:
            job_id = _slugify(title)

        slug = _slugify(title)
        filename = f"{job_id}.yaml"
        file_path = jobs_dir / filename

        data = {
            "id": job_id,
            "title": title,
            "schedule": schedule,
            "command": command,
            "enabled": enabled,
            "tags": tags or [],
            "created": _now_iso(),
        }

        job = cls(data, file_path=file_path)
        job.save()
        return job

    def to_crontab_line(self, project_root: str) -> str:
        """Generate a crontab line for this job."""
        cmd = self.command
        if not cmd.startswith("/"):
            cmd = f"cd {project_root} && {cmd}"
        return f"{self.schedule}  {cmd}"


def validate_schedule(schedule: str):
    """Validate a cron schedule expression."""
    parts = schedule.strip().split()
    if len(parts) != 5:
        raise ValidationError(
            f"Invalid schedule '{schedule}': expected 5 fields (minute hour dom month dow)"
        )
    for i, part in enumerate(parts):
        if not re.match(r"^(\*|\*/[0-9]+|[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*)$", part):
            raise ValidationError(
                f"Invalid schedule field '{part}' at position {i} in '{schedule}'"
            )
