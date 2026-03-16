"""Tests for adversarial review fixes in todoctl."""
import os
import time
from pathlib import Path

import pytest
import yaml

from halos.todoctl.todo import VALID_STATUSES, TodoItem, ValidationError, _now_id


class TestAtomicWrite:
    """H1: save() should use atomic write (write to .tmp then os.replace)."""

    def test_save_no_tmp_leftover(self, tmp_path):
        item = TodoItem.create(items_dir=tmp_path, title="Atomic test")
        # After save, no .tmp file should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_save_writes_correct_content(self, tmp_path):
        item = TodoItem.create(items_dir=tmp_path, title="Content check")
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.title == "Content check"


class TestMillisecondIds:
    """H3: IDs should include milliseconds to prevent collision on rapid creation."""

    def test_id_has_millisecond_suffix(self):
        id_str = _now_id()
        # Format: YYYYMMDD-HHMMSS-NNN
        parts = id_str.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 3  # milliseconds: 3 digits
        assert parts[2].isdigit()

    def test_rapid_create_unique_ids(self, tmp_path):
        """Two items created in rapid succession should have different IDs."""
        item1 = TodoItem.create(items_dir=tmp_path, title="First")
        item2 = TodoItem.create(items_dir=tmp_path, title="Second")
        assert item1.id != item2.id or item1.file_path != item2.file_path


class TestValidationOnLoad:
    """H2: from_file() should validate and reject corrupt YAML."""

    def test_missing_id_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"title": "no id", "status": "open", "priority": 3}))
        with pytest.raises(ValueError, match="id is required"):
            TodoItem.from_file(p)

    def test_missing_title_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"id": "123", "status": "open", "priority": 3}))
        with pytest.raises(ValueError, match="title is required"):
            TodoItem.from_file(p)

    def test_invalid_status_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"id": "123", "title": "T", "status": "bogus", "priority": 3}))
        with pytest.raises(ValueError, match="invalid status"):
            TodoItem.from_file(p)

    def test_bool_priority_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"id": "123", "title": "T", "status": "open", "priority": True}))
        with pytest.raises(ValueError, match="priority must be int"):
            TodoItem.from_file(p)

    def test_valid_file_passes(self, tmp_path):
        p = tmp_path / "good.yaml"
        p.write_text(yaml.dump({
            "id": "123", "title": "Good Item",
            "status": "open", "priority": 2,
        }))
        item = TodoItem.from_file(p)
        assert item.id == "123"


class TestLoadAllWarnings:
    """H14: _load_all_items should warn on stderr, not swallow silently."""

    def test_corrupt_file_warns_on_stderr(self, tmp_path, capsys):
        # Write a valid item
        TodoItem.create(items_dir=tmp_path, title="Valid item")
        # Write a corrupt item
        (tmp_path / "zzz-corrupt.yaml").write_text("not: valid\nno_id: true\n")

        from halos.todoctl.cli import _load_all_items
        items = _load_all_items(tmp_path)
        captured = capsys.readouterr()
        assert "WARN" in captured.err
        assert len(items) == 1  # only the valid one loaded
