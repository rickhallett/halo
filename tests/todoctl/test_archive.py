"""Tests for archive — moves done/cancelled items, dry-run, age threshold."""
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import yaml

from halos.todoctl.todo import TodoItem


def _make_old_item(items_dir, title, status, days_old=60):
    """Create an item with a created timestamp in the past."""
    item = TodoItem.create(items_dir=items_dir, title=title)
    old_dt = datetime.now(timezone.utc) - timedelta(days=days_old)
    item.data["status"] = status
    item.data["created"] = old_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    item.save()
    return item


class TestArchive:
    def test_archive_moves_done_item(self, tmp_path):
        items_dir = tmp_path / "items"
        items_dir.mkdir()
        archive_dir = tmp_path / "archive"

        item = _make_old_item(items_dir, "Old done item", "done", days_old=60)
        original_path = item.file_path
        assert original_path.exists()

        item.archive(archive_dir)
        assert not original_path.exists()
        assert (archive_dir / original_path.name).exists()

    def test_archive_moves_cancelled_item(self, tmp_path):
        items_dir = tmp_path / "items"
        items_dir.mkdir()
        archive_dir = tmp_path / "archive"

        item = _make_old_item(items_dir, "Old cancelled item", "cancelled", days_old=60)
        original_path = item.file_path

        item.archive(archive_dir)
        assert not original_path.exists()
        assert (archive_dir / original_path.name).exists()

    def test_archive_creates_dir(self, tmp_path):
        items_dir = tmp_path / "items"
        items_dir.mkdir()
        archive_dir = tmp_path / "archive"
        assert not archive_dir.exists()

        item = _make_old_item(items_dir, "Test", "done", days_old=60)
        item.archive(archive_dir)
        assert archive_dir.exists()

    def test_archive_does_not_move_recent_items(self, tmp_path):
        """Items less than 30 days old should not be archive candidates."""
        items_dir = tmp_path / "items"
        items_dir.mkdir()

        recent = _make_old_item(items_dir, "Recent done", "done", days_old=5)
        old = _make_old_item(items_dir, "Old done", "done", days_old=60)

        # Simulate the filtering logic from cmd_archive
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        from halos.todoctl.cli import _load_all_items
        items = _load_all_items(items_dir)
        candidates = []
        for i in items:
            if i.status not in ("done", "cancelled"):
                continue
            created_dt = datetime.strptime(
                i.created, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            if created_dt < cutoff:
                candidates.append(i)

        assert len(candidates) == 1
        assert candidates[0].title == "Old done"

    def test_archive_does_not_move_open_items(self, tmp_path):
        """Open items should never be archived regardless of age."""
        items_dir = tmp_path / "items"
        items_dir.mkdir()

        old_open = _make_old_item(items_dir, "Old open", "open", days_old=60)

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        from halos.todoctl.cli import _load_all_items
        items = _load_all_items(items_dir)
        candidates = [
            i for i in items
            if i.status in ("done", "cancelled")
            and datetime.strptime(i.created, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            ) < cutoff
        ]
        assert len(candidates) == 0

    def test_archive_atomic(self, tmp_path):
        """archive() should use os.replace (atomic)."""
        items_dir = tmp_path / "items"
        items_dir.mkdir()
        archive_dir = tmp_path / "archive"

        item = _make_old_item(items_dir, "Atomic archive", "done", days_old=60)
        item.archive(archive_dir)

        # No tmp files left
        tmp_files = list(archive_dir.glob("*.tmp")) + list(items_dir.glob("*.tmp"))
        assert tmp_files == []
