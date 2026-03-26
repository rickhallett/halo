"""Message delivery — direct Telegram bot API with IPC fallback."""
import json
import os
import time
from pathlib import Path

import httpx

from .config import Config


def _send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Send message directly via Telegram Bot API."""
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        return r.json().get("ok", False)
    except Exception:
        return False


def _get_bot_token() -> str:
    """Read bot token from environment or .env file."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        return token
    # Try .env in project root
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


def deliver_message(cfg: Config, text: str) -> Path:
    """Deliver a message via Telegram bot API, falling back to IPC.

    Returns the path of the archive/IPC file written.
    """
    if not cfg.chat_jid:
        raise RuntimeError(
            "No chat_jid configured — set it in briefings.yaml or ensure "
            "a main group is registered in the database"
        )

    chat_id = cfg.chat_jid.replace("tg:", "")
    token = _get_bot_token()

    # Try direct Telegram delivery first
    if token and chat_id:
        sent = _send_telegram(token, chat_id, text)
        if sent:
            # Still write IPC file as receipt/log
            return _write_ipc(cfg, text, delivered=True)

    # Fallback to IPC (requires gateway to be running)
    return _write_ipc(cfg, text, delivered=False)


def _write_ipc(cfg: Config, text: str, delivered: bool = False) -> Path:
    """Write an IPC message JSON file."""
    messages_dir = cfg.ipc_dir / cfg.ipc_group / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "type": "message",
        "chatJid": cfg.chat_jid,
        "text": text,
    }

    if delivered:
        payload["_delivered_direct"] = True

    # Timestamped filename to avoid collisions
    filename = f"briefing-{int(time.time() * 1000)}.json"
    filepath = messages_dir / filename

    # Atomic write: write to tmp then rename
    tmp = filepath.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(str(tmp), str(filepath))

    return filepath
