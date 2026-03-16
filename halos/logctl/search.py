"""Search and filter logic for log entries."""

import collections
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .parser import LogEntry, parse_line


def matches_level(entry: LogEntry, level: Optional[str]) -> bool:
    """Check if entry matches the requested level filter."""
    if not level:
        return True
    return entry.level == level.lower()


def matches_source(entry: LogEntry, source: Optional[str]) -> bool:
    """Check if entry matches the requested source filter."""
    if not source:
        return True
    return entry.source.lower() == source.lower()


def matches_text(entry: LogEntry, text: Optional[str]) -> bool:
    """Check if entry message contains the search text (case-insensitive)."""
    if not text:
        return True
    lower_text = text.lower()
    if lower_text in entry.message.lower():
        return True
    # Also search in data values
    for v in entry.data.values():
        if lower_text in str(v).lower():
            return True
    return False


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse a human-friendly duration string like '1h', '24h', '7d', '30m'."""
    m = re.match(r"^(\d+)\s*([mhd])$", duration_str.strip().lower())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return None


def matches_since(entry: LogEntry, since: Optional[str], now: Optional[datetime] = None) -> bool:
    """Check if entry falls within the time window specified by 'since'."""
    if not since:
        return True
    if not entry.timestamp:
        return True  # Can't filter on time if no timestamp — include it

    delta = parse_duration(since)
    if not delta:
        return True  # Unparseable duration — include everything

    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - delta

    # Parse the timestamp — could be HH:MM:SS.mmm (pino pretty) or ISO format
    ts = entry.timestamp
    try:
        if "T" in ts:
            # ISO format
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            # HH:MM:SS.mmm — assume today in UTC
            t = datetime.strptime(ts, "%H:%M:%S.%f").time()
            dt = datetime.combine(now.date(), t, tzinfo=timezone.utc)
            # If the parsed time is in the future, it's from yesterday
            if dt > now:
                dt -= timedelta(days=1)
    except (ValueError, TypeError):
        return True  # Can't parse — include it

    return dt >= cutoff


def filter_entries(
    entries: list[LogEntry],
    level: Optional[str] = None,
    source: Optional[str] = None,
    text: Optional[str] = None,
    since: Optional[str] = None,
    now: Optional[datetime] = None,
) -> list[LogEntry]:
    """Apply all filters to a list of log entries."""
    return [
        e for e in entries
        if matches_level(e, level)
        and matches_source(e, source)
        and matches_text(e, text)
        and matches_since(e, since, now)
    ]


def read_log_file(filepath: str, fmt: str = "pino") -> list[LogEntry]:
    """Read and parse all lines from a log file (streaming, never loads entire file)."""
    p = Path(filepath)
    if not p.exists():
        return []

    entries = []
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                entry = parse_line(line.rstrip("\n"), fmt)
                if entry:
                    entries.append(entry)
    except (PermissionError, OSError) as e:
        print(f"WARN: cannot read {filepath}: {e}", file=sys.stderr)
    return entries


def read_log_tail(filepath: str, n: int = 50, fmt: str = "pino") -> list[LogEntry]:
    """Read and parse the last n lines from a log file (streaming with deque)."""
    p = Path(filepath)
    if not p.exists():
        return []

    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            tail = collections.deque(fh, maxlen=n)
    except (PermissionError, OSError) as e:
        print(f"WARN: cannot read {filepath}: {e}", file=sys.stderr)
        return []

    entries = []
    for line in tail:
        entry = parse_line(line.rstrip("\n"), fmt)
        if entry:
            entries.append(entry)
    return entries


def compute_stats(entries: list[LogEntry]) -> dict:
    """Compute log statistics: volume by source, level distribution, error rate."""
    by_source: dict[str, int] = {}
    by_level: dict[str, int] = {}
    total = len(entries)

    for e in entries:
        src = e.source or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
        by_level[e.level] = by_level.get(e.level, 0) + 1

    error_count = by_level.get("error", 0) + by_level.get("fatal", 0)
    error_rate = (error_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "by_source": dict(sorted(by_source.items(), key=lambda x: -x[1])),
        "by_level": dict(sorted(by_level.items(), key=lambda x: -x[1])),
        "error_count": error_count,
        "error_rate": round(error_rate, 2),
    }
