"""Tests for the microHAL onboarding state machine."""

from __future__ import annotations

from pathlib import Path

import yaml

from halos.microhal.onboarding import (
    LIKERT_QUESTIONS,
    STATES,
    TERMS_TEXT,
    TUTORIAL_MESSAGES,
    advance_onboarding,
    get_onboarding_prompt,
    get_onboarding_state,
)


# --- get_onboarding_state ---


def test_no_state_file_returns_first_contact(tmp_path: Path):
    assert get_onboarding_state(tmp_path) == "first_contact"


def test_reads_persisted_state(tmp_path: Path):
    (tmp_path / "onboarding-state.yaml").write_text("state: tutorial\n")
    assert get_onboarding_state(tmp_path) == "tutorial"


def test_invalid_state_falls_back_to_first_contact(tmp_path: Path):
    (tmp_path / "onboarding-state.yaml").write_text("state: bogus\n")
    assert get_onboarding_state(tmp_path) == "first_contact"


def test_corrupt_yaml_returns_first_contact(tmp_path: Path):
    (tmp_path / "onboarding-state.yaml").write_text("not a mapping")
    assert get_onboarding_state(tmp_path) == "first_contact"


# --- get_onboarding_prompt ---


def test_first_contact_prompt():
    msg = get_onboarding_prompt("first_contact")
    assert "AI assistant" in msg


def test_terms_prompt_contains_terms():
    msg = get_onboarding_prompt("terms_of_service")
    assert msg == TERMS_TEXT
    assert "YES" in msg


def test_assessment_prompt_contains_first_question():
    msg = get_onboarding_prompt("pre_flight_assessment")
    assert LIKERT_QUESTIONS[0] in msg


def test_tutorial_prompt():
    msg = get_onboarding_prompt("tutorial")
    assert msg == TUTORIAL_MESSAGES[0]


def test_active_prompt():
    msg = get_onboarding_prompt("active")
    assert "complete" in msg.lower() or "ready" in msg.lower()


# --- advance_onboarding: first_contact → terms_of_service ---


def test_first_contact_advances_to_terms(tmp_path: Path):
    result = advance_onboarding(tmp_path, "first_contact", "")
    assert result["new_state"] == "terms_of_service"
    assert result["advanced"] is True
    assert get_onboarding_state(tmp_path) == "terms_of_service"


# --- advance_onboarding: terms_of_service ---


def test_terms_accepted_advances_to_assessment(tmp_path: Path):
    # Set up terms state
    advance_onboarding(tmp_path, "first_contact", "")
    result = advance_onboarding(tmp_path, "terms_of_service", "YES")
    assert result["new_state"] == "pre_flight_assessment"
    assert result["advanced"] is True


def test_terms_accepted_case_insensitive(tmp_path: Path):
    advance_onboarding(tmp_path, "first_contact", "")
    result = advance_onboarding(tmp_path, "terms_of_service", "yes")
    assert result["new_state"] == "pre_flight_assessment"
    assert result["advanced"] is True


def test_terms_rejected_stays(tmp_path: Path):
    advance_onboarding(tmp_path, "first_contact", "")
    result = advance_onboarding(tmp_path, "terms_of_service", "no")
    assert result["new_state"] == "terms_of_service"
    assert result["advanced"] is False


def test_terms_stores_waiver_timestamp(tmp_path: Path):
    advance_onboarding(tmp_path, "first_contact", "")
    advance_onboarding(tmp_path, "terms_of_service", "YES")
    data = yaml.safe_load((tmp_path / "onboarding-state.yaml").read_text())
    assert "waiver_accepted_at" in data
    assert data["waiver_accepted_at"].endswith("Z")


# --- advance_onboarding: pre_flight_assessment ---


def test_assessment_captures_valid_response(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "3")
    assert result["advanced"] is True
    assert result["data"]["likert_response"]["value"] == 3


def test_assessment_rejects_non_numeric(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "banana")
    assert result["advanced"] is False
    assert result["new_state"] == "pre_flight_assessment"
    assert "1 to 5" in result["message"]


def test_assessment_rejects_out_of_range_high(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "7")
    assert result["advanced"] is False
    assert "1 to 5" in result["message"]


def test_assessment_rejects_out_of_range_low(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "0")
    assert result["advanced"] is False
    assert "1 to 5" in result["message"]


def test_assessment_rejects_negative(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "-1")
    assert result["advanced"] is False


