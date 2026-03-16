import os
from pathlib import Path

import yaml


DEFAULTS = {
    "cron_dir": "./cron",
    "jobs_dir": "./cron/jobs",
    "output_file": "./cron/crontab.generated",
    "log_dir": "./logs/cron",
    "install_method": "file",
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
    def cron_dir(self) -> Path:
        return self._resolve(self._data["cron_dir"])

    @property
    def jobs_dir(self) -> Path:
        return self._resolve(self._data["jobs_dir"])

    @property
    def output_file(self) -> Path:
        return self._resolve(self._data["output_file"])

    @property
    def log_dir(self) -> Path:
        return self._resolve(self._data["log_dir"])

    @property
    def install_method(self) -> str:
        return self._data.get("install_method", "file")

    def ensure_dirs(self):
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = None) -> Config:
    if config_path:
        path = Path(config_path).resolve()
    else:
        env_path = os.environ.get("CRONCTL_CONFIG")
        if env_path:
            path = Path(env_path).resolve()
        else:
            path = Path("cronctl.yaml").resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    data = {**DEFAULTS, **raw}
    cfg = Config(data, path)
    cfg.ensure_dirs()
    return cfg
