"""Template loading, variable parsing, and Jinja2 rendering."""
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Optional

import yaml

try:
    from jinja2 import Environment, StrictUndefined, UndefinedError
    _JINJA_AVAILABLE = True
except ImportError:
    _JINJA_AVAILABLE = False

from .doc import parse_frontmatter

# Default templates directory relative to repo root
_DEFAULT_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "docs"


def _templates_dir(override: Optional[Path] = None) -> Path:
    if override:
        return override
    return _DEFAULT_TEMPLATES_DIR


def list_templates(templates_dir: Optional[Path] = None) -> list[str]:
    """Return sorted list of template names (without .md extension)."""
    tdir = _templates_dir(templates_dir)
    if not tdir.exists():
        return []
    return sorted(p.stem for p in tdir.glob("*.md"))


def load_template(name: str, templates_dir: Optional[Path] = None) -> tuple[str, dict]:
    """Load a template file. Returns (raw_text, variable_defs).

    variable_defs is a list of dicts with keys: name, required (bool), default.
    """
    tdir = _templates_dir(templates_dir)
    path = tdir / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"template not found: {path}")
    text = path.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)
    # Parse variable definitions from frontmatter (stored under 'variables' key)
    raw_front = _raw_frontmatter(text)
    var_defs = raw_front.get("variables", []) if raw_front else []
    return text, var_defs or []


def _raw_frontmatter(text: str) -> Optional[dict]:
    """Return the raw parsed YAML frontmatter dict or None."""
    import re
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def _builtin_vars() -> dict:
    now = datetime.now()
    return {
        "today": date.today().isoformat(),
        "now": now.isoformat(timespec="seconds"),
        "year": str(now.year),
        "month": str(now.month).zfill(2),
        "day": str(now.day).zfill(2),
    }


def load_vars_file(path: Path) -> dict:
    """Load a YAML variables file."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def validate_vars(var_defs: list[dict], provided: dict) -> list[str]:
    """Check all required variables are present. Returns list of error strings."""
    errors = []
    for v in var_defs:
        name = v.get("name", "")
        required = v.get("required", False)
        default = v.get("default")
        if required and name not in provided and default is None:
            errors.append(f"required variable missing: {name}")
    return errors


def render_template(
    text: str,
    var_defs: list[dict],
    provided_vars: dict,
    templates_dir: Optional[Path] = None,
) -> str:
    """Render a Jinja2 template with provided variables.

    Strips the YAML frontmatter from the output (rendering returns body only).
    """
    if not _JINJA_AVAILABLE:
        raise RuntimeError("jinja2 is not installed - run: uv add jinja2")

    # Build merged variable context
    ctx = _builtin_vars()
    # Apply defaults from var_defs
    for v in var_defs:
        name = v.get("name", "")
        default = v.get("default")
        if name and default is not None and name not in provided_vars:
            # Render default through Jinja2 in case it uses {{ today }} etc.
            try:
                env = Environment(undefined=StrictUndefined)
                rendered_default = env.from_string(str(default)).render(**ctx)
                ctx[name] = rendered_default
            except Exception:
                ctx[name] = default
    ctx.update(provided_vars)

    # Strip the YAML frontmatter before rendering so Jinja2 only processes body
    import re
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    body = text[m.end():] if m else text

    env = Environment(undefined=StrictUndefined)
    try:
        rendered = env.from_string(body).render(**ctx)
    except UndefinedError as e:
        raise ValueError(f"template variable error: {e}") from e

    return rendered
