import os
from pathlib import Path

import yaml


DEFAULTS = {
    "backlog_dir": "./backlog",
    "items_dir": "./backlog/items",
    "valid_priorities": [1, 2, 3, 4],
    "valid_tags": [],
}


class Config:
    def __init__(self, data: dict, config_path: Path):
        self._data = data
        self.config_path = config_path
        self.base_dir = config_path.parent

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return (self.base_dir / p).resolve()

    @property
    def backlog_dir(self) -> Path:
        return self._resolve(self._data["backlog_dir"])

    @property
    def items_dir(self) -> Path:
        return self._resolve(self._data["items_dir"])

    @property
    def valid_priorities(self) -> list[int]:
        return self._data.get("valid_priorities", [1, 2, 3, 4])

    @property
    def valid_tags(self) -> list[str]:
        return self._data.get("valid_tags", [])

    def ensure_dirs(self):
        self.items_dir.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = None) -> Config:
    if config_path:
        path = Path(config_path).resolve()
    else:
        env_path = os.environ.get("TODOCTL_CONFIG")
        if env_path:
            path = Path(env_path).resolve()
        else:
            path = Path("todoctl.yaml").resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    data = {**DEFAULTS, **raw}
    cfg = Config(data, path)
    cfg.ensure_dirs()
    return cfg
