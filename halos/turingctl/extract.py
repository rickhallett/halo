"""Extract and sanitise conversation turns from Claude Code JSONL sessions.

Reads the raw JSONL that Claude Code writes per-session, strips sensitive
content (file bodies, tool results, env vars, API keys), and returns only
the conversational signal: what the user said, what the assistant reasoned,
and which tools were invoked (names only, no payloads).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# Patterns that look like secrets — stripped from text content
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),              # Anthropic / OpenAI keys
    re.compile(r"xoxb-[a-zA-Z0-9_-]+"),                 # Slack bot tokens
    re.compile(r"ghp_[a-zA-Z0-9]{36,}"),                # GitHub PATs
    re.compile(r"[A-Z_]{3,}=\S+"),                      # ENV_VAR=value patterns
    re.compile(r"\b[0-9]{10}:[A-Za-z0-9_-]{35}\b"),     # Telegram bot tokens
]


def _redact(text: str) -> str:
    """Replace secret-shaped strings with [REDACTED]."""
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def _extract_text_from_content(content: list | str) -> tuple[str, list[str]]:
    """Extract text blocks and tool names from a message content array.

    Returns (text, tool_names) where text is the concatenated text blocks
    and tool_names is a list of tool names that were invoked.
    """
    if isinstance(content, str):
        return _redact(content), []

    texts = []
    tools = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            texts.append(_redact(block.get("text", "")))
        elif block.get("type") == "tool_use":
            tools.append(block.get("name", "unknown"))
            # Keep only the tool name — inputs may contain file contents,
            # API keys, full command strings. Strip everything.
    return "\n".join(texts), tools


def extract_conversations(path: Path) -> list[dict]:
    """Extract sanitised conversation turns from a Claude Code JSONL file.

    Returns a list of turn dicts:
        {
            "role": "user" | "assistant",
            "text": str,           # sanitised text content only
            "tools_used": [str],   # tool names invoked (assistant only)
            "turn_number": int,
            "message_id": str,
        }

    Tool results, file contents, and command outputs are stripped entirely.
    Only the conversational exchange and tool invocation names are preserved.
    """
    turns: list[dict] = []
    turn_number = 0

    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            msg = d.get("message", {})
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue

            content = msg.get("content", [])
            text, tools = _extract_text_from_content(content)

            # Skip empty turns (tool results with no text)
            if not text.strip() and not tools:
                continue

            turn_number += 1
            turns.append({
                "role": role,
                "text": text.strip(),
                "tools_used": tools,
                "turn_number": turn_number,
                "message_id": msg.get("id", ""),
            })

    return turns


def find_latest_session(project_hint: Optional[str] = None) -> Optional[Path]:
    """Find the most recent Claude Code JSONL session file.

    Args:
        project_hint: substring to match in the project path (e.g. "halo")

    Returns the path to the most recent .jsonl file, or None.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    candidates = []
    for jsonl in projects_dir.rglob("*.jsonl"):
        if project_hint and project_hint not in str(jsonl):
            continue
        candidates.append(jsonl)

    if not candidates:
        return None

    # Most recently modified
    return max(candidates, key=lambda p: p.stat().st_mtime)
