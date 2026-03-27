"""Obsidian note generator — markdown with frontmatter, tags, wikilinks."""

from datetime import datetime, timezone
from pathlib import Path

from .evaluate import Evaluation
from .feed import VideoEntry


def _stars(rating: float) -> str:
    """Convert numeric rating to star display."""
    full = int(rating)
    return "★" * full + "☆" * (5 - full)


def _slugify(text: str) -> str:
    """Create a filename-safe slug from text."""
    import re
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].strip("-")


def render_note(video: VideoEntry, evaluation: Evaluation) -> str:
    """Render a full Obsidian markdown note for a video evaluation."""

    # Frontmatter
    all_tags = ["youtube-monitor"] + evaluation.tags
    tag_str = ", ".join(f'"{t}"' for t in all_tags)

    # Score table rows
    score_rows = []
    for name, info in evaluation.scores.items():
        score_rows.append(
            f"| {name.replace('_', ' ').title()} | {info['score']}/5 | {info['note']} |"
        )
    score_table = "\n".join(score_rows)

    # Goodies by tier
    def _goodies_by_tier(tier: str) -> str:
        items = [g for g in evaluation.goodies if g.get("tier") == tier]
        if not items:
            return "_None identified._"
        return "\n".join(f"- {g['item']}" for g in items)

    # Related notes as wikilinks
    related = ""
    if evaluation.related_notes:
        related = "\n".join(f"- [[{note}]]" for note in evaluation.related_notes)
    else:
        related = "_No related notes identified._"

    pub_date = video.published.strftime("%Y-%m-%d")
    eval_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    note = f"""---
title: "{video.title}"
channel: "{video.channel_name}"
date: {pub_date}
evaluated: {eval_date}
rating: {evaluation.overall}
verdict: {evaluation.verdict}
tags: [{tag_str}]
url: "{video.url}"
video_id: "{video.video_id}"
model: "{evaluation.model}"
tokens_in: {evaluation.input_tokens}
tokens_out: {evaluation.output_tokens}
---

# {video.title}

**Channel:** {video.channel_name} | **Rating:** {_stars(evaluation.overall)} ({evaluation.overall}/5) | **Verdict:** {evaluation.verdict}
**URL:** {video.url}
**Published:** {pub_date}

## Summary

{evaluation.summary}

## Evaluation

| Criterion | Score | Note |
|-----------|-------|------|
{score_table}

## Extractable Goodies

### High Value
{_goodies_by_tier("HIGH")}

### Medium Value
{_goodies_by_tier("MEDIUM")}

### Low Value
{_goodies_by_tier("LOW")}

## Related
{related}
"""
    return note


def write_note(vault_dir: Path, video: VideoEntry, evaluation: Evaluation) -> Path:
    """Write an Obsidian note to the vault directory.

    Returns:
        Path to the written note file.
    """
    vault_dir.mkdir(parents=True, exist_ok=True)

    pub_date = video.published.strftime("%Y-%m-%d")
    slug = _slugify(video.title)
    filename = f"{pub_date}-{slug}.md"
    filepath = vault_dir / filename

    content = render_note(video, evaluation)
    filepath.write_text(content)
    return filepath
