"""Template composition for microHAL CLAUDE.md files."""

from pathlib import Path


def _templates_dir() -> Path:
    """Return the templates/microhal directory."""
    return Path(__file__).resolve().parents[2] / "templates" / "microhal"


def _read_template(path: Path) -> str:
    """Read a template file, returning empty string if missing."""
    if path.exists():
        return path.read_text()
    return ""


def compose_claude_md(personality: str, user_name: str) -> str:
    """Compose CLAUDE.md from base + personality + user layers.

    Layers:
      1. templates/microhal/base.md — shared instructions
      2. templates/microhal/personality/<personality>.md — tone
      3. templates/microhal/user/<user_name>.md — user-specific context

    Missing layers are silently skipped.
    """
    tdir = _templates_dir()

    base = _read_template(tdir / "base.md")
    pers = _read_template(tdir / "personality" / f"{personality}.md")
    user = _read_template(tdir / "user" / f"{user_name}.md")

    sections = [s for s in [base, pers, user] if s.strip()]
    return "\n\n".join(sections) + "\n"
