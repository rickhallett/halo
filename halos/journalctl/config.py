"""journalctl configuration and path resolution."""

from pathlib import Path


def _repo_root() -> Path:
    """Walk up from this file to find the repo root (where store/ lives)."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "store").is_dir():
            return ancestor
    return Path.cwd()


REPO_ROOT = _repo_root()
DB_PATH = REPO_ROOT / "store" / "journal.db"
CACHE_DIR = REPO_ROOT / "store" / "journal-cache"

DEFAULT_WINDOW_DAYS = 7
DEFAULT_MONTH_DAYS = 30
