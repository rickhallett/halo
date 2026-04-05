"""journalctl configuration and path resolution."""

from halos.common.paths import repo_root

REPO_ROOT = repo_root()
DB_PATH = REPO_ROOT / "store" / "journal.db"
CACHE_DIR = REPO_ROOT / "store" / "journal-cache"

DEFAULT_WINDOW_DAYS = 7
DEFAULT_MONTH_DAYS = 30
