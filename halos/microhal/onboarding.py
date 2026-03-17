"""Onboarding state machine for microHAL instances.

Manages the first-contact flow: terms -> waiver -> assessment -> tutorial -> active.
State is persisted as YAML files in the instance's memory directory.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

# --- State Machine ---

STATES = [
    "first_contact",
    "terms_of_service",
    "waiver_accepted",
    "pre_flight_assessment",
    "tutorial",
    "active",
]

STATE_ORDER = {s: i for i, s in enumerate(STATES)}

LIKERT_QUESTIONS = [
    "How comfortable are you using AI assistants? (1=not at all, 5=very)",
    "How much do you trust AI-generated advice? (1=not at all, 5=completely)",
    "How often do you currently use AI tools? (1=never, 5=daily)",
    "How confident are you in evaluating whether AI output is correct? (1=not at all, 5=very)",
    "How would you describe your attitude toward AI? (1=skeptical, 5=enthusiastic)",
]

TERMS_TEXT = (
    "Before we get started, a few things to know:\n\n"
    "All data collected during this pilot belongs to the operator. "
    "This is a research pilot, not a product. "
    "By continuing, you agree to these terms.\n\n"
    "Reply YES to accept."
)

TUTORIAL_MESSAGES = [
    (
        "Welcome aboard! Here's what I can help with:\n\n"
        "- Answer questions and have conversations on any topic\n"
        "- Help you write, edit, and brainstorm\n"
        "- Run code and build small projects together\n"
        "- Keep notes and remember what matters to you"
    ),
    (
        "A few tips to get the most out of our chats:\n\n"
        "- Just talk naturally — no special commands needed\n"
        "- If I get something wrong, tell me. I learn from corrections.\n"
        "- You can ask me to remember things for later\n"
        "- I'm here whenever you need me, no rush"
    ),
    "That's it. You're all set. What would you like to talk about?",
]

# --- State File ---

_STATE_FILENAME = "onboarding-state.yaml"


def _state_path(memory_dir: Path) -> Path:
    return memory_dir / _STATE_FILENAME


def _read_state_file(memory_dir: Path) -> dict:
    path = _state_path(memory_dir)
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _write_state_file(memory_dir: Path, data: dict) -> None:
    """Atomic write: write to temp file then rename."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(memory_dir)
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=memory_dir,
        suffix=".yaml.tmp",
        delete=False,
    )
    try:
        yaml.dump(data, fd, default_flow_style=False, sort_keys=False, allow_unicode=True)
        fd.close()
        Path(fd.name).replace(path)
    except BaseException:
        fd.close()
        Path(fd.name).unlink(missing_ok=True)
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Public API ---


def get_onboarding_state(memory_dir: Path) -> str:
    """Read current onboarding state from memory directory.

    Returns state name or 'first_contact' if no state exists.
    """
    data = _read_state_file(memory_dir)
    state = data.get("state", "first_contact")
    if state not in STATE_ORDER:
        return "first_contact"
    return state


def get_onboarding_prompt(state: str) -> str:
    """Return the message to send for a given onboarding state."""
    if state == "first_contact":
        return "Hi there! I'm your new AI assistant. Let's get you set up."
    if state == "terms_of_service":
        return TERMS_TEXT
    if state == "waiver_accepted":
        return "Terms accepted. Let's learn a bit about you."
    if state == "pre_flight_assessment":
        return f"Quick question (1 of {len(LIKERT_QUESTIONS)}):\n\n{LIKERT_QUESTIONS[0]}"
    if state == "tutorial":
        return TUTORIAL_MESSAGES[0]
    if state == "active":
        return "Onboarding complete. I'm ready when you are."
    return "Hi there! I'm your new AI assistant. Let's get you set up."


