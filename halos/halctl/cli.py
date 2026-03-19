"""halctl CLI — microHAL fleet management.

Provision, monitor, and control independent HAL instances.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from halos.common.log import hlog
from .logged import logged


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@logged
def cmd_create(args):
    """Provision a new microHAL instance."""
    from .provision import create_instance

    try:
        entry = create_instance(
            name=args.name,
            personality=args.personality,
        )
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"created  {entry['name']}  {entry['path']}")
    print(f"personality: {entry['personality']}")
    print(f"token env:   {entry['telegram_bot_token_env']}")
    print()
    print("Next steps:")
    print("  1. Open Telegram, message @BotFather")
    print("  2. Send /newbot and follow the prompts")
    print(
        f"  3. Set the bot token as {entry['telegram_bot_token_env']} in your environment"
    )
    print(
        f"  4. Start the instance: cd {entry['path']}/.. && npx pm2 start ecosystem.config.cjs"
    )
    return 0


@logged
def cmd_list(args):
    """List fleet instances with live audit data."""
    from .config import load_fleet_manifest
    from pathlib import Path
    import re
    import sqlite3 as sqlite

    manifest = load_fleet_manifest()
    instances = manifest.get("instances", [])

    if not instances:
        print("no instances")
        return 0

    rows = []
    for inst in instances:
        name = inst["name"]
        deploy = Path(inst.get("path", ""))
        status = inst.get("status", "unknown")
        personality = inst.get("personality", "")

        bot_username = ""
        tg_group = ""
        notes = 0
        host_path = str(deploy).replace(str(Path.home()), "~")

        if deploy.exists():
            # Bot username from ecosystem config
            eco = deploy.parent / "ecosystem.config.cjs"
            if eco.exists():
                content = eco.read_text()
                m = re.search(r'TELEGRAM_BOT_TOKEN:\s*["\'](\d+):', content)
                if m:
                    # Get username from DB chats or fall back to token prefix
                    bot_username = m.group(1)

            # Telegram group from registered_groups
            db_path = deploy / "store" / "messages.db"
            if db_path.exists():
                try:
                    conn = sqlite.connect(str(db_path))
                    cur = conn.execute(
                        "SELECT jid, name FROM registered_groups LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        tg_group = f"{row[0]} ({row[1]})"
                    conn.close()
                except Exception:
                    tg_group = "?"

            # Notes count
            notes_dir = deploy / "memory" / "notes"
            if notes_dir.exists():
                notes = len(list(notes_dir.glob("*.md")))

        rows.append(
            (name, status, personality, bot_username, tg_group, notes, host_path)
        )

    # Print table
    fmt = "{:<10} {:<8} {:<16} {:<14} {:<28} {:<6} {}"
    print(
        fmt.format(
            "NAME", "STATUS", "PERSONALITY", "BOT ID", "TG GROUP", "NOTES", "HOST PATH"
        )
    )
    print("─" * 120)
    for r in rows:
        print(fmt.format(r[0], r[1], r[2], r[3], r[4], r[5], r[6]))

    # Container perspective (footer)
    print()
    print(
        "Container mounts: /workspace/project (ro) · /workspace/group (rw) · /workspace/ipc (rw)"
    )
    return 0


@logged
def cmd_status(args):
    """Show details of a specific instance."""
    from .config import load_fleet_manifest
    from pathlib import Path

    manifest = load_fleet_manifest()
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            instance = inst
            break

    if instance is None:
        print(f"ERROR: instance '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    deploy = Path(instance["path"])
    print(f"Name:        {instance['name']}")
    print(f"Status:      {instance.get('status', 'unknown')}")
    print(f"Personality: {instance.get('personality', '')}")
    print(f"Path:        {instance['path']}")
    print(f"Token env:   {instance.get('telegram_bot_token_env', '')}")
    print(f"Services:    {', '.join(instance.get('services', []))}")
    print(f"Created:     {instance.get('created', '')}")

    # Disk usage (if path exists)
    if deploy.exists():
        import subprocess

        try:
            result = subprocess.run(
                ["du", "-sh", str(deploy)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(f"Disk:        {result.stdout.split()[0]}")
        except Exception:
            pass

        # Memory notes count
        mem_dir = deploy / "memory" / "notes"
        if mem_dir.exists():
            notes = list(mem_dir.glob("*.md"))
            print(f"Notes:       {len(notes)}")
    else:
        print(f"Disk:        (path not found)")

    return 0


@logged
def cmd_freeze(args):
    """Freeze an instance (stop process, preserve everything)."""
    from .provision import freeze_instance

    try:
        freeze_instance(args.name)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


@logged
def cmd_fold(args):
    """Fold an instance (stop + archive)."""
    from .provision import fold_instance

    try:
        fold_instance(args.name)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


@logged
def cmd_fry(args):
    """Fry an instance (stop + wipe). Nuclear."""
    from .provision import fry_instance

    try:
        fry_instance(args.name, confirm=args.confirm)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


@logged
def cmd_reset(args):
    """Nuclear reset: kill container, clear all state, fresh start."""
    from .config import load_fleet_manifest
    from pathlib import Path
    import subprocess
    import shutil

    manifest = load_fleet_manifest()
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            instance = inst
            break

    if instance is None:
        print(f"ERROR: instance '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    deploy = Path(instance["path"])
    print(f"Resetting {args.name}...")

    # 1. Kill any running containers for this instance
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=nanoclaw-telegram-main", "-q"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for cid in result.stdout.strip().split("\n"):
            if cid:
                subprocess.run(["docker", "kill", cid], capture_output=True, timeout=5)
                print(f"  killed container {cid[:12]}")
    except Exception:
        pass

    # 2. Clear database
    db_path = deploy / "store" / "messages.db"
    if db_path.exists():
        try:
            subprocess.run(
                [
                    "sqlite3",
                    str(db_path),
                    "DELETE FROM messages; DELETE FROM chats; DELETE FROM sessions;",
                ],
                capture_output=True,
                timeout=5,
            )
            print("  cleared messages, chats, sessions")
        except Exception as e:
            print(f"  WARN: db clear failed: {e}", file=sys.stderr)

    # 3. Wipe session files
    sessions_dir = deploy / "data" / "sessions"
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir)
        print("  wiped session files")

    # 4. Restart pm2
    try:
        subprocess.run(
            ["npx", "pm2", "delete", f"microhal-{args.name}"],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass

    eco_path = deploy.parent / "ecosystem.config.cjs"
    if eco_path.exists():
        result = subprocess.run(
            ["npx", "pm2", "start", str(eco_path)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(deploy.parent),
        )
        if result.returncode == 0:
            print(f"  restarted pm2 process")
        else:
            print(f"  WARN: pm2 start failed: {result.stderr[:100]}", file=sys.stderr)
    else:
        print(f"  WARN: no ecosystem config at {eco_path}", file=sys.stderr)

    print(f"\nreset complete — {args.name} is fresh")
    return 0


@logged
def cmd_assess(args):
    """Run assessment scenarios against a live instance."""
    from .eval_harness import run_assessment, SCENARIOS

    scenarios = None
    if args.scenario:
        scenarios = [args.scenario]

    print(f"assessment: {args.name}")
    print("─" * 50)
    records = run_assessment(args.name, scenarios=scenarios, timeout=args.timeout)
    print("─" * 50)

    passed = sum(1 for r in records if r.passed)
    total = len(records)
    print(f"result: {passed}/{total} scenarios passed")

    print(f"records written to: data/assessments/")

    return 0 if passed == total else 1


@logged
def cmd_supervise(args):
    """Run supervisor sweep on an instance or all instances."""
    from .supervisor import supervise_instance, supervise_all

    window = args.window

    if args.name == "all":
        results = supervise_all(window_minutes=window)
        total_fired = sum(len(v) for v in results.values())
        for name, triggers in results.items():
            status = f"{len(triggers)} triggers" if triggers else "clean"
            print(f"  {name:<12} {status}")
        print(f"\n{len(results)} instances checked, {total_fired} triggers fired")
    else:
        fired = supervise_instance(args.name, window_minutes=window)
        if fired:
            for t in fired:
                print(f"  FIRED: {t['trigger']} — {t.get('timestamp', '')}")
        else:
            print(f"  {args.name}: clean")
    return 0


@logged
def cmd_smoke(args):
    """Run tier 2 smoke test against a live instance."""
    from .smoke import run_smoke

    print(f"smoke test: {args.name}")
    print("─" * 40)
    result = run_smoke(args.name, timeout=args.timeout)
    print("─" * 40)
    print(f"result: {result.summary()}")
    return 0 if result.passed else 1


@logged
def cmd_behavioral_smoke(args):
    """Run behavioral smoke tests — verify agents follow operating instructions.

    Burns tokens. Tests real agent reasoning. Acceptance: >95% success rate.
    """
    from .behavioral_smoke import run_behavioral_smoke, SCENARIO_REGISTRY

    # Handle --list flag
    if getattr(args, "list", False):
        print("Available scenarios:")
        print(
            f"{'ID':<6} {'NAME':<25} {'PHASE':<15} {'CAP':<6} {'RUNS':<5} DESCRIPTION"
        )
        print("-" * 100)
        for sid, (meta, _) in sorted(SCENARIO_REGISTRY.items()):
            req = ""
            if meta.requires_main:
                req = " (main only)"
            elif meta.requires_microhal:
                req = " (microHAL only)"
            print(
                f"{meta.id:<6} {meta.name:<25} {meta.phase.name:<15} "
                f"{meta.capability.value:<6} {meta.default_runs:<5} {meta.description[:40]}{req}"
            )
        return 0

    # Name is required if not --list
    if not args.name:
        print("ERROR: instance name required (or use --list)", file=sys.stderr)
        sys.exit(1)

    # Parse scenario/phase/capability filters
    scenario_ids = None
    if args.scenario:
        scenario_ids = [s.strip().upper() for s in args.scenario.split(",")]

    phases = None
    if args.phase:
        phases = [int(p.strip()) for p in args.phase.split(",")]

    capabilities = None
    if args.capability:
        capabilities = [c.strip().upper() for c in args.capability.split(",")]

    result = run_behavioral_smoke(
        name=args.name,
        runs_per_scenario=args.runs if args.runs else None,
        timeout=args.timeout,
        threshold=args.threshold,
        scenario_ids=scenario_ids,
        phases=phases,
        capabilities=capabilities,
    )
    return 0 if result.passed else 1


@logged
def cmd_push(args):
    """Push code updates from prime to microHAL instance(s)."""
    if args.all:
        from .provision import push_all

        pushed = push_all()
        if not pushed:
            print("no active instances to push")
        else:
            for name in pushed:
                print(f"pushed  {name}")
    else:
        if not args.name:
            print("ERROR: specify --name or --all", file=sys.stderr)
            sys.exit(1)
        from .provision import push_instance

        try:
            push_instance(args.name)
            print(f"pushed  {args.name}")
        except (ValueError, FileNotFoundError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    return 0


# ---------------------------------------------------------------------------
# Recon & Ops Commands
# ---------------------------------------------------------------------------


@logged
def cmd_ps(args):
    """Fleet process table via pm2."""
    try:
        result = subprocess.run(
            ["npx", "pm2", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(result.stdout)
        if result.stderr and "error" in result.stderr.lower():
            print(result.stderr, file=sys.stderr)
    except FileNotFoundError:
        print("ERROR: pm2 not found", file=sys.stderr)
        return 1
    return 0


@logged
def cmd_logs(args):
    """Tail pm2 + container logs for an instance."""
    pm2_name = (
        f"microhal-{args.name}" if not args.name.startswith("microhal-") else args.name
    )
    pm2_log = Path.home() / ".pm2" / "logs" / f"{pm2_name}-out.log"
    pm2_err = Path.home() / ".pm2" / "logs" / f"{pm2_name}-error.log"

    n = args.lines

    if pm2_log.exists():
        print(f"=== pm2 stdout (last {n} lines) ===")
        _tail(pm2_log, n)
    else:
        print(f"no pm2 log at {pm2_log}")

    if pm2_err.exists():
        print(f"\n=== pm2 stderr (last {n} lines) ===")
        _tail(pm2_err, n)

    # Container logs
    from .config import load_fleet_manifest

    manifest = load_fleet_manifest()
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            deploy = Path(inst["path"])
            logs_dir = deploy / "groups" / "telegram_main" / "logs"
            if logs_dir.exists():
                logs = sorted(logs_dir.glob("container-*.log"), reverse=True)
                if logs:
                    print(f"\n=== latest container log ===")
                    _tail(logs[0], n)
            break
    return 0


@logged
def cmd_health(args):
    """Active health check — catches zombies, not just dead pids."""
    from .health import check_instance, check_all, auto_heal

    if args.name == "all":
        results = check_all()
        if not results:
            print("no active fleet instances")
            return 0

        print(f"{'INSTANCE':<12} {'STATUS':<8} {'DETAILS'}")
        print("─" * 80)
        failures = 0
        for r in results:
            print(r.summary_line())
            if not r.healthy:
                failures += 1
                hlog(
                    "halctl",
                    "error",
                    "health_alert",
                    {
                        "instance": r.instance,
                        "pid": r.pid,
                        "zombie": r.zombie,
                        "minutes_silent": r.minutes_silent,
                        "errors": r.errors,
                    },
                )
        print()
        print(
            f"{len(results)} checked, {len(results) - failures} healthy, {failures} unhealthy"
        )

        if failures and args.heal:
            restarted = auto_heal(results)
            if restarted:
                print(f"auto-healed: {', '.join(restarted)}")
            else:
                print("auto-heal: no instances could be restarted")

        return 1 if failures else 0
    else:
        r = check_instance(args.name)
        print(r.summary_line())
        if not r.healthy:
            hlog(
                "halctl",
                "error",
                "health_alert",
                {
                    "instance": r.instance,
                    "pid": r.pid,
                    "zombie": r.zombie,
                    "minutes_silent": r.minutes_silent,
                    "errors": r.errors,
                },
            )
            if args.heal:
                from .health import auto_heal

                restarted = auto_heal([r])
                if restarted:
                    print(f"auto-healed: {r.instance}")
        return 0 if r.healthy else 1


@logged
def cmd_messages(args):
    """Recent messages for an instance."""
    from .config import load_fleet_manifest
    import sqlite3

    manifest = load_fleet_manifest()
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            instance = inst
            break

    if instance is None:
        print(f"ERROR: instance '{args.name}' not found", file=sys.stderr)
        return 1

    db_path = Path(instance["path"]) / "store" / "messages.db"
    if not db_path.exists():
        print(f"no database at {db_path}")
        return 1

    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            """SELECT timestamp, sender_name, is_from_me,
                      substr(content, 1, 200) as content
               FROM messages ORDER BY timestamp DESC LIMIT ?""",
            (args.lines,),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("no messages")
        return 0

    for ts, sender, is_me, content in reversed(rows):
        direction = "→" if is_me else "←"
        content_clean = content.replace("\n", " ") if content else ""
        print(f"  {ts}  {direction} {sender or '?'}: {content_clean}")
    return 0


@logged
def cmd_restart(args):
    """Restart a fleet instance via pm2."""
    pm2_name = (
        f"microhal-{args.name}" if not args.name.startswith("microhal-") else args.name
    )
    try:
        result = subprocess.run(
            ["npx", "pm2", "restart", pm2_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            print(f"restarted {args.name}")
        else:
            print(f"ERROR: {result.stderr[:200]}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def _tail(path: Path, n: int = 30):
    """Print last n lines of a file."""
    try:
        lines = path.read_text(errors="replace").splitlines()
        for line in lines[-n:]:
            print(line)
    except Exception as e:
        print(f"  (read error: {e})")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="halctl",
        description="halctl — microHAL fleet management.",
    )

    sub = parser.add_subparsers(dest="subcommand")

    # create
    cr = sub.add_parser("create", help="Provision a new microHAL instance")
    cr.add_argument("--name", required=True, help="Instance name")
    cr.add_argument("--personality", default=None, help="Personality template name")

    # list
    sub.add_parser("list", help="List fleet instances")

    # status
    st = sub.add_parser("status", help="Instance details")
    st.add_argument("name", help="Instance name")

    # freeze
    fr = sub.add_parser("freeze", help="Stop process, preserve everything")
    fr.add_argument("name", help="Instance name")

    # fold
    fo = sub.add_parser("fold", help="Stop + archive data")
    fo.add_argument("name", help="Instance name")

    # fry
    fy = sub.add_parser("fry", help="Stop + wipe (nuclear)")
    fy.add_argument("name", help="Instance name")
    fy.add_argument(
        "--confirm", action="store_true", help="Required for destructive operation"
    )

    # reset
    rs = sub.add_parser(
        "reset", help="Nuclear reset: kill container, clear state, restart"
    )
    rs.add_argument("name", help="Instance name")

    # assess
    ass = sub.add_parser(
        "assess", help="Run assessment scenarios against a live instance"
    )
    ass.add_argument("name", help="Instance name")
    ass.add_argument("--scenario", default=None, help="Run a specific scenario")
    ass.add_argument(
        "--timeout", type=float, default=60.0, help="Agent response timeout"
    )

    # supervise
    sv = sub.add_parser("supervise", help="Run supervisor sweep (trigger detection)")
    sv.add_argument("name", nargs="?", default="all", help="Instance name or 'all'")
    sv.add_argument("--window", type=int, default=30, help="Lookback window in minutes")

    # smoke
    sm = sub.add_parser("smoke", help="Tier 2 smoke test against a live instance")
    sm.add_argument("name", help="Instance name")
    sm.add_argument(
        "--timeout", type=float, default=60.0, help="Agent response timeout in seconds"
    )

    # behavioral-smoke
    bs = sub.add_parser(
        "behavioral-smoke",
        help="Behavioral smoke tests (burns tokens, tests agent reasoning)",
    )
    bs.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Instance name ('prime' for HAL-prime, or microHAL instance name)",
    )
    bs.add_argument("--runs", type=int, default=None, help="Override runs per scenario")
    bs.add_argument(
        "--timeout", type=float, default=120.0, help="Agent response timeout in seconds"
    )
    bs.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Success rate threshold (default: 0.95)",
    )
    bs.add_argument(
        "--scenario",
        "-s",
        default=None,
        help="Specific scenarios (e.g., 'T1,M1' or 'T' for all task tests)",
    )
    bs.add_argument(
        "--phase",
        "-p",
        default=None,
        help="Phases to run: 1=core, 2=complementary, 3=auth, 4=onboarding (e.g., '1,2')",
    )
    bs.add_argument(
        "--capability",
        "-c",
        default=None,
        help="Capabilities: T=task, M=memory, F=format, C=command, A=auth, O=onboarding",
    )
    bs.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available scenarios and exit",
    )

    # push
    pu = sub.add_parser("push", help="Push code updates from prime")
    pu.add_argument("name", nargs="?", default=None, help="Instance name")
    pu.add_argument("--all", action="store_true", help="Push to all active instances")

    # --- Recon & Ops ---

    # ps
    sub.add_parser("ps", help="Fleet process table (pm2)")

    # logs
    lo = sub.add_parser("logs", help="Tail logs for an instance")
    lo.add_argument("name", help="Instance name")
    lo.add_argument("-n", "--lines", type=int, default=30, help="Number of lines")

    # health
    he = sub.add_parser("health", help="Active health check (catches zombies)")
    he.add_argument("name", nargs="?", default="all", help="Instance name or 'all'")
    he.add_argument(
        "--heal", action="store_true", help="Auto-restart unhealthy instances"
    )

    # messages
    ms = sub.add_parser("messages", help="Recent messages for an instance")
    ms.add_argument("name", help="Instance name")
    ms.add_argument("-n", "--lines", type=int, default=15, help="Number of messages")

    # restart
    re_ = sub.add_parser("restart", help="Restart a fleet instance via pm2")
    re_.add_argument("name", help="Instance name")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "create": cmd_create,
        "list": cmd_list,
        "status": cmd_status,
        "freeze": cmd_freeze,
        "fold": cmd_fold,
        "fry": cmd_fry,
        "reset": cmd_reset,
        "assess": cmd_assess,
        "smoke": cmd_smoke,
        "behavioral-smoke": cmd_behavioral_smoke,
        "supervise": cmd_supervise,
        "push": cmd_push,
        "ps": cmd_ps,
        "logs": cmd_logs,
        "health": cmd_health,
        "messages": cmd_messages,
        "restart": cmd_restart,
    }

    if args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args) or 0)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
