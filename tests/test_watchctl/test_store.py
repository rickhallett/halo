"""Tests for watchctl SQLite store."""

import tempfile
from pathlib import Path

import pytest

from halos.watchctl import store


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_watch.db"
    store._conn = None  # Reset global
    store.init(path)
    yield path
    store.close()


def test_mark_and_check_seen(db_path):
    assert not store.is_seen(db_path, "vid1")
    store.mark_seen(db_path, "vid1", "ch1", "Channel", "Title", "2026-03-27", "https://yt/vid1")
    assert store.is_seen(db_path, "vid1")


def test_mark_seen_idempotent(db_path):
    store.mark_seen(db_path, "vid1", "ch1", "Channel", "Title", "2026-03-27", "https://yt/vid1")
    store.mark_seen(db_path, "vid1", "ch1", "Channel", "Title", "2026-03-27", "https://yt/vid1")
    assert store.is_seen(db_path, "vid1")


def test_save_and_retrieve_evaluation(db_path):
    store.mark_seen(db_path, "vid1", "ch1", "Channel", "Title", "2026-03-27", "https://yt/vid1")
    row_id = store.save_evaluation(
        db_path, "vid1", "test-rubric", 1,
        {"sig": {"score": 4, "note": "good"}},
        4.0, "REQUIRED", "Summary text",
        [{"tier": "HIGH", "item": "thing"}],
        ["tag1"], "test-model",
    )
    assert row_id > 0

    evals = store.recent_evaluations(db_path, days=1)
    assert len(evals) == 1
    assert evals[0]["verdict"] == "REQUIRED"


def test_log_failure(db_path):
    store.log_failure(db_path, "FEED_ERROR", "Connection refused", channel_id="ch1")
    stats = store.get_stats(db_path)
    assert stats["failures"]["FEED_ERROR"] == 1


def test_stats_empty(db_path):
    stats = store.get_stats(db_path)
    assert stats["evaluations"]["count"] == 0
