#!/usr/bin/env python3
"""
Gemini CLI ↔ Telegram bridge.

Thin polling loop: receives Telegram messages, pipes them to `gemini -p`,
returns the output. No session management, no IPC, no Hermes.

Env:
    TELEGRAM_BOT_TOKEN  — from BotFather
    TELEGRAM_ALLOWED_USERS — comma-separated user IDs (optional, unrestricted if unset)
    GEMINI_SYSTEM_PROMPT — path to system prompt file (default: ./GEMINI.md)
    GEMINI_MODEL — model override (default: gemini-2.5-pro)
    GEMINI_WORK_DIR — cwd for gemini process (default: .)
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from same directory as this script
load_dotenv(Path(__file__).parent / ".env")

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("gemini-bridge")

# --- Config ---

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS: set[int] | None = None
_allowed = os.environ.get("TELEGRAM_ALLOWED_USERS", "").strip()
if _allowed:
    ALLOWED_USERS = {int(uid.strip()) for uid in _allowed.split(",")}

SYSTEM_PROMPT_PATH = Path(os.environ.get("GEMINI_SYSTEM_PROMPT", "./GEMINI.md"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# cwd for gemini — defaults to this script's directory (where GEMINI.md lives)
WORK_DIR = Path(os.environ.get("GEMINI_WORK_DIR", str(Path(__file__).parent))).resolve()
# repo root — for finding the halos venv
REPO_ROOT = Path(os.environ.get("HALO_REPO_ROOT", str(Path(__file__).parent.parent.parent))).resolve()
GEMINI_BIN = shutil.which("gemini")
YOLO = os.environ.get("GEMINI_YOLO", "1").lower() in {"1", "true", "yes"}

# Telegram message length limit
TG_MAX_LEN = 4096


def _check_prerequisites():
    if not GEMINI_BIN:
        log.error("gemini CLI not found on PATH")
        sys.exit(1)
    if not SYSTEM_PROMPT_PATH.exists():
        log.warning("System prompt not found at %s — running without persona", SYSTEM_PROMPT_PATH)
    log.info("Gemini binary: %s", GEMINI_BIN)
    log.info("Model: %s", MODEL)
    log.info("Work dir: %s", WORK_DIR)
    log.info("System prompt: %s", SYSTEM_PROMPT_PATH if SYSTEM_PROMPT_PATH.exists() else "(none)")
    log.info("Allowed users: %s", ALLOWED_USERS or "unrestricted")


def _is_allowed(user_id: int) -> bool:
    return ALLOWED_USERS is None or user_id in ALLOWED_USERS


async def _run_gemini(prompt: str) -> str:
    """Run gemini CLI in headless mode and return output."""
    cmd = [GEMINI_BIN, "-p", prompt, "-m", MODEL, "-o", "text"]
    if YOLO:
        cmd.insert(1, "--yolo")

    # Gemini reads GEMINI.md from cwd. We point cwd at the bridge dir for
    # the persona, but set PATH so halos tools are available.

    env = os.environ.copy()
    # Ensure sandbox mode is off for local testing
    env.pop("GEMINI_SANDBOX", None)

    # Add halos venv to PATH so gemini shell tools can call trackctl, nightctl, etc.
    halos_venv_bin = REPO_ROOT / ".venv" / "bin"
    if halos_venv_bin.exists():
        env["PATH"] = f"{halos_venv_bin}:{env.get('PATH', '')}"
    # Ensure HALO_STORE_DIR is set for halos tools
    if "HALO_STORE_DIR" not in env:
        env["HALO_STORE_DIR"] = str(REPO_ROOT / "store")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORK_DIR),
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            log.error("gemini exited %d: %s", proc.returncode, err)
            # Filter out the "Loaded cached credentials" and "Skill" noise lines
            if output:
                return output
            return f"[gemini error {proc.returncode}] {err[:500]}"

        # Filter common gemini CLI noise from output
        lines = output.split("\n")
        filtered = [
            l for l in lines
            if not l.startswith("Loaded cached credentials")
            and not l.startswith("Skill ")
            and not l.startswith("Using ")
        ]
        return "\n".join(filtered).strip() or "(empty response)"

    except asyncio.TimeoutError:
        log.error("gemini timed out after 120s")
        try:
            proc.kill()
        except Exception:
            pass
        return "[timeout] gemini did not respond within 120 seconds"
    except Exception as e:
        log.exception("gemini invocation failed")
        return f"[error] {e}"


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "Gemini bridge online. Send a message and I'll route it through Gemini CLI."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not _is_allowed(user.id):
        log.warning("Rejected message from unauthorized user %d (%s)", user.id, user.username)
        return

    text = update.message.text
    if not text:
        return

    log.info("← [%s] %s", user.username, text[:100])

    # Send typing indicator
    await update.message.chat.send_action("typing")

    response = await _run_gemini(text)

    log.info("→ [%s] %d chars", user.username, len(response))

    # Split long responses
    if len(response) <= TG_MAX_LEN:
        await update.message.reply_text(response)
    else:
        for i in range(0, len(response), TG_MAX_LEN):
            chunk = response[i : i + TG_MAX_LEN]
            await update.message.reply_text(chunk)


def main():
    _check_prerequisites()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Starting Telegram polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
