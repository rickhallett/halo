"""Sliding window summaries — LLM-synthesised, content-hash cached.

The window command produces a narrative summary of recent journal entries.
Designed for injection into advisor context. Cached by content hash so
multiple readers (advisors, briefings) pay zero LLM cost after the first.
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional

from .config import CACHE_DIR, DEFAULT_WINDOW_DAYS, DEFAULT_MONTH_DAYS, DB_PATH
from .store import list_entries


WINDOW_SYSTEM = """\
You are summarising a personal journal for context injection into an advisory system.
The journal owner is Kai. Produce a concise narrative summary.

Guidelines:
- Write in third person ("Kai has been...", "This week saw...")
- Structure: what happened, what's in progress, what might be coming
- Surface: plan-vs-actuality drift, recurring themes, mood/energy trends
- Note: discrepancies between stated intentions and actual behaviour
- Flag: patterns that suggest habitual avoidance, compulsion, or attachment
- Be honest. If the entries show procrastination or avoidance, say so plainly.
- If entries are sparse, say so — that itself is signal.
- Output ONLY the summary. No preamble, no meta-commentary.
- Aim for 200-400 words. Dense, not padded.
"""


def _content_hash(entries: list[dict]) -> str:
    """SHA-256 of entry IDs + timestamps + text."""
    h = hashlib.sha256()
    for e in entries:
        h.update(f"{e['id']}:{e['timestamp']}:{e['raw_text']}".encode())
    return h.hexdigest()


def _cache_paths(label: str) -> tuple[Path, Path]:
    """Return (summary_path, hash_path) for a cache label."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return (
        CACHE_DIR / f"{label}.md",
        CACHE_DIR / f"{label}.hash",
    )


def _read_cache(label: str) -> tuple[Optional[str], Optional[str]]:
    """Read cached summary and hash. Returns (summary, hash) or (None, None)."""
    summary_path, hash_path = _cache_paths(label)
    if summary_path.exists() and hash_path.exists():
        return summary_path.read_text(), hash_path.read_text().strip()
    return None, None


def _write_cache(label: str, summary: str, content_hash: str) -> None:
    """Write summary and hash to cache."""
    summary_path, hash_path = _cache_paths(label)
    summary_path.write_text(summary)
    hash_path.write_text(content_hash + "\n")


def _synthesise(entries: list[dict], days: int) -> Optional[str]:
    """Call Claude CLI to synthesise a window summary."""
    if not entries:
        return f"No journal entries in the last {days} days. Silence is data."

    entry_lines = []
    for e in entries:
        parts = [f"[{e['timestamp']}]"]
        if e.get("tags"):
            parts.append(f"({e['tags']})")
        if e.get("mood"):
            parts.append(f"mood:{e['mood']}")
        if e.get("energy"):
            parts.append(f"energy:{e['energy']}")
        parts.append(e["raw_text"])
        entry_lines.append(" ".join(parts))

    prompt = (
        f"Summarise these journal entries from the last {days} days.\n\n"
        + "\n\n".join(entry_lines)
    )
    full_prompt = f"{WINDOW_SYSTEM}\n\n{prompt}"

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--model", "sonnet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr:
            print(f"WARNING: claude CLI: {result.stderr.strip()[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print("WARNING: window synthesis timed out", flush=True)
    except FileNotFoundError:
        print("WARNING: claude CLI not found", flush=True)
    return None


def window(
    days: int = DEFAULT_WINDOW_DAYS,
    no_cache: bool = False,
    db_path: Optional[Path] = None,
) -> str:
    """Produce a sliding window summary.

    Returns cached summary if content hasn't changed.
    Synthesises and caches a new one otherwise.
    """
    if db_path is None:
        db_path = DB_PATH
    entries = list_entries(days=days, db_path=db_path)
    current_hash = _content_hash(entries)

    label = f"window-{days}d"
    if not no_cache:
        cached_summary, cached_hash = _read_cache(label)
        if cached_summary and cached_hash == current_hash:
            return cached_summary

    summary = _synthesise(entries, days)
    if summary is None:
        # Synthesis failed — return raw fallback
        if not entries:
            return f"No journal entries in the last {days} days."
        lines = [f"[{e['timestamp']}] {e['raw_text']}" for e in entries[:20]]
        return "Journal entries (raw, synthesis unavailable):\n\n" + "\n".join(lines)

    _write_cache(label, summary, current_hash)
    return summary


def window_month(no_cache: bool = False, db_path: Optional[Path] = None) -> str:
    """Convenience: 30-day window summary."""
    return window(days=DEFAULT_MONTH_DAYS, no_cache=no_cache, db_path=db_path)
