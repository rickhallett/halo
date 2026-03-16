"""Tests for entities field on todo items."""
from pathlib import Path

import pytest

from halos.todoctl.todo import TodoItem


class TestEntities:
    def test_create_with_entities(self, tmp_path):
        item = TodoItem.create(
            items_dir=tmp_path,
            title="Entity test",
            entities=["user-alice", "project-x"],
        )
        assert item.data["entities"] == ["user-alice", "project-x"]

    def test_create_without_entities_defaults_empty(self, tmp_path):
        item = TodoItem.create(items_dir=tmp_path, title="No entities")
        assert item.data["entities"] == []

    def test_entities_persisted_to_file(self, tmp_path):
        item = TodoItem.create(
            items_dir=tmp_path,
            title="Persist test",
            entities=["org-acme"],
        )
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.data["entities"] == ["org-acme"]

    def test_entities_roundtrip(self, tmp_path):
        item = TodoItem.create(
            items_dir=tmp_path,
            title="Roundtrip",
            entities=["a", "b", "c"],
        )
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.data["entities"] == ["a", "b", "c"]
