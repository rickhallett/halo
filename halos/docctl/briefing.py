"""Briefing integration for docctl.

text_summary() produces a one-liner suitable for inclusion in daily briefings.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .doc import parse_frontmatter


def text_summary(docs_root: Optional[Path] = None) -> str:
    """Return a one-liner summary of the docs corpus.

    Format: "N docs, M categories, K without frontmatter"
    """
    if docs_root is None:
        # Default: look for docs/ relative to cwd
        docs_root = Path.cwd() / "docs"

    if not docs_root.exists():
        return "docs/ not found"

    md_files = [
        p for p in docs_root.rglob("*.md")
        if p.name != "INDEX.md"
    ]

    total = len(md_files)
    categories: set[str] = set()
    missing_frontmatter = 0

    for p in md_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        meta, _ = parse_frontmatter(text)
        if meta is None:
            missing_frontmatter += 1
        elif meta.category:
            categories.add(meta.category)

    return (
        f"{total} docs, {len(categories)} categories, "
        f"{missing_frontmatter} without frontmatter"
    )
