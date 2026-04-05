"""Shared path resolution for halos modules.

All store/data resolution should go through these helpers so that
containerised deployments (where HERMES_HOME points to /opt/data)
find the right directories regardless of Python install location.
"""

import os
from pathlib import Path


def store_dir() -> Path:
    """Resolve the store/ directory.

    Priority: HALO_STORE_DIR env > HERMES_HOME/store > repo root walk > cwd/store.
    """
    env = os.environ.get("HALO_STORE_DIR")
    if env:
        return Path(env)
    hermes = os.environ.get("HERMES_HOME")
    if hermes:
        p = Path(hermes) / "store"
        if p.is_dir():
            return p
    # Walk up from caller's file — but we don't know it here,
    # so fall back to cwd which is the repo root in dev and
    # HERMES_HOME in containers (entrypoint does cd).
    cwd_store = Path.cwd() / "store"
    if cwd_store.is_dir():
        return cwd_store
    return cwd_store  # Will be created on first write


def repo_root() -> Path:
    """Resolve the repository / data root.

    Priority: HERMES_HOME (if store/ exists there) > cwd.
    """
    hermes = os.environ.get("HERMES_HOME")
    if hermes:
        p = Path(hermes)
        if (p / "store").is_dir():
            return p
    return Path.cwd()
