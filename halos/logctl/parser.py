"""Log line parsers for pino pretty-print, JSON, and plain text formats."""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class LogEntry:
    timestamp: Optional[str] = None
    level: str = "info"
    source: str = ""
    message: str = ""
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


# Pino pretty-print format:
# [16:03:37.233] INFO (30081): Database initialized
# With ANSI codes: [16:03:37.233] \x1b[32mINFO\x1b[39m (30081): \x1b[36mDatabase initialized\x1b[39m
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_PINO_RE = re.compile(
    r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+"
    r"(\w+)\s+"
    r"\((\d+)\):\s+"
    r"(.+)$"
)
# Pino key-value continuation line: "    key: value"
_PINO_KV_RE = re.compile(r"^\s{4}(\w+):\s+(.+)$")

# Pino JSON format (when piped without pretty-print)
# {"level":30,"time":1710000000000,"msg":"Database initialized","pid":30081}
_PINO_LEVELS = {10: "trace", 20: "debug", 30: "info", 40: "warn", 50: "error", 60: "fatal"}

# halos structured format (YAML one-liner or JSON)
_HALOS_LEVELS = {"debug", "info", "warn", "error"}


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def parse_pino_pretty(line: str) -> Optional[LogEntry]:
    """Parse a pino pretty-printed log line."""
    clean = strip_ansi(line.rstrip())
    m = _PINO_RE.match(clean)
    if not m:
        return None
    timestamp, level, pid, message = m.groups()
    return LogEntry(
        timestamp=timestamp,
        level=level.lower(),
        source="nanoclaw",
        message=message.strip(),
        data={"pid": int(pid)},
    )


def parse_pino_json(line: str) -> Optional[LogEntry]:
    """Parse a pino JSON log line."""
    try:
        obj = json.loads(line.strip())
    except (json.JSONDecodeError, ValueError):
        return None

    if "level" not in obj and "msg" not in obj:
        return None

    level_num = obj.get("level", 30)
    level = _PINO_LEVELS.get(level_num, "info") if isinstance(level_num, int) else str(level_num)

    ts = obj.get("time")
    timestamp = None
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            timestamp = dt.strftime("%H:%M:%S.%f")[:-3]
        except (OSError, ValueError):
            pass
    elif isinstance(ts, str):
        timestamp = ts

    # Extract known fields, put rest in data
    known = {"level", "time", "msg", "pid", "hostname", "name"}
    data = {k: v for k, v in obj.items() if k not in known}
    if "pid" in obj:
        data["pid"] = obj["pid"]

    return LogEntry(
        timestamp=timestamp,
        level=level,
        source=obj.get("name", "nanoclaw"),
        message=obj.get("msg", ""),
        data=data,
    )


def parse_halos_structured(line: str) -> Optional[LogEntry]:
    """Parse a halos structured log line (JSON or simple YAML-ish)."""
    stripped = line.strip()
    if not stripped:
        return None

    # Try JSON first
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict) and "event" in obj:
            return LogEntry(
                timestamp=obj.get("ts", ""),
                level=obj.get("level", "info"),
                source=obj.get("source", ""),
                message=obj.get("event", ""),
                data=obj.get("data", {}),
            )
    except (json.JSONDecodeError, ValueError):
        pass

    # Try YAML
    try:
        import yaml
        obj = yaml.safe_load(stripped)
        if isinstance(obj, dict) and "event" in obj:
            return LogEntry(
                timestamp=obj.get("ts", ""),
                level=obj.get("level", "info"),
                source=obj.get("source", ""),
                message=obj.get("event", ""),
                data=obj.get("data", {}),
            )
    except Exception:
        pass

    return None


def parse_plain(line: str) -> Optional[LogEntry]:
    """Parse a plain text log line — just wraps the raw text."""
    stripped = line.rstrip()
    if not stripped:
        return None
    return LogEntry(message=stripped)


def parse_line(line: str, fmt: str = "pino") -> Optional[LogEntry]:
    """Parse a log line according to the specified format.

    Falls back through parsers: pino pretty -> pino json -> halos structured -> plain.
    """
    if fmt == "pino":
        entry = parse_pino_pretty(line)
        if entry:
            return entry
        entry = parse_pino_json(line)
        if entry:
            return entry

    if fmt == "jsonl":
        entry = parse_pino_json(line)
        if entry:
            return entry
        entry = parse_halos_structured(line)
        if entry:
            return entry

    # halos structured logs
    entry = parse_halos_structured(line)
    if entry:
        return entry

    # Final fallback: plain text (skip blank lines and continuation lines for pino)
    return parse_plain(line)


def format_entry(entry: LogEntry) -> str:
    """Format a LogEntry for human-readable display."""
    parts = []
    if entry.timestamp:
        parts.append(f"[{entry.timestamp}]")
    parts.append(f"{entry.level.upper():5s}")
    if entry.source:
        parts.append(f"({entry.source})")
    parts.append(entry.message)
    return " ".join(parts)
