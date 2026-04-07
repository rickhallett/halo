# Coding Conventions

**Analysis Date:** 2026-04-07

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python source files
- Module directories are `lowercase` single words or compound words: `memctl`, `nightctl`, `trackctl`, `backupctl`
- Each module has a standard file set: `cli.py`, `config.py`, `engine.py` (or domain-specific names like `store.py`, `item.py`, `note.py`)
- Test files follow `test_<module_or_feature>.py` pattern

**Functions:**
- Use `snake_case` for all functions and methods
- Private/internal functions prefixed with underscore: `_connect()`, `_find_repo_root()`, `_make_config()`
- CLI entry points are always `main()` in `cli.py`
- Factory/builder functions use descriptive verbs: `add_entry()`, `load_config()`, `create()`, `parse()`

**Variables:**
- Use `snake_case` for all variables
- Constants use `UPPER_SNAKE_CASE`: `VALID_KINDS`, `TERMINAL_STATUSES`, `FLEET_NS`
- Type aliases and sentinel values use `UPPER_SNAKE_CASE`

**Types/Classes:**
- Use `PascalCase` for all classes: `Item`, `Note`, `BackupConfig`, `CheckResult`
- Exception classes end with `Error`: `ValidationError`, `TransitionError`, `SaveError`, `ContainerError`, `PlanValidationError`
- Dataclass names describe the data they hold: `RetentionPolicy`, `BackupTarget`, `Event`

## Data Modelling

**Use `dataclasses` for structured data throughout:**
```python
# Simple value objects — halos/memctl/note.py
@dataclass
class Note:
    id: str = ""
    title: str = ""
    type: str = ""
    tags: list[str] = field(default_factory=list)

# Immutable event envelopes — halos/eventsource/core.py
@dataclass(frozen=True)
class Event:
    id: str
    type: str
    version: int
    payload: dict[str, Any]

# Config objects — halos/backupctl/config.py
@dataclass
class BackupConfig:
    repository: Path
    password_file: Optional[Path] = None
    targets: dict[str, BackupTarget] = field(default_factory=dict)
```

**Do NOT use Pydantic, attrs, or TypedDict.** The codebase uses stdlib `dataclasses` exclusively.

**Rich domain models use dict-backed storage with property accessors:**
```python
# halos/nightctl/item.py — Item wraps a YAML-serializable dict
class Item:
    def __init__(self, data: dict):
        self.data = data
    
    @property
    def status(self) -> str:
        return self.data.get("status", "open")
```

## Code Style

**Formatting:**
- No automated formatter configured (no black, ruff format, or autopep8)
- Follow consistent 4-space indentation
- Line length appears to be ~100-120 characters (no enforced limit)
- Use double quotes for strings consistently

**Linting:**
- No linter configured. `Makefile` has placeholder: `lint: @echo "lint: no linter configured"`
- No type checker configured. `Makefile` has placeholder: `typecheck: @echo "typecheck: no type checker configured"`
- No pre-commit hooks (`.pre-commit-config.yaml` does not exist)

**Gate rule:** `make gate` runs `test lint typecheck` but currently only `test` does real work. See `Makefile`.

## Import Organization

**Order:**
1. `__future__` imports (when present): `from __future__ import annotations`
2. Standard library: `import json`, `import os`, `from pathlib import Path`, `from datetime import datetime, timezone`
3. Third-party: `import yaml`, `import pytest`, `from rich import ...`
4. Local/project: `from halos.common.log import hlog`, `from .config import load_config`

**No import sorting tool enforced.** Follow the above order manually.

**Relative imports within a module:**
```python
# Inside halos/nightctl/cli.py
from .config import load_config
from .item import Item, ValidationError, TransitionError
```

**Absolute imports for cross-module references:**
```python
# Inside halos/nightctl/cli.py
from halos.common.log import hlog
```

**Path Aliases:**
- None. All imports use the `halos.` package prefix or relative dots.

## Error Handling

**Custom exception hierarchy per module:**
- Define module-specific exceptions inheriting from `Exception` directly
- Include structured data on exception objects for programmatic access:
```python
# halos/nightctl/item.py
class TransitionError(Exception):
    def __init__(self, current: str, attempted: str, allowed: list[str]):
        self.current = current
        self.attempted = attempted
        self.allowed = allowed
        super().__init__(f"Cannot transition from '{current}' to '{attempted}'...")
```

**CLI error handling pattern:**
```python
# Print to stderr and sys.exit(1) — never raise from CLI layer
try:
    item.transition(new_status)
except TransitionError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
```

**Validation returns error lists, not exceptions (for batch validation):**
```python
# halos/memctl/note.py
def validate(n: Note, valid_types, valid_confidence) -> list[str]:
    errs = []
    if not n.title:
        errs.append("title is required")
    return errs
```

