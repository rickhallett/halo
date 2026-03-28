#!/usr/bin/env python3
"""Extract telemetry from a Claude Code session JSONL file.

Usage: python3 session_telemetry.py <session_id_or_jsonl_path>

Searches ~/.claude/projects/ for matching session files if given a session ID.
Outputs a structured summary of token usage, tool calls, and timing.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional


def find_session_file(session_id: str) -> Optional[Path]:
    """Find JSONL file by session ID in Claude projects dir."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    for jsonl in projects_dir.rglob(f"{session_id}.jsonl"):
        return jsonl
    # Partial match
    for jsonl in projects_dir.rglob("*.jsonl"):
        if session_id in jsonl.stem:
            return jsonl
    return None


def categorize_bash(cmd: str) -> str:
    """Categorize a bash command by purpose."""
    cl = cmd.lower()
    if "steer see" in cl or "steer ocr" in cl or "screencapture" in cl:
        return "observe"
    elif "steer click" in cl:
        return "act:click"
    elif "steer type" in cl:
        return "act:type"
    elif "steer hotkey" in cl or "steer scroll" in cl or "steer drag" in cl:
        return "act:input"
    elif "steer apps" in cl or "steer focus" in cl:
        return "act:focus"
    elif "sleep" in cl:
        return "wait"
    elif "steer" in cl and ("help" in cl or "which" in cl or "find" in cl):
        return "explore"
    elif "yq" in cl:
        return "report"
    elif "curl" in cl:
        return "navigate"
    else:
        return "other"


def analyze(path: Path) -> dict:
    """Parse JSONL and return telemetry dict."""
    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    assistant_turns = 0
    tool_calls = Counter()
    bash_categories = Counter()
    bash_commands = []
    steer_path_redefs = 0

    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue

            msg = d.get("message", {})
            if not isinstance(msg, dict):
                continue

            usage = msg.get("usage", {})
            if usage:
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                total_cache_create += usage.get("cache_creation_input_tokens", 0)
                total_cache_read += usage.get("cache_read_input_tokens", 0)

            if msg.get("role") == "assistant":
                assistant_turns += 1

            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "unknown")
                        tool_calls[name] += 1
                        if name == "Bash":
                            cmd = block.get("input", {}).get("command", "")
                            bash_commands.append(cmd)
                            bash_categories[categorize_bash(cmd)] += 1
                            if "STEER=/" in cmd or "steer=/" in cmd:
                                steer_path_redefs += 1

    return {
        "file": str(path),
        "file_size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "tokens": {
            "input": total_input,
            "output": total_output,
            "cache_creation": total_cache_create,
            "cache_read": total_cache_read,
            "total_context": total_input + total_output + total_cache_create + total_cache_read,
        },
        "turns": assistant_turns,
        "tool_calls": dict(tool_calls.most_common()),
        "tool_calls_total": sum(tool_calls.values()),
        "bash_categories": dict(sorted(bash_categories.items(), key=lambda x: -x[1])),
        "bash_total": len(bash_commands),
        "steer_path_redefinitions": steer_path_redefs,
        "act_commands": sum(v for k, v in bash_categories.items() if k.startswith("act:")),
        "efficiency": round(
            sum(v for k, v in bash_categories.items() if k.startswith("act:"))
            / max(len(bash_commands), 1) * 100, 1
        ),
    }


def print_report(data: dict):
    """Print human-readable report."""
    t = data["tokens"]
    print(f"=== Agent Session Telemetry ===")
    print(f"File:                {data['file']} ({data['file_size_mb']} MB)")
    print(f"Assistant turns:     {data['turns']}")
    print(f"Tool calls:          {data['tool_calls_total']}")
    print(f"")
    print(f"--- Tokens ---")
    print(f"  Input:             {t['input']:>12,}")
    print(f"  Output:            {t['output']:>12,}")
    print(f"  Cache creation:    {t['cache_creation']:>12,}")
    print(f"  Cache read:        {t['cache_read']:>12,}")
    print(f"  Total context:     {t['total_context']:>12,}")
    print(f"")
    print(f"--- Tool Calls ---")
    for name, count in data["tool_calls"].items():
        print(f"  {name:30s} {count:4d}")
    print(f"")
    print(f"--- Bash Categories ---")
    for cat, count in data["bash_categories"].items():
        pct = count / max(data["bash_total"], 1) * 100
        print(f"  {cat:30s} {count:4d}  ({pct:.0f}%)")
    print(f"  {'TOTAL':30s} {data['bash_total']:4d}")
    print(f"")
    print(f"--- Efficiency ---")
    print(f"  Steer path redefs: {data['steer_path_redefinitions']}/{data['bash_total']}")
    print(f"  ACT commands:      {data['act_commands']}/{data['bash_total']} ({data['efficiency']}%)")
    print(f"")

    # Output JSON too
    print(f"--- JSON ---")
    print(json.dumps(data, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: session_telemetry.py <session_id_or_jsonl_path>")
        sys.exit(1)

    target = sys.argv[1]
    path = Path(target)

    if path.exists() and path.suffix == ".jsonl":
        pass
    else:
        path = find_session_file(target)
        if not path:
            print(f"Session not found: {target}")
            sys.exit(1)

    data = analyze(path)
    print_report(data)


if __name__ == "__main__":
    main()