def test_assessment_all_questions_advances_to_tutorial(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    for i in range(len(LIKERT_QUESTIONS) - 1):
        result = advance_onboarding(tmp_path, "pre_flight_assessment", str(i % 5 + 1))
        assert result["new_state"] == "pre_flight_assessment"

    # Last question
    result = advance_onboarding(tmp_path, "pre_flight_assessment", "4")
    assert result["new_state"] == "tutorial"
    assert result["advanced"] is True


def test_assessment_likert_data_persisted_as_yaml(tmp_path: Path):
    _advance_to_assessment(tmp_path)
    for i in range(len(LIKERT_QUESTIONS)):
        advance_onboarding(tmp_path, "pre_flight_assessment", str(i % 5 + 1))

    data = yaml.safe_load((tmp_path / "onboarding-state.yaml").read_text())
    responses = data["likert_responses"]
    assert len(responses) == len(LIKERT_QUESTIONS)
    for r in responses:
        assert "question" in r
        assert "value" in r
        assert "answered_at" in r
        assert 1 <= r["value"] <= 5


# --- advance_onboarding: tutorial ---


def test_tutorial_advances_through_messages(tmp_path: Path):
    _advance_to_tutorial(tmp_path)
    for i in range(len(TUTORIAL_MESSAGES) - 1):
        result = advance_onboarding(tmp_path, "tutorial", "ok")
        assert result["new_state"] == "tutorial"
        assert result["message"] == TUTORIAL_MESSAGES[i + 1]

    # Final tutorial step → active
    result = advance_onboarding(tmp_path, "tutorial", "ok")
    assert result["new_state"] == "active"
    assert result["advanced"] is True


# --- advance_onboarding: active ---


def test_active_state_returns_completion(tmp_path: Path):
    result = advance_onboarding(tmp_path, "active", "hello")
    assert result["new_state"] == "active"
    assert result["advanced"] is False


# --- State persistence round-trip ---


def test_state_persists_across_reads(tmp_path: Path):
    assert get_onboarding_state(tmp_path) == "first_contact"
    advance_onboarding(tmp_path, "first_contact", "")
    assert get_onboarding_state(tmp_path) == "terms_of_service"
    advance_onboarding(tmp_path, "terms_of_service", "YES")
    assert get_onboarding_state(tmp_path) == "pre_flight_assessment"


def test_full_flow_end_to_end(tmp_path: Path):
    """Walk through the entire onboarding flow and verify final state."""
    # first_contact → terms
    advance_onboarding(tmp_path, "first_contact", "")
    assert get_onboarding_state(tmp_path) == "terms_of_service"

    # terms → assessment
    advance_onboarding(tmp_path, "terms_of_service", "YES")
    assert get_onboarding_state(tmp_path) == "pre_flight_assessment"

    # answer all 5 questions
    for i in range(len(LIKERT_QUESTIONS)):
        advance_onboarding(tmp_path, "pre_flight_assessment", "3")

    assert get_onboarding_state(tmp_path) == "tutorial"

    # walk through tutorial
    for _ in range(len(TUTORIAL_MESSAGES)):
        advance_onboarding(tmp_path, "tutorial", "ok")

    assert get_onboarding_state(tmp_path) == "active"

    # Verify all data is present
    data = yaml.safe_load((tmp_path / "onboarding-state.yaml").read_text())
    assert data["state"] == "active"
    assert "waiver_accepted_at" in data
    assert len(data["likert_responses"]) == len(LIKERT_QUESTIONS)
    assert len(data["transitions"]) > 0


def test_state_file_created_in_nonexistent_dir(tmp_path: Path):
    """Memory dir is created if it doesn't exist."""
    deep = tmp_path / "a" / "b" / "c"
    advance_onboarding(deep, "first_contact", "")
    assert get_onboarding_state(deep) == "terms_of_service"


# --- State ordering ---


def test_states_are_ordered():
    assert STATES[0] == "first_contact"
    assert STATES[-1] == "active"
    assert len(STATES) == 6


# --- Helpers ---


def _advance_to_assessment(tmp_path: Path):
    """Helper to get to pre_flight_assessment state."""
    advance_onboarding(tmp_path, "first_contact", "")
    advance_onboarding(tmp_path, "terms_of_service", "YES")


def _advance_to_tutorial(tmp_path: Path):
    """Helper to get to tutorial state."""
    _advance_to_assessment(tmp_path)
    for i in range(len(LIKERT_QUESTIONS)):
        advance_onboarding(tmp_path, "pre_flight_assessment", str(i % 5 + 1))
