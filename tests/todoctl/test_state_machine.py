"""Tests for the todoctl state machine — valid/invalid transitions."""
from pathlib import Path

import pytest

from halos.todoctl.todo import (
    VALID_TRANSITIONS,
    VALID_STATUSES,
    TodoItem,
    TransitionError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(tmp_path: Path, status: str = "open") -> TodoItem:
    item = TodoItem.create(items_dir=tmp_path, title="State machine test")
    item.data["status"] = status
    item.save()
    return item


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------

class TestValidTransitions:
    """Every edge in the transition graph should succeed."""

    @pytest.mark.parametrize("src,dst", [
        ("open", "in-progress"),
        ("open", "cancelled"),
        ("open", "deferred"),
        ("in-progress", "review"),
        ("in-progress", "blocked"),
        ("in-progress", "cancelled"),
        ("review", "in-progress"),
        ("review", "testing"),
        ("review", "done"),
        ("testing", "in-progress"),
        ("testing", "done"),
        ("blocked", "in-progress"),
        ("blocked", "cancelled"),
        ("deferred", "open"),
        ("deferred", "cancelled"),
    ])
    def test_valid_transition(self, tmp_path, src, dst):
        item = _make_item(tmp_path, src)
        item.transition(dst)
        assert item.status == dst

    def test_transition_persists(self, tmp_path):
        item = _make_item(tmp_path, "open")
        item.transition("in-progress")
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "in-progress"


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

class TestInvalidTransitions:
    """Forbidden edges must raise TransitionError with the right message."""

    @pytest.mark.parametrize("src,dst", [
        ("open", "done"),
        ("open", "testing"),
        ("open", "review"),
        ("open", "blocked"),
        ("done", "open"),
        ("done", "in-progress"),
        ("done", "cancelled"),
        ("cancelled", "open"),
        ("cancelled", "in-progress"),
        ("cancelled", "done"),
        ("testing", "open"),
        ("testing", "blocked"),
        ("testing", "review"),
        ("in-progress", "done"),
        ("in-progress", "open"),
        ("in-progress", "deferred"),
        ("review", "cancelled"),
        ("review", "blocked"),
        ("blocked", "done"),
        ("blocked", "open"),
        ("deferred", "in-progress"),
        ("deferred", "done"),
    ])
    def test_invalid_transition_raises(self, tmp_path, src, dst):
        item = _make_item(tmp_path, src)
        with pytest.raises(TransitionError, match=f"Cannot transition from {src} to {dst}"):
            item.transition(dst)
        # status unchanged
        assert item.status == src


# ---------------------------------------------------------------------------
# Error message format
# ---------------------------------------------------------------------------

class TestErrorMessage:
    def test_error_lists_valid_transitions(self, tmp_path):
        item = _make_item(tmp_path, "open")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("done")
        msg = str(exc_info.value)
        assert "Valid transitions:" in msg
        assert "in-progress" in msg
        assert "cancelled" in msg
        assert "deferred" in msg

    def test_terminal_state_error(self, tmp_path):
        item = _make_item(tmp_path, "done")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("open")
        msg = str(exc_info.value)
        assert "terminal state" in msg


# ---------------------------------------------------------------------------
# Modified timestamp
# ---------------------------------------------------------------------------

class TestTransitionTimestamp:
    def test_transition_sets_modified(self, tmp_path):
        item = _make_item(tmp_path, "open")
        assert item.data.get("modified") is None
        item.transition("in-progress")
        assert item.data["modified"] is not None
        assert "T" in item.data["modified"]  # ISO format

    def test_modified_updates_on_each_transition(self, tmp_path):
        item = _make_item(tmp_path, "open")
        item.transition("in-progress")
        first = item.data["modified"]
        item.transition("review")
        second = item.data["modified"]
        assert second >= first


# ---------------------------------------------------------------------------
# VALID_STATUSES completeness
# ---------------------------------------------------------------------------

class TestStatusCompleteness:
    def test_all_statuses_present(self):
        expected = {"open", "in-progress", "review", "testing", "done", "blocked", "deferred", "cancelled"}
        assert set(VALID_STATUSES) == expected

    def test_transitions_cover_all_statuses(self):
        assert set(VALID_TRANSITIONS.keys()) == set(VALID_STATUSES)
