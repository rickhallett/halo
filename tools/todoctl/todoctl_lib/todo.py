"""Todo item model: parse, validate, marshal."""
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


VALID_STATUSES = ["open", "in-progress", "done", "blocked", "deferred"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S")


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


class ValidationError(Exception):
    pass


class TodoItem:
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
    def status(self) -> str:
        return self.data.get("status", "open")

    @property
    def priority(self) -> int:
        return self.data.get("priority", 3)

    @property
    def tags(self) -> list:
        return self.data.get("tags", [])

    @property
    def context(self) -> str:
        return self.data.get("context", "")

    @property
    def created(self) -> str:
        return self.data.get("created", "")

    @property
    def due(self) -> str | None:
        return self.data.get("due")

    @property
    def blocked_by(self) -> str | None:
        return self.data.get("blocked_by")

    def to_yaml(self) -> str:
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False)

    def save(self):
        if not self.file_path:
            raise RuntimeError("No file path set")
        self.file_path.write_text(self.to_yaml())

    @classmethod
    def from_file(cls, path: Path) -> "TodoItem":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(data, file_path=path)

    @classmethod
    def create(cls, items_dir: Path, title: str, priority: int = 3,
               tags: list | None = None, context: str = "",
               due: str | None = None) -> "TodoItem":
        title = title.strip()
        if not title:
            raise ValidationError("--title is required")

        item_id = _now_id()
        slug = _slugify(title)
        filename = f"{item_id}-{slug}.yaml"
        file_path = items_dir / filename

        data = {
            "id": item_id,
            "title": title,
            "status": "open",
            "priority": priority,
            "tags": tags or [],
            "context": context or "",
            "created": _now_iso(),
            "due": due,
            "blocked_by": None,
        }

        item = cls(data, file_path=file_path)
        item.save()
        return item
