"""watchctl CLI — YouTube channel monitor with LLM-as-judge triage.

Usage:
    watchctl scan                  # full pipeline: fetch → evaluate → write
    watchctl scan --dry-run        # show what would be evaluated
    watchctl scan --channel "Theo" # single channel only
    watchctl channels              # list configured channels
    watchctl list [--days N]       # list recent evaluations
    watchctl stats                 # cost tracking, score distributions
"""

import argparse
import json
import sys

from halos.common.log import hlog

from .config import load_config
from .feed import fetch_channel_feed, FeedError
from .transcript import fetch_transcript, TranscriptError
from .rubric import load_rubric
from .evaluate import evaluate, EvalError
from .obsidian import write_note
from .digest import format_digest, send_telegram
from . import store


def cmd_scan(args, cfg):
    """Run full scan pipeline."""
    rubric = load_rubric(cfg.rubric_path)
    store.init(cfg.db_path)

    channels = cfg.channels
    if args.channel:
        channels = [c for c in channels if args.channel.lower() in c.name.lower()]
        if not channels:
            print(f"No channel matching '{args.channel}'")
            return 1

    results = []  # (VideoEntry, Evaluation) for digest
    new_count = 0
    skip_count = 0
    fail_count = 0

    for channel in channels:
        hlog("watchctl", "info", "scan_channel", {"channel": channel.name})

        # Fetch RSS feed
        try:
            videos = fetch_channel_feed(channel.youtube_id)
        except FeedError as e:
            hlog("watchctl", "error", "feed_error", {
                "channel": channel.name, "error": str(e),
            })
            store.log_failure(
                cfg.db_path, "FEED_ERROR", str(e),
                channel_id=channel.youtube_id,
            )
            fail_count += 1
            continue

        for video in videos:
            # Skip already-seen videos
            if store.is_seen(cfg.db_path, video.video_id):
                skip_count += 1
                continue

            if args.dry_run:
                print(f"  [NEW] {video.title} ({video.published.date()})")
                new_count += 1
                # Mark seen even in dry-run? No — dry-run is read-only.
                continue

            hlog("watchctl", "info", "eval_video", {
                "video_id": video.video_id, "title": video.title,
            })

            # Fetch transcript
            try:
                transcript = fetch_transcript(
                    video.video_id,
                    max_chars=cfg.max_transcript_chars,
                )
            except TranscriptError as e:
                hlog("watchctl", "warn", "transcript_error", {
                    "video_id": video.video_id, "error_type": e.error_type,
                })
                store.log_failure(
                    cfg.db_path, e.error_type, str(e),
                    video_id=video.video_id, channel_id=channel.youtube_id,
                )
                # Mark seen so we don't retry endlessly
                store.mark_seen(
                    cfg.db_path, video.video_id, channel.youtube_id,
                    channel.name, video.title,
                    video.published.isoformat(), video.url,
                )
                fail_count += 1
                continue

            # Evaluate
            try:
                ev = evaluate(video, transcript, rubric, model=cfg.model)
            except EvalError as e:
                hlog("watchctl", "error", "eval_error", {
                    "video_id": video.video_id, "error_type": e.error_type,
                })
                store.log_failure(
                    cfg.db_path, e.error_type, str(e),
                    video_id=video.video_id, channel_id=channel.youtube_id,
                )
                store.mark_seen(
                    cfg.db_path, video.video_id, channel.youtube_id,
                    channel.name, video.title,
                    video.published.isoformat(), video.url,
                )
                fail_count += 1
                continue

            # Write Obsidian note
            note_path = write_note(cfg.vault_output_path, video, ev)
            hlog("watchctl", "info", "note_written", {
                "path": str(note_path), "verdict": ev.verdict,
            })

            # Save to DB
            store.mark_seen(
                cfg.db_path, video.video_id, channel.youtube_id,
                channel.name, video.title,
                video.published.isoformat(), video.url,
            )
            store.save_evaluation(
                cfg.db_path,
                video_id=video.video_id,
                rubric_name=rubric.name,
                rubric_ver=rubric.version,
                scores=ev.scores,
                overall=ev.overall,
                verdict=ev.verdict,
                summary=ev.summary,
                goodies=ev.goodies,
                tags=ev.tags,
                model=ev.model,
                input_tokens=ev.input_tokens,
                output_tokens=ev.output_tokens,
                cost_usd=ev.cost_usd,
            )

            results.append((video, ev))
            new_count += 1

    # Summary
    print(f"Scan complete: {new_count} new, {skip_count} seen, {fail_count} failed")

    if args.dry_run:
        return 0

    # Send digest
    if results and cfg.telegram_enabled:
        digest_text = format_digest(results)
        sent = send_telegram(digest_text)
        if sent:
            hlog("watchctl", "info", "digest_sent", {"count": len(results)})
            print(f"Telegram digest sent ({len(results)} videos)")
        else:
            hlog("watchctl", "warn", "digest_failed", {})
            print("Telegram digest failed — check token/chat_id")
            # Print to stdout as fallback
            print("\n" + digest_text)
    elif results:
        # Telegram disabled — print digest
        print("\n" + format_digest(results))

    return 0


