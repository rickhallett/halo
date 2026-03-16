"""Structured log emitter for halos modules.

Usage:
    from halos.common.log import hlog
    hlog("memctl", "info", "note_created", {"id": "20260316-...", "title": "..."})

Writes one JSON line per call to the configured log file.
If LOG_FILE is not set, writes to stderr as a fallback.
"""

import json
import os
import sys
from datetime import datetime, timezone


_LOG_FILE = os.environ.get("HALOS_LOG_FILE", "")


def hlog(source: str, level: str, event: str, data: dict | None = None) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "source": source,
        "event": event,
    }
    if data:
        entry["data"] = data

    line = json.dumps(entry, default=str)

    if _LOG_FILE:
        try:
            with open(_LOG_FILE, "a") as f:
                f.write(line + "\n")
        except OSError:
            print(line, file=sys.stderr)
    else:
        print(line, file=sys.stderr)
