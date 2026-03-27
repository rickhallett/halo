"""Tests for watchctl rubric loading and scoring."""

from pathlib import Path

import pytest

from halos.watchctl.rubric import load_rubric, Rubric


RUBRIC_PATH = Path(__file__).resolve().parents[2] / "rubrics" / "watchctl-triage.yaml"


@pytest.fixture
def rubric() -> Rubric:
    return load_rubric(RUBRIC_PATH)


def test_load_rubric(rubric):
    assert rubric.name == "engineering-relevance"
    assert rubric.version == 1
    assert len(rubric.criteria) == 4


def test_criteria_names(rubric):
    names = {c.name for c in rubric.criteria}
    assert names == {"signal_density", "actionability", "technical_depth", "relevance"}


def test_criteria_weights(rubric):
    weights = {c.name: c.weight for c in rubric.criteria}
    assert weights["signal_density"] == 3
    assert weights["actionability"] == 3
    assert weights["technical_depth"] == 2
    assert weights["relevance"] == 2


def test_compute_overall_perfect(rubric):
    scores = {c.name: 5 for c in rubric.criteria}
    assert rubric.compute_overall(scores) == 5.0


def test_compute_overall_minimum(rubric):
    scores = {c.name: 1 for c in rubric.criteria}
    assert rubric.compute_overall(scores) == 1.0


def test_compute_overall_weighted(rubric):
    # signal_density(3)*4 + actionability(3)*5 + technical_depth(2)*2 + relevance(2)*3
    # = 12 + 15 + 4 + 6 = 37 / 10 = 3.7
    scores = {"signal_density": 4, "actionability": 5, "technical_depth": 2, "relevance": 3}
    assert rubric.compute_overall(scores) == 3.7


def test_score_clamped_to_scale(rubric):
    scores = {c.name: 10 for c in rubric.criteria}  # Over scale
    assert rubric.compute_overall(scores) == 5.0


def test_verdict_required(rubric):
    assert rubric.score_to_verdict(4.5) == "REQUIRED"


def test_verdict_watch(rubric):
    assert rubric.score_to_verdict(3.5) == "WATCH"


def test_verdict_skim(rubric):
    assert rubric.score_to_verdict(2.5) == "SKIM"


def test_verdict_skip(rubric):
    assert rubric.score_to_verdict(1.5) == "SKIP"


def test_criteria_prompt(rubric):
    prompt = rubric.criteria_prompt()
    assert "signal_density" in prompt
    assert "weight: 3" in prompt
