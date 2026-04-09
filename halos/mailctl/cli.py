"""mailctl CLI — Email operations, inbox triage, and filter management.

Supports both gmail (kai@oceanheart.ai) and icloud (rickhallett@icloud.com).

Usage:
    mailctl inbox [--unread] [--json]       Inbox snapshot
    mailctl read <id>                       Read a message
    mailctl search <query>                  Search messages (IMAP syntax)
    mailctl triage [--execute] [--json]     Run triage rules on unread inbox
    mailctl send --to X --subject Y         Send (body from stdin)
    mailctl folders                         List folders/labels
    mailctl filters                         List managed filters
    mailctl actions [--limit N]             Show recent action log
    mailctl summary                         One-line summary for briefings

All commands accept -a/--account (gmail|icloud|all). Default: all for triage, gmail for others.
"""

import argparse
import json
import sys

from . import store
from .engine import ACCOUNTS, DEFAULT_ACCOUNT


def _get_accounts(args: argparse.Namespace) -> list[str]:
    """Resolve account arg to list of accounts."""
    acct = getattr(args, "account", DEFAULT_ACCOUNT)
    if acct == "all":
        return list(ACCOUNTS)
    return [acct]


# --- Commands ---


def cmd_inbox(args: argparse.Namespace) -> int:
    """Inbox snapshot."""
    from . import engine

    for acct in _get_accounts(args):
        messages = engine.list_messages(folder="INBOX", page_size=50, account=acct)
        if args.unread:
            messages = [m for m in messages if "Seen" not in m.get("flags", [])]

        if args.json:
            print(json.dumps({"account": acct, "messages": messages}, indent=2))
            continue

        print(f"\n{'=' * 60}")
        print(f"  {acct.upper()}")
        print(f"{'=' * 60}")

        if not messages:
            print("  (empty)" if not args.unread else "  (no unread)")
            continue

        for m in messages:
            seen = " " if "Seen" in m.get("flags", []) else "*"
            sender = m.get("from", {}).get("name") or m.get("from", {}).get("addr", "?")
            subject = m.get("subject", "(no subject)")
            date = m.get("date", "")[:16]
            print(f"  {seen} {m.get('id', '?'):<8} {date}  {sender:<25} {subject:.60}")

        print(f"  {len(messages)} message(s)")

    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Read a message."""
    from . import engine

    acct = _get_accounts(args)[0]
    msg = engine.read_message(args.message_id, account=acct)
    if isinstance(msg, dict):
        print(json.dumps(msg, indent=2) if args.json else msg.get("body", ""))
    else:
        print(msg)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search messages."""
    from . import engine

    for acct in _get_accounts(args):
        results = engine.search(args.query, account=acct)
        if args.json:
            print(json.dumps({"account": acct, "results": results}, indent=2))
            continue

        if not results:
            continue

        print(f"\n  [{acct.upper()}]")
        for m in results:
            sender = m.get("from", {}).get("name") or m.get("from", {}).get("addr", "?")
            subject = m.get("subject", "(no subject)")
            print(f"  {m.get('id', '?'):<8} {sender:<25} {subject:.60}")
        print(f"  {len(results)} result(s)")

    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """Run triage rules on unread inbox across accounts."""
    from . import engine
    from .triage import run_triage

    dry_run = not args.execute
    grand_total = 0
    grand_actions: dict[str, int] = {}

    for acct in _get_accounts(args):
        messages = engine.list_messages(folder="INBOX", page_size=100, account=acct)
        unread = [m for m in messages if "Seen" not in m.get("flags", [])]

        if not unread:
            print(f"\n  [{acct.upper()}] No unread messages.")
            continue

        results = run_triage(unread, dry_run=dry_run, account=acct)

        if args.json:
            print(json.dumps({"account": acct, "results": results}, indent=2))
            continue

        print(f"\n{'=' * 60}")
        print(f"  {acct.upper()} — {len(results)} message(s)")
        print(f"{'=' * 60}")

        for r in results:
            action = r["action"].upper()
            grand_actions[action] = grand_actions.get(action, 0) + 1
            dest = f" -> {r['label']}" if r.get("label") else ""
            print(f"  [{action:<8}] {r['from']:<35} {r['subject'][:50]}{dest}")

        grand_total += len(results)

    if not args.json:
        label = "DRY RUN — " if dry_run else ""
        print(f"\n{label}{grand_total} message(s) triaged across {len(_get_accounts(args))} account(s)")
        for act, count in sorted(grand_actions.items()):
            print(f"  {act}: {count}")

    return 0


