"""engine — himalaya subprocess wrapper for mailctl.

Provides structured access to email via the himalaya CLI.
All methods return parsed Python objects (dicts/lists), never raw strings.
Supports multiple accounts (gmail, icloud) via the `account` parameter.

Requires: himalaya binary on PATH, configured accounts in ~/.config/himalaya/config.toml
"""

import json
import subprocess
from typing import Optional


ACCOUNTS = ("gmail", "icloud")
DEFAULT_ACCOUNT = "gmail"
HIMALAYA = "himalaya"


class HimalayaError(Exception):
    """Raised when himalaya exits non-zero."""

    def __init__(self, message: str, returncode: int, stderr: str):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def _run(
    args: list[str],
    account: str = DEFAULT_ACCOUNT,
    stdin: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Run himalaya with args, return stdout."""
    # -a and -o are per-subcommand flags in himalaya, append after args
    cmd = [HIMALAYA, *args, "-a", account, "-o", "json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise HimalayaError(
            f"himalaya -a {account} {' '.join(args)} failed: {result.stderr.strip()}",
            result.returncode,
            result.stderr,
        )
    return result.stdout


def _parse(raw: str) -> list[dict] | dict:
    """Parse JSON output from himalaya."""
    if not raw.strip():
        return []
    return json.loads(raw)


def list_messages(
    folder: str = "INBOX",
    page: int = 1,
    page_size: int = 25,
    account: str = DEFAULT_ACCOUNT,
) -> list[dict]:
    """List messages in a folder."""
    raw = _run(
        ["envelope", "list", "--folder", folder, "-p", str(page), "-s", str(page_size)],
        account=account,
    )
    return _parse(raw)


def read_message(
    message_id: str,
    folder: str = "INBOX",
    account: str = DEFAULT_ACCOUNT,
) -> dict:
    """Read a single message by ID."""
    raw = _run(["message", "read", "--folder", folder, message_id], account=account)
    return _parse(raw)


def search(
    query: str,
    folder: str = "INBOX",
    account: str = DEFAULT_ACCOUNT,
) -> list[dict]:
    """Search messages. Query uses IMAP search syntax."""
    raw = _run(
        ["envelope", "list", "--folder", folder, *query.split()],
        account=account,
    )
    return _parse(raw)


def send(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    account: str = DEFAULT_ACCOUNT,
) -> None:
    """Compose and send a message."""
    headers = f"To: {to}\nSubject: {subject}\n"
    if cc:
        headers += f"Cc: {cc}\n"
    headers += f"\n{body}"
    _run(["message", "send"], account=account, stdin=headers)


def move(
    message_id: str,
    dest: str,
    folder: str = "INBOX",
    account: str = DEFAULT_ACCOUNT,
) -> None:
    """Move a message to another folder."""
    _run(["message", "move", "--folder", folder, dest, message_id], account=account)


def flag(
    message_id: str,
    flag: str = "seen",
    folder: str = "INBOX",
    account: str = DEFAULT_ACCOUNT,
) -> None:
    """Add a flag to a message."""
    _run(["flag", "add", "--folder", folder, message_id, flag], account=account)


def folders(account: str = DEFAULT_ACCOUNT) -> list[dict]:
    """List all folders/labels."""
    raw = _run(["folder", "list"], account=account)
    return _parse(raw)
