"""Tests for cancel command and cancelled status."""
from pathlib import Path

import pytest
import yaml

from halos.todoctl.todo import VALID_STATUSES, TodoItem


class TestCancelledStatus:
    def test_cancelled_in_valid_statuses(self):
        assert "cancelled" in VALID_STATUSES

    def test_cancel_sets_status(self, tmp_path):
        item = TodoItem.create(items_dir=tmp_path, title="Cancel me")
        item.data["status"] = "cancelled"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "cancelled"

    def test_cancelled_excluded_from_default_list(self, tmp_path):
        """Cancelled items should not appear in the default (non --all) listing."""
        TodoItem.create(items_dir=tmp_path, title="Active item")
        cancelled = TodoItem.create(items_dir=tmp_path, title="Cancelled item")
        cancelled.data["status"] = "cancelled"
        cancelled.save()

        from halos.todoctl.cli import _load_all_items
        items = _load_all_items(tmp_path)
        active = [i for i in items if i.status in ("open", "in-progress", "blocked")]
        assert len(active) == 1
        assert active[0].title == "Active item"

    def test_cancelled_appears_in_all_list(self, tmp_path):
        """Cancelled items should appear when --all is used."""
        TodoItem.create(items_dir=tmp_path, title="Active item")
        cancelled = TodoItem.create(items_dir=tmp_path, title="Cancelled item")
        cancelled.data["status"] = "cancelled"
        cancelled.save()

        from halos.todoctl.cli import _load_all_items
        items = _load_all_items(tmp_path)
        assert len(items) == 2

    def test_cancel_from_file_validates(self, tmp_path):
        p = tmp_path / "item.yaml"
        p.write_text(yaml.dump({
            "id": "123", "title": "T", "status": "cancelled", "priority": 3,
        }))
        item = TodoItem.from_file(p)
        assert item.status == "cancelled"