def advance_onboarding(memory_dir: Path, current_state: str, user_response: str) -> dict:
    """Process user response and advance state if appropriate.

    Returns:
        {
            'new_state': str,
            'message': str,
            'advanced': bool,
            'data': dict,
        }
    """
    data = _read_state_file(memory_dir)
    response = user_response.strip()

    if current_state == "first_contact":
        return _advance_to(memory_dir, data, "terms_of_service")

    if current_state == "terms_of_service":
        return _handle_terms(memory_dir, data, response)

    if current_state == "waiver_accepted":
        return _advance_to(memory_dir, data, "pre_flight_assessment")

    if current_state == "pre_flight_assessment":
        return _handle_assessment(memory_dir, data, response)

    if current_state == "tutorial":
        return _handle_tutorial(memory_dir, data, response)

    if current_state == "active":
        return {
            "new_state": "active",
            "message": "Onboarding complete. I'm ready when you are.",
            "advanced": False,
            "data": {},
        }

    # Unknown state — reset
    return _advance_to(memory_dir, data, "first_contact")


# --- Internal Handlers ---


def _advance_to(memory_dir: Path, data: dict, new_state: str) -> dict:
    data["state"] = new_state
    data.setdefault("transitions", []).append({
        "to": new_state,
        "at": _now_iso(),
    })
    _write_state_file(memory_dir, data)
    return {
        "new_state": new_state,
        "message": get_onboarding_prompt(new_state),
        "advanced": True,
        "data": {},
    }


def _handle_terms(memory_dir: Path, data: dict, response: str) -> dict:
    if response.upper() == "YES":
        data["waiver_accepted_at"] = _now_iso()
        data["state"] = "waiver_accepted"
        data.setdefault("transitions", []).append({
            "to": "waiver_accepted",
            "at": data["waiver_accepted_at"],
        })
        _write_state_file(memory_dir, data)
        # Immediately advance through waiver_accepted to pre_flight_assessment
        return _advance_to(memory_dir, data, "pre_flight_assessment")

    return {
        "new_state": "terms_of_service",
        "message": "No worries — just reply YES when you're ready to continue.",
        "advanced": False,
        "data": {},
    }


def _handle_assessment(memory_dir: Path, data: dict, response: str) -> dict:
    likert = data.get("likert_responses", [])
    question_index = len(likert)

    # Validate numeric 1-5
    try:
        value = int(response)
    except ValueError:
        return {
            "new_state": "pre_flight_assessment",
            "message": f"Please reply with a number from 1 to 5.\n\n{LIKERT_QUESTIONS[question_index]}",
            "advanced": False,
            "data": {},
        }

    if value < 1 or value > 5:
        return {
            "new_state": "pre_flight_assessment",
            "message": f"That's outside the range. Please pick a number from 1 to 5.\n\n{LIKERT_QUESTIONS[question_index]}",
            "advanced": False,
            "data": {},
        }

    # Record response
    likert.append({
        "question": LIKERT_QUESTIONS[question_index],
        "value": value,
        "answered_at": _now_iso(),
    })
    data["likert_responses"] = likert

    # More questions?
    next_index = len(likert)
    if next_index < len(LIKERT_QUESTIONS):
        data["state"] = "pre_flight_assessment"
        _write_state_file(memory_dir, data)
        return {
            "new_state": "pre_flight_assessment",
            "message": f"Question {next_index + 1} of {len(LIKERT_QUESTIONS)}:\n\n{LIKERT_QUESTIONS[next_index]}",
            "advanced": True,
            "data": {"likert_response": {"index": question_index, "value": value}},
        }

    # All questions answered — move to tutorial
    return _advance_to(memory_dir, data, "tutorial")


def _handle_tutorial(memory_dir: Path, data: dict, response: str) -> dict:
    tutorial_step = data.get("tutorial_step", 0)
    next_step = tutorial_step + 1

    if next_step < len(TUTORIAL_MESSAGES):
        data["tutorial_step"] = next_step
        data["state"] = "tutorial"
        _write_state_file(memory_dir, data)
        return {
            "new_state": "tutorial",
            "message": TUTORIAL_MESSAGES[next_step],
            "advanced": True,
            "data": {},
        }

    # Tutorial complete — activate
    return _advance_to(memory_dir, data, "active")
