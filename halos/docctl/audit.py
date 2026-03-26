"""Audit engine for docs/ directory governance.

Checks:
- missing frontmatter (any .md in docs/ without YAML frontmatter)
- tier mismatch (category wrong for the tier directory)
- superseded not in d3 (status:superseded file outside d3/)
- broken relative links (relative markdown links pointing to non-existent files)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .doc import (
    MISPLACED_IN_TIER,
    DocMeta,
    extract_links,
    parse_frontmatter,
    tier_from_path,
)


@dataclass
class Finding:
    issue_type: str  # missing_frontmatter | tier_mismatch | superseded_not_archived | broken_link
    file: str        # relative path from docs_root
    detail: str = ""


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)

    def by_type(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {}
        for f in self.findings:
            grouped.setdefault(f.issue_type, []).append(f)
        return grouped

    def count_by_type(self) -> dict[str, int]:
        grouped = self.by_type()
        return {k: len(v) for k, v in grouped.items()}


def run_audit(docs_root: Path, check_links: bool = True) -> AuditResult:
    """Run all audit checks under docs_root and return consolidated AuditResult."""
    result = AuditResult()

    md_files = [
        p for p in docs_root.rglob("*.md")
        if p.name != "INDEX.md"
    ]

    for md_path in sorted(md_files):
        rel = str(md_path.relative_to(docs_root.parent))
        text = md_path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)

        if meta is None:
            result.findings.append(Finding(
                issue_type="missing_frontmatter",
                file=rel,
                detail="no YAML frontmatter block found",
            ))
            # No further checks possible without frontmatter
            if check_links:
                _check_links(md_path, text, docs_root, rel, result)
            continue

        tier = tier_from_path(md_path)

        # Tier mismatch checks
        if tier and meta.category:
            wrong_cats = MISPLACED_IN_TIER.get(tier, set())
            if meta.category in wrong_cats:
                result.findings.append(Finding(
                    issue_type="tier_mismatch",
                    file=rel,
                    detail=f"category '{meta.category}' should not be in {tier}/",
                ))
            # Anything active (not superseded/archived) in d3 is a mismatch
            if tier == "d3" and meta.status not in ("superseded", "archived", ""):
                result.findings.append(Finding(
                    issue_type="tier_mismatch",
                    file=rel,
                    detail=f"status '{meta.status}' in d3/ (d3 is for superseded/archived docs)",
                ))

        # Superseded not in d3
        if meta.status == "superseded" and tier != "d3":
            result.findings.append(Finding(
                issue_type="superseded_not_archived",
                file=rel,
                detail=f"status:superseded but file is in {tier or 'unknown tier'}, not d3/",
            ))

        # Broken links
        if check_links:
            _check_links(md_path, text, docs_root, rel, result)

    return result


def _check_links(
    md_path: Path,
    text: str,
    docs_root: Path,
    rel: str,
    result: AuditResult,
) -> None:
    for href in extract_links(text):
        # Resolve relative to the file's directory
        target = (md_path.parent / href).resolve()
        if not target.exists():
            result.findings.append(Finding(
                issue_type="broken_link",
                file=rel,
                detail=f"broken link: {href}",
            ))


def infer_frontmatter(md_path: Path, docs_root: Path) -> DocMeta:
    """Infer reasonable frontmatter values for a file that has none."""
    import re
    from datetime import date

    text = md_path.read_text(encoding="utf-8", errors="replace")
    tier = tier_from_path(md_path)
    rel_path = str(md_path.relative_to(docs_root.parent))

    # Try to extract title from first H1
    title = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = md_path.stem.replace("-", " ").replace("_", " ").title()

    # Infer category from filename prefix and location
    name = md_path.stem
    if "briefings" in rel_path:
        category = "briefing"
    elif name.startswith("spec-"):
        category = "spec"
    elif name.startswith("analysis-"):
        category = "analysis"
    elif name.startswith("review"):
        category = "review"
    elif "reviews" in rel_path:
        category = "review"
    elif tier == "d1":
        category = "runbook"
    elif tier == "d2":
        category = "spec"
    elif tier == "d3":
        category = "archive"
    else:
        category = "reference"

    # Infer status
    if tier == "d3":
        status = "archived"
    else:
        status = "active"

    # Infer created date from filename date patterns
    created = str(date.today())
    date_pat = re.search(r"(\d{4}-\d{2}-\d{2})", md_path.name)
    if date_pat:
        created = date_pat.group(1)

    return DocMeta(
        title=title,
        category=category,
        status=status,
        created=created,
    )
