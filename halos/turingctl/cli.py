"""CLI for Turing drill session management.

Commands:
    capture   Extract and store a drill session from Claude Code JSONL
    list      List stored drill sessions
    show      Show a session with its conversation turns
    stats     Session count and machine distribution
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import extract, store


def _session_id() -> str:
    """Generate a date-based session ID: YYYYMMDD-HHMMSS."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def cmd_capture(args: argparse.Namespace) -> int:
    """Extract a drill session from a JSONL file and store it."""
    # Find the session file
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
    else:
        path = extract.find_latest_session(project_hint="halo")
        if not path:
            print("No Claude Code session files found.", file=sys.stderr)
            return 1
        print(f"Using latest session: {path}")

    # Extract turns
    turns = extract.extract_conversations(path)
    if not turns:
        print("No conversation turns found in session.", file=sys.stderr)
        return 1

    print(f"Extracted {len(turns)} turns ({sum(1 for t in turns if t['role'] == 'user')} user, "
          f"{sum(1 for t in turns if t['role'] == 'assistant')} assistant)")

    # Create session
    session_id = _session_id()
    session = store.create_session(
        session_id=session_id,
        machine=args.machine,
        fmt=args.format,
        drill_description=args.description or "",
        turns=turns,
        duration_mins=args.duration,
        scores=json.loads(args.scores) if args.scores else None,
        session_source=str(path),
        notes=args.notes or "",
    )

    print(f"Session stored: {session['id']}")
    print(f"  Machine: {session['machine']}")
    print(f"  Format: {session['format']}")
    if session["duration_mins"]:
        print(f"  Duration: {session['duration_mins']} min")
    print(f"  Turns: {len(turns)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List stored drill sessions."""
    sessions = store.list_sessions(
        machine=args.machine,
        days=args.days,
    )
    if not sessions:
        print("No drill sessions found.")
        return 0

    print(f"{'ID':<20} {'Date':<12} {'Machine':<16} {'Fmt':<10} {'Desc'}")
    print("-" * 80)
    for s in sessions:
        date = s["timestamp"][:10]
        desc = (s["drill_description"][:35] + "...") if len(s["drill_description"]) > 38 else s["drill_description"]
        print(f"{s['id']:<20} {date:<12} {s['machine']:<16} {s['format']:<10} {desc}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show a session with conversation turns."""
    session = store.get_session(args.session_id)
    if not session:
        print(f"Session not found: {args.session_id}", file=sys.stderr)
        return 1

    print(f"=== Drill Session: {session['id']} ===")
    print(f"Machine:     {session['machine']}")
    print(f"Format:      {session['format']}")
    print(f"Timestamp:   {session['timestamp']}")
    if session["duration_mins"]:
        print(f"Duration:    {session['duration_mins']} min")
    if session["drill_description"]:
        print(f"Description: {session['drill_description']}")
    if session["scores"]:
        print(f"Scores:      {json.dumps(session['scores'])}")
    if session["notes"]:
        print(f"Notes:       {session['notes']}")
    print()

    for turn in session["turns"]:
        role_label = "USER" if turn["role"] == "user" else "TURING"
        tools = turn["tools_used"]
        tool_str = f" [{', '.join(tools)}]" if tools else ""
        print(f"--- {role_label} (turn {turn['turn_number']}){tool_str} ---")
        # Truncate long content for display
        content = turn["content"]
        if not args.full and len(content) > 500:
            content = content[:500] + "\n[... truncated, use --full to see all]"
        print(content)
        print()

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show session statistics."""
    total = store.session_count()
    by_machine = store.machine_summary()

    print(f"Total drill sessions: {total}")
    if by_machine:
        print("\nBy machine:")
        for machine, count in sorted(by_machine.items()):
            print(f"  {machine:<20} {count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="turingctl",
        description="Turing drill session management",
    )
    sub = parser.add_subparsers(dest="command")

    # capture
    cap = sub.add_parser("capture", help="Extract and store a drill session")
    cap.add_argument("--file", "-f", help="Path to JSONL session file (default: latest)")
    cap.add_argument("--machine", "-m", required=True,
                     choices=store.VALID_MACHINES,
                     help="Which of the Five Machines was drilled")
    cap.add_argument("--format", required=True,
                     choices=store.VALID_FORMATS,
                     help="Drill format")
    cap.add_argument("--description", "-d", help="What the drill was about")
    cap.add_argument("--duration", type=int, help="Duration in minutes")
    cap.add_argument("--scores", help='JSON scores: \'{"control":"functional",...}\'')
    cap.add_argument("--notes", "-n", help="Post-drill observations")

    # list
    ls = sub.add_parser("list", help="List drill sessions")
    ls.add_argument("--machine", "-m", choices=store.VALID_MACHINES)
    ls.add_argument("--days", type=int, help="Look back N days")

    # show
    sh = sub.add_parser("show", help="Show a session with turns")
    sh.add_argument("session_id", help="Session ID to display")
    sh.add_argument("--full", action="store_true", help="Show full turn content")

    # stats
    sub.add_parser("stats", help="Session statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "capture": cmd_capture,
        "list": cmd_list,
        "show": cmd_show,
        "stats": cmd_stats,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
