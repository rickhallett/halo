"""Frontmatter parsing and schema validation for docs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


REQUIRED_FIELDS = ("title", "category", "status", "created")

VALID_CATEGORIES = {
    "runbook", "guide", "reference", "journal", "briefing",
    "spec", "analysis", "review", "archive",
}

VALID_STATUSES = {"draft", "active", "superseded", "archived"}

# Categories expected per tier directory
TIER_CATEGORIES: dict[str, set[str]] = {
    "d1": {"runbook", "guide", "reference", "journal", "briefing"},
    "d2": {"spec", "analysis", "review"},
    "d3": {"archive"},
}

# Categories NOT expected in each tier (used for misplacement detection)
MISPLACED_IN_TIER: dict[str, set[str]] = {
    "d1": {"spec", "analysis"},
    "d2": {"runbook", "guide"},
    "d3": set(),  # anything active in d3 is a mismatch
}

_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


@dataclass
class DocMeta:
    title: str = ""
    category: str = ""
    status: str = ""
    created: str = ""
    updated: str = ""
    superseded_by: Optional[str] = None
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    effort: str = ""
    tier: str = ""


def parse_frontmatter(text: str) -> tuple[Optional[DocMeta], str]:
    """Parse YAML frontmatter from document text.

    Returns (DocMeta | None, body_text). If no frontmatter found, returns (None, text).
    """
    m = _FRONT_RE.match(text)
    if not m:
        return None, text

    try:
        raw = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text

    if not raw or not isinstance(raw, dict):
        return None, text

    meta = DocMeta(
        title=str(raw.get("title", "")),
        category=str(raw.get("category", "")),
        status=str(raw.get("status", "")),
        created=str(raw.get("created", "")),
        updated=str(raw.get("updated", "")),
        superseded_by=raw.get("superseded_by"),
        related=raw.get("related") or [],
        tags=raw.get("tags") or [],
        effort=str(raw.get("effort", "")),
        tier=str(raw.get("tier", "")),
    )
    body = text[m.end():]
    return meta, body


def marshal_frontmatter(meta: DocMeta) -> str:
    """Serialise a DocMeta back to a YAML frontmatter block."""
    data: dict = {"title": meta.title, "category": meta.category,
                  "status": meta.status, "created": meta.created}
    if meta.updated:
        data["updated"] = meta.updated
    if meta.superseded_by:
        data["superseded_by"] = meta.superseded_by
    if meta.related:
        data["related"] = meta.related
    if meta.tags:
        data["tags"] = meta.tags
    if meta.effort:
        data["effort"] = meta.effort
    if meta.tier:
        data["tier"] = meta.tier

    dumped = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return "---\n" + dumped.rstrip() + "\n---\n"


def validate_schema(meta: DocMeta) -> list[str]:
    """Return list of validation error strings for a DocMeta."""
    errors: list[str] = []
    for f in REQUIRED_FIELDS:
        if not getattr(meta, f):
            errors.append(f"missing required field: {f}")
    if meta.category and meta.category not in VALID_CATEGORIES:
        errors.append(f"invalid category: {meta.category!r} (valid: {sorted(VALID_CATEGORIES)})")
    if meta.status and meta.status not in VALID_STATUSES:
        errors.append(f"invalid status: {meta.status!r} (valid: {sorted(VALID_STATUSES)})")
    return errors


def extract_links(text: str) -> list[str]:
    """Return all relative link targets from markdown text (excludes http/https/mailto)."""
    links = []
    for _label, href in _LINK_RE.findall(text):
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # Strip anchor fragment
        href = href.split("#")[0]
        if href:
            links.append(href)
    return links


def tier_from_path(path: Path) -> Optional[str]:
    """Infer the tier (d1/d2/d3) from a file path."""
    for part in path.parts:
        if part in ("d1", "d2", "d3"):
            return part
    return None