def cmd_send(args: argparse.Namespace) -> int:
    """Send a message (body from stdin)."""
    from . import engine

    acct = _get_accounts(args)[0]
    body = sys.stdin.read()
    engine.send(to=args.to, subject=args.subject, body=body, cc=args.cc, account=acct)
    print(f"Sent to {args.to} via {acct}")
    return 0


def cmd_folders(args: argparse.Namespace) -> int:
    """List folders/labels."""
    from . import engine

    for acct in _get_accounts(args):
        folder_list = engine.folders(account=acct)
        if args.json:
            print(json.dumps({"account": acct, "folders": folder_list}, indent=2))
            continue

        print(f"\n  [{acct.upper()}]")
        for f in folder_list:
            name = f.get("name", "?") if isinstance(f, dict) else str(f)
            print(f"    {name}")

    return 0


def cmd_filters(args: argparse.Namespace) -> int:
    """List all managed filters."""
    filters = store.list_filters()
    if not filters:
        print("No managed filters.")
        return 0
    for f in filters:
        reason = f.get("reason") or ""
        print(f"  {f['sender']:<45} {f['gmail_filter_id'][:20]}...  {reason}")
    print(f"\n{len(filters)} filter(s) managed by mailctl")
    return 0


def cmd_actions(args: argparse.Namespace) -> int:
    """Show recent action log."""
    actions = store.list_actions(limit=args.limit)
    if not actions:
        print("No actions recorded.")
        return 0
    for a in actions:
        sender = a.get("sender") or ""
        details = a.get("details") or ""
        print(f"  {a['timestamp'][:19]}  {a['action']:<20} {sender:<35} {details}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """One-line summary for briefing integration."""
    from .briefing import text_summary

    print(text_summary())
    return 0


# --- Argument Parser ---


def _add_account_arg(parser: argparse.ArgumentParser, default: str = DEFAULT_ACCOUNT):
    """Add -a/--account argument to a parser."""
    parser.add_argument(
        "-a", "--account",
        choices=[*ACCOUNTS, "all"],
        default=default,
        help=f"Account to use (default: {default})",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mailctl",
        description="Email operations, inbox triage, and filter management",
    )
    sub = parser.add_subparsers(dest="command")

    # inbox
    inbox_p = sub.add_parser("inbox", help="Inbox snapshot")
    inbox_p.add_argument("--unread", action="store_true", help="Unread only")
    inbox_p.add_argument("--json", action="store_true", help="JSON output")
    _add_account_arg(inbox_p)

    # read
    read_p = sub.add_parser("read", help="Read a message")
    read_p.add_argument("message_id", help="Message ID")
    read_p.add_argument("--json", action="store_true", help="JSON output")
    _add_account_arg(read_p)

    # search
    search_p = sub.add_parser("search", help="Search messages")
    search_p.add_argument("query", help="Search query (IMAP syntax)")
    search_p.add_argument("--json", action="store_true", help="JSON output")
    _add_account_arg(search_p)

    # triage — defaults to "all" accounts
    triage_p = sub.add_parser("triage", help="Run triage rules on unread inbox")
    triage_p.add_argument("--execute", action="store_true", help="Execute triage actions")
    triage_p.add_argument("--json", action="store_true", help="JSON output")
    _add_account_arg(triage_p, default="all")

    # send
    send_p = sub.add_parser("send", help="Send a message (body from stdin)")
    send_p.add_argument("--to", required=True, help="Recipient address")
    send_p.add_argument("--subject", required=True, help="Subject line")
    send_p.add_argument("--cc", default=None, help="CC address")
    _add_account_arg(send_p)

    # folders
    folders_p = sub.add_parser("folders", help="List folders/labels")
    folders_p.add_argument("--json", action="store_true", help="JSON output")
    _add_account_arg(folders_p, default="all")

    # existing (no account needed)
    sub.add_parser("filters", help="List managed filters")

    actions_p = sub.add_parser("actions", help="Show recent action log")
    actions_p.add_argument("--limit", type=int, default=50, help="Max actions to show")

    sub.add_parser("summary", help="One-line briefing summary")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "inbox": cmd_inbox,
        "read": cmd_read,
        "search": cmd_search,
        "triage": cmd_triage,
        "send": cmd_send,
        "folders": cmd_folders,
        "filters": cmd_filters,
        "actions": cmd_actions,
        "summary": cmd_summary,
    }
    sys.exit(dispatch[args.command](args) or 0)
