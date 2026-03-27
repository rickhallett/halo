"""Tests for watchctl obsidian note rendering."""

from datetime import datetime, timezone

from halos.watchctl.evaluate import Evaluation
from halos.watchctl.feed import VideoEntry
from halos.watchctl.obsidian import render_note, _slugify


def _make_video():
    return VideoEntry(
        video_id="abc123",
        title="Test Video Title",
        published=datetime(2026, 3, 27, tzinfo=timezone.utc),
        channel_name="Test Channel",
        channel_id="UCtest",
        url="https://www.youtube.com/watch?v=abc123",
    )


def _make_eval():
    return Evaluation(
        scores={
            "signal_density": {"score": 4, "note": "Good signal"},
            "actionability": {"score": 5, "note": "Very actionable"},
        },
        overall=4.2,
        verdict="REQUIRED",
        summary="A test summary of the video.",
        goodies=[
            {"tier": "HIGH", "item": "Key insight one"},
            {"tier": "MEDIUM", "item": "Decent insight"},
            {"tier": "LOW", "item": "Minor point"},
        ],
        tags=["engineering", "ai"],
        related_notes=["Related Note One"],
        model="test-model",
    )


def test_render_note_has_frontmatter():
    note = render_note(_make_video(), _make_eval())
    assert note.startswith("---")
    assert 'title: "Test Video Title"' in note
    assert "rating: 4.2" in note
    assert "verdict: REQUIRED" in note


def test_render_note_has_tags():
    note = render_note(_make_video(), _make_eval())
    assert '"youtube-monitor"' in note
    assert '"engineering"' in note


def test_render_note_has_score_table():
    note = render_note(_make_video(), _make_eval())
    assert "| Signal Density | 4/5 |" in note
    assert "| Actionability | 5/5 |" in note


def test_render_note_has_goodies():
    note = render_note(_make_video(), _make_eval())
    assert "### High Value" in note
    assert "Key insight one" in note
    assert "### Medium Value" in note
    assert "### Low Value" in note


def test_render_note_has_wikilinks():
    note = render_note(_make_video(), _make_eval())
    assert "[[Related Note One]]" in note


def test_slugify():
    assert _slugify("Hello World! This is a Test") == "hello-world-this-is-a-test"
    assert _slugify("Special @#$ Characters") == "special-characters"
    assert len(_slugify("A" * 200)) <= 80