def cmd_channels(args, cfg):
    """List configured channels."""
    for ch in cfg.channels:
        tags = ", ".join(ch.tags) if ch.tags else "—"
        print(f"  {ch.name}")
        print(f"    ID:   {ch.youtube_id}")
        print(f"    Tags: {tags}")
        print()
    return 0


def cmd_list(args, cfg):
    """List recent evaluations."""
    store.init(cfg.db_path)
    days = args.days or 7
    evals = store.recent_evaluations(cfg.db_path, days=days)

    if not evals:
        print(f"No evaluations in the last {days} days.")
        return 0

    for e in evals:
        verdict = e["verdict"]
        stars = "★" * int(e["overall"]) + "☆" * (5 - int(e["overall"]))
        print(f"  {verdict:8s} {stars} ({e['overall']:.1f})  {e['title']}")
        print(f"           {e['channel_name']}  {e['url']}")
        print()

    if args.json_out:
        print(json.dumps(evals, indent=2, default=str))

    return 0


def cmd_stats(args, cfg):
    """Show cost tracking and score distributions."""
    store.init(cfg.db_path)
    stats = store.get_stats(cfg.db_path)

    ev = stats["evaluations"]
    print("=== Evaluation Stats ===")
    print(f"  Total evaluations: {ev.get('count', 0)}")
    print(f"  Avg score:         {ev.get('avg_score', 0):.1f}")
    print(f"  Total cost:        ${ev.get('total_cost', 0):.4f}")
    print(f"  Total tokens:      {ev.get('total_input', 0):,} in / {ev.get('total_output', 0):,} out")
    print()

    print("=== Verdicts ===")
    for v, c in sorted(stats["verdicts"].items()):
        print(f"  {v}: {c}")
    print()

    if stats["failures"]:
        print("=== Failures ===")
        for t, c in sorted(stats["failures"].items()):
            print(f"  {t}: {c}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="watchctl",
        description="watchctl — YouTube channel monitor with LLM-as-judge triage",
    )
    parser.add_argument("--config", default=None, help="Path to watchctl.yaml")
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan channels for new videos")
    p_scan.add_argument("--dry-run", action="store_true",
                        help="Show new videos without evaluating")
    p_scan.add_argument("--channel", default=None,
                        help="Filter to a specific channel name")

    # channels
    sub.add_parser("channels", help="List configured channels")

    # list
    p_list = sub.add_parser("list", help="List recent evaluations")
    p_list.add_argument("--days", type=int, default=7,
                        help="Look back N days (default: 7)")
    p_list.add_argument("--json", action="store_true", dest="json_out")

    # stats
    sub.add_parser("stats", help="Cost tracking and score distributions")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cfg = load_config(args.config)

    commands = {
        "scan": cmd_scan,
        "channels": cmd_channels,
        "list": cmd_list,
        "stats": cmd_stats,
    }

    sys.exit(commands[args.command](args, cfg))