**Validation raises exceptions (for single-item creation):**
```python
# halos/nightctl/item.py
if not data.get("title", "").strip():
    raise ValidationError("title is required")
```

Both patterns exist. Use error-list for batch operations, exceptions for single-item creation/mutation.

## Logging

**Framework:** Custom structured JSON logger at `halos/common/log.py`

**Import and usage:**
```python
from halos.common.log import hlog

hlog("nightctl", "info", "status_changed", {"id": item.id, "status": new_status})
hlog("memctl", "error", "boom", {"detail": "something"})
```

**Signature:** `hlog(source: str, level: str, event: str, data: dict | None = None)`

**Output:** One JSON line per call with fields: `ts`, `level`, `source`, `event`, `data`

**Levels:** `info`, `warn`, `error` (no `debug` level observed)

**Do NOT use Python's `logging` module.** Use `hlog` exclusively.

**Environment:** Set `HALOS_LOG_FILE` for file output; defaults to stderr.

## Comments

**Module-level docstrings are mandatory:**
```python
"""Unified work item model for nightctl.

Merges Job (execution engine) + TodoItem (state machine) into a single
model with kind-aware transition enforcement, atomic writes, and plan
validation gates.
"""
```

**Section separators use comment blocks:**
```python
# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
```

**Function docstrings use Google-style with Args/Returns/Raises sections:**
```python
def add_entry(domain: str, duration_mins: int, notes: str = "", timestamp: Optional[str] = None) -> dict:
    """Add a new entry. Returns the created row as a dict.

    Args:
        domain: Domain name (e.g. 'zazen').
        duration_mins: Duration in minutes. Must be >= 0.

    Returns:
        Dict with id, timestamp, duration_mins, notes.

    Raises:
        ValueError: If duration_mins is negative or domain is empty.
    """
```

**Inline comments are used sparingly for non-obvious logic only.**

## Function Design

**Size:** Functions are generally short (10-30 lines). Longer functions exist in CLI dispatch but are structured with early returns.

**Parameters:** Use keyword arguments with defaults. Use `Optional[T]` (or `T | None` in newer code) for nullable params. Prefer `Path` over `str` for filesystem paths.

**Return Values:**
- Return `dict` for data objects from storage layers (SQLite rows)
- Return dataclass instances for domain models
- Return `list[str]` for validation errors
- CLI `main()` functions return `int` exit codes (0 for success, 1 for error)

## Module Design

**Standard module layout:**
```
halos/<module>/
    __init__.py      # Usually empty or minimal re-exports
    cli.py           # argparse-based CLI, main() entry point
    config.py        # dataclass config + load_config() from YAML
    engine.py        # Core business logic (or domain-specific: store.py, item.py, note.py)
```

**Exports:** `__init__.py` files are typically empty (`"""halos — HAL agent operating system modules."""`). No barrel files or `__all__` declarations. Import from specific submodules directly.

**Entry points defined in `pyproject.toml`:**
```toml
[project.scripts]
memctl = "halos.memctl.cli:main"
nightctl = "halos.nightctl.cli:main"
```

**CLI pattern — argparse with subcommands:**
```python
def main(argv=None):
    parser = argparse.ArgumentParser(description="...")
    sub = parser.add_subparsers(dest="command")
    # ... add subcommands
    args = parser.parse_args(argv)
```

Accept `argv=None` parameter on `main()` to enable testability without subprocess.

## Configuration Pattern

**YAML config files at repo root:** `memctl.yaml`, `cronctl.yaml`, `backupctl.yaml`, etc.

**Config loader pattern:**
```python
def load_config(config_path: Optional[Path] = None) -> SomeConfig:
    repo_root = _find_repo_root()
    if config_path is None:
        config_path = repo_root / "module.yaml"
    if config_path.exists():
        # parse YAML
    else:
        # return sensible defaults
```

**Path resolution:** Use `halos/common/paths.py` for `store_dir()` and `repo_root()`. These respect `HALO_STORE_DIR` and `HERMES_HOME` environment variables for container deployments.

## Serialisation

**YAML for human-editable config and work items:** Use `yaml.safe_load()` / `yaml.dump()` with `default_flow_style=False, sort_keys=False`.

**JSON for structured logs and API payloads:** Use `json.dumps(entry, default=str)` to handle datetime serialisation.

**SQLite for time-series and transactional data:** Direct `sqlite3` module usage with `Row` factory. No ORM.

## Type Annotations

**Use modern Python type syntax (3.11+):**
```python
def valid_transitions(status: str, kind: str) -> list[str]: ...
tags: list[str] = field(default_factory=list)
payload: dict[str, Any]
```

**Use `from __future__ import annotations` when needed for forward references.**

**Use `Optional[T]` from `typing` (legacy code) or `T | None` (newer code) — both patterns exist. Prefer `T | None` for new code.**

---

*Convention analysis: 2026-04-07*
