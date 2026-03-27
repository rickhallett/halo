"""Configuration loader for watchctl."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Channel:
    name: str
    youtube_id: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Config:
    obsidian_vault: Path
    output_dir: str
    rubric_path: Path
    db_path: Path
    model: str
    max_transcript_chars: int
    telegram_enabled: bool
    channels: list[Channel]

    @property
    def vault_output_path(self) -> Path:
        """Full path to the obsidian output directory."""
        return self.obsidian_vault / self.output_dir


def load_config(path: Optional[str] = None) -> Config:
    """Load watchctl config from YAML file.

    Searches for watchctl.yaml in:
    1. Explicit path if provided
    2. Current working directory
    3. Halo project root (alongside other *.yaml configs)
    """
    if path:
        config_path = Path(path)
    else:
        candidates = [
            Path.cwd() / "watchctl.yaml",
            Path(__file__).resolve().parents[2] / "watchctl.yaml",
        ]
        config_path = next((p for p in candidates if p.exists()), None)
        if config_path is None:
            raise FileNotFoundError(
                "watchctl.yaml not found. Looked in: "
                + ", ".join(str(p) for p in candidates)
            )

    raw = yaml.safe_load(config_path.read_text())
    project_root = config_path.parent

    channels = [
        Channel(
            name=ch["name"],
            youtube_id=ch["youtube_id"],
            tags=ch.get("tags", []),
        )
        for ch in raw.get("channels", [])
    ]

    vault_path = Path(raw["obsidian_vault"]).expanduser()

    rubric_raw = raw.get("rubric", "./rubrics/watchctl-triage.yaml")
    rubric_path = (project_root / rubric_raw).resolve()

    db_raw = raw.get("db_path", "./store/watch.db")
    db_path = (project_root / db_raw).resolve()

    return Config(
        obsidian_vault=vault_path,
        output_dir=raw.get("output_dir", "code/youtube-monitor"),
        rubric_path=rubric_path,
        db_path=db_path,
        model=raw.get("model", "claude-sonnet-4-5-20250514"),
        max_transcript_chars=raw.get("max_transcript_chars", 80000),
        telegram_enabled=raw.get("telegram_enabled", True),
        channels=channels,
    )
