"""Daily digest formatter and Telegram delivery."""

import os
from pathlib import Path
from typing import Optional

import httpx

from .evaluate import Evaluation
from .feed import VideoEntry


VERDICT_EMOJI = {
    "REQUIRED": "🔴",
    "WATCH": "🟡",
    "SKIM": "🔵",
    "SKIP": "⚪",
}


def format_digest(results: list[tuple[VideoEntry, Evaluation]]) -> str:
    """Format a daily digest of video evaluations.

    Args:
        results: List of (video, evaluation) tuples from today's scan.

    Returns:
        Formatted text string for Telegram.
    """
    if not results:
        return "📺 *watchctl* — no new videos today."

    lines = ["📺 *watchctl daily digest*", ""]

    # Sort by verdict priority: REQUIRED > WATCH > SKIM > SKIP
    priority = {"REQUIRED": 0, "WATCH": 1, "SKIM": 2, "SKIP": 3}
    results.sort(key=lambda x: priority.get(x[1].verdict, 99))

    for video, ev in results:
        emoji = VERDICT_EMOJI.get(ev.verdict, "⚪")
        stars = "★" * int(ev.overall) + "☆" * (5 - int(ev.overall))

        lines.append(f"{emoji} *{ev.verdict}* {stars} ({ev.overall}/5)")
        lines.append(f"  _{video.title}_")
        lines.append(f"  {video.channel_name}")

        # Top goodies (HIGH tier only)
        high_goodies = [g for g in ev.goodies if g.get("tier") == "HIGH"]
        if high_goodies:
            for g in high_goodies[:3]:
                lines.append(f"  → {g['item'][:100]}")

        lines.append(f"  {video.url}")
        lines.append("")

    # Stats footer
    total = len(results)
    by_verdict = {}
    for _, ev in results:
        by_verdict[ev.verdict] = by_verdict.get(ev.verdict, 0) + 1
    stats = " | ".join(f"{v}: {c}" for v, c in sorted(by_verdict.items()))
    lines.append(f"_{total} videos evaluated — {stats}_")

    return "\n".join(lines)


def send_telegram(text: str, chat_id: Optional[str] = None) -> bool:
    """Send digest via Telegram Bot API.

    Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment or .env.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    # Try .env fallback
    if not token or not chat_id:
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() == "TELEGRAM_BOT_TOKEN" and not token:
                    token = v
                if k.strip() == "TELEGRAM_CHAT_ID" and not chat_id:
                    chat_id = v

    if not token or not chat_id:
        return False

    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            },
            timeout=15,
        )
        return r.json().get("ok", False)
    except Exception:
        return False
