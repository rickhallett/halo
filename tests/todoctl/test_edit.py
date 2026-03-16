"""Tests for edit command — only specified fields change."""
from pathlib import Path

import pytest

from halos.todoctl.todo import TodoItem


class TestEdit:
    def _create_item(self, tmp_path):
        return TodoItem.create(
            items_dir=tmp_path,
            title="Original title",
            priority=3,
            tags=["dev"],
            context="original context",
            due="2026-01-01",
            entities=["project-a"],
        )

    def test_edit_title(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["title"] = "New title"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.title == "New title"
        assert reloaded.priority == 3  # unchanged
        assert reloaded.tags == ["dev"]  # unchanged

    def test_edit_priority(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["priority"] = 1
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.priority == 1
        assert reloaded.title == "Original title"  # unchanged

    def test_edit_tags_replaces(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["tags"] = ["ops", "infra"]
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.tags == ["ops", "infra"]

    def test_edit_context(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["context"] = "new context"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.data["context"] == "new context"

    def test_edit_entities(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["entities"] = ["project-b", "project-c"]
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.data["entities"] == ["project-b", "project-c"]

    def test_edit_only_specified_fields(self, tmp_path):
        """When editing one field, all others remain untouched."""
        item = self._create_item(tmp_path)
        original_data = dict(item.data)
        item.data["due"] = "2026-12-31"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.data["due"] == "2026-12-31"
        # Everything else unchanged
        assert reloaded.title == original_data["title"]
        assert reloaded.priority == original_data["priority"]
        assert reloaded.tags == original_data["tags"]
        assert reloaded.data["context"] == original_data["context"]
        assert reloaded.data["entities"] == original_data["entities"]

    def test_edit_preserves_atomic_write(self, tmp_path):
        item = self._create_item(tmp_path)
        item.data["title"] = "Edited"
        item.save()
        # No .tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
