"""Fleet configuration loader for halctl."""

from pathlib import Path

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml


def _resolve_source(raw: str) -> Path:
    """Expand ~ and resolve the source path."""
    return Path(raw).expanduser().resolve()


def load_fleet_config(config_path: Path | None = None) -> dict:
    """Load fleet-config.yaml, returning the parsed dict.

    Search order:
      1. Explicit path
      2. HALFLEET_CONFIG env var
      3. <repo_root>/halfleet/fleet-config.yaml
    """
    import os

    if config_path is None:
        env = os.environ.get("HALFLEET_CONFIG")
        if env:
            config_path = Path(env)
        else:
            # Walk up from this file to find the repo root
            config_path = Path(__file__).resolve().parents[2] / "halfleet" / "fleet-config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"fleet config not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Resolve source path
    if "base" in data and "source" in data["base"]:
        data["base"]["source"] = str(_resolve_source(data["base"]["source"]))

    return data


def fleet_dir(base: Path | None = None) -> Path:
    """Return the halfleet base directory."""
    if base is not None:
        return base
    return Path.home() / "code" / "halfleet"


def fleet_manifest_path(fleet_base: Path | None = None) -> Path:
    """Return path to FLEET.yaml."""
    return fleet_dir(fleet_base) / "FLEET.yaml"


def load_fleet_manifest(fleet_base: Path | None = None) -> dict:
    """Load FLEET.yaml, returning empty structure if it doesn't exist."""
    path = fleet_manifest_path(fleet_base)
    if not path.exists():
        return {"instances": []}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if "instances" not in data:
        data["instances"] = []
    return data


def save_fleet_manifest(data: dict, fleet_base: Path | None = None) -> None:
    """Atomically write FLEET.yaml."""
    import os
    import tempfile

    path = fleet_manifest_path(fleet_base)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
