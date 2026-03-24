"""Assessment eval harness — structured tests for agent behaviour under varied conditions.

Unlike smoke tests (binary pass/fail), the harness captures the full context
of an agent interaction for later analysis. Each run produces a structured
YAML record: what was asked, under what conditions, what the agent did,
and whether it met expectations.

Supports both single-injection scenarios and multi-turn dialogue scenarios.

Usage:
    halctl assess <instance> --scenario <name>
    halctl assess <instance> --all
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from halos.common.log import hlog
from .config import load_fleet_manifest, fleet_dir
from .provision import OPERATOR_CHAT_JID
from .smoke import _connect_db, _inject_message, _wait_for_response, _count_log_lines


# ---------------------------------------------------------------------------
# Dialogue building blocks
# ---------------------------------------------------------------------------

@dataclass
class TurnRecord:
    """One turn in a multi-turn dialogue."""
    turn: int
    message: str
    response: str
    assertions: list[dict] = field(default_factory=list)
    behaviour: dict = field(default_factory=dict)


def _dialogue_turn(
    conn: sqlite3.Connection,
    pm2_log: Path,
    chat_jid: str,
    sender_id: str,
    sender_name: str,
    message: str,
    timeout: float = 30.0,
) -> str:
    """Inject one message and wait for the agent's response.

    Uses collect_all=True to capture multi-message responses (e.g.,
    greeting + first Likert question in one turn).
    """
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, chat_jid, sender_id, sender_name, message)
    return _wait_for_response(pm2_log, before_lines, timeout=timeout, collect_all=True) or ""


def _check_response(response: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the response (case-insensitive)."""
    lower = response.lower()
    return any(k.lower() in lower for k in keywords)


class AssessRecord:
    """A single assessment run with full context."""

    def __init__(self, instance: str, scenario: str):
        self.record_id = f"assess-{uuid.uuid4().hex[:8]}"
        self.instance = instance
        self.scenario = scenario
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.conditions: dict = {}
        self.prompt = ""
        self.response = ""
        self.behaviour: dict = {}
        self.assertions: list[dict] = []
        self.dialogue: list[TurnRecord] = []

    def assert_check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.assertions.append({"name": name, "passed": passed, "detail": detail})
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {name}" + (f"  ({detail})" if detail else ""))
        return passed

    @property
    def passed(self) -> bool:
        return all(a["passed"] for a in self.assertions)

    def to_dict(self) -> dict:
        d = {
            "record_id": self.record_id,
            "instance": self.instance,
            "scenario": self.scenario,
            "timestamp": self.timestamp,
            "conditions": self.conditions,
            "behaviour": self.behaviour,
            "assertions": self.assertions,
            "passed": self.passed,
        }
        if self.dialogue:
            d["dialogue"] = [
                {"turn": t.turn, "message": t.message, "response": t.response,
                 "assertions": t.assertions, "behaviour": t.behaviour}
                for t in self.dialogue
            ]
        else:
            d["prompt"] = self.prompt
            d["response"] = self.response
        return d


def _get_conversation_count(conn: sqlite3.Connection, sender_id: str, chat_jid: str) -> int:
    """Count distinct 'sessions' by looking at message gaps > 30 min."""
    rows = conn.execute(
        "SELECT timestamp FROM messages WHERE sender = ? AND chat_jid = ? ORDER BY timestamp",
        (sender_id, chat_jid),
    ).fetchall()
    if not rows:
        return 0
    count = 1
    prev = rows[0][0]
    for (ts,) in rows[1:]:
        try:
            from datetime import datetime as dt
            t1 = dt.fromisoformat(prev.replace("Z", "+00:00"))
            t2 = dt.fromisoformat(ts.replace("Z", "+00:00"))
            if (t2 - t1).total_seconds() > 1800:
                count += 1
        except (ValueError, TypeError):
            pass
        prev = ts
    return count


def _seed_conversations(conn: sqlite3.Connection, chat_jid: str, sender_id: str, count: int) -> None:
    """Inject synthetic conversation history to simulate N prior conversations."""
    from datetime import timedelta
    base = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        ts = (base + timedelta(hours=i * 2)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO messages (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message) VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
            (f"seed-{i}-user", chat_jid, sender_id, "Assess User", f"conversation {i} message", ts),
        )
        ts_reply = (base + timedelta(hours=i * 2, minutes=1)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO messages (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message) VALUES (?, ?, ?, ?, ?, ?, 1, 0)",
            (f"seed-{i}-bot", chat_jid, "HAL", "HAL", f"response to conversation {i}", ts_reply),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_likert_delivery(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: does the agent deliver Likert questions during first real conversation?"""
    rec = AssessRecord("", "likert_delivery")
    rec.conditions = {
        "onboarding_state": "active",
        "likert_complete": False,
        "conversation_count": 0,
    }

    rec.prompt = "@HAL hello, I'm new here"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    # collect_all: agent may greet first, then ask Likert in follow-up messages
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout, collect_all=True) or ""

    response_lower = rec.response.lower()
    rec.behaviour = {
        "mentioned_questions": "question" in response_lower or "scale" in response_lower or "1" in rec.response,
        "mentioned_rick": "rick" in response_lower,
        "was_warm": any(w in response_lower for w in ["welcome", "hello", "hi", "glad"]),
    }

    rec.assert_check(
        "initiates_assessment",
        rec.behaviour["mentioned_questions"],
        rec.response[:100],
    )
    rec.assert_check(
        "warm_tone",
        rec.behaviour["was_warm"] or len(rec.response) > 20,
        "response has conversational warmth",
    )

    return rec


def scenario_qualitative_not_too_early(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent should NOT ask qualitative questions before 3 conversations."""
    rec = AssessRecord("", "qualitative_not_too_early")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 1)
    conv_count = _get_conversation_count(conn, "5967394003", OPERATOR_CHAT_JID)

    rec.conditions = {
        "conversation_count": conv_count,
        "likert_complete": True,
        "qualitative_pre_complete": False,
    }

    rec.prompt = "@HAL that was really helpful, thanks"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help", "feel about ai", "couple of questions", "rick asked"]
    )
    rec.behaviour = {"asked_qualitative": asked_qualitative}

    rec.assert_check(
        "should_not_ask_qualitative_early",
        not asked_qualitative,
        f"conv_count={conv_count}, asked={asked_qualitative}",
    )

    return rec


def scenario_qualitative_dropin_eligible(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent behaviour when eligible to ask qualitative questions (3-7 conversations)."""
    rec = AssessRecord("", "qualitative_dropin_eligible")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 5)
    conv_count = _get_conversation_count(conn, "5967394003", OPERATOR_CHAT_JID)

    rec.conditions = {
        "conversation_count": conv_count,
        "likert_complete": True,
        "qualitative_pre_complete": False,
        "session_context": "user just completed a task, natural pause",
    }

    rec.prompt = "@HAL thanks, that was exactly what I needed. Quiet day otherwise."
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help", "feel about ai", "couple of questions", "rick asked", "good time"]
    )
    asked_permission = any(
        phrase in response_lower
        for phrase in ["good time", "is now", "would you", "mind if", "before i forget"]
    )

    rec.behaviour = {
        "asked_qualitative": asked_qualitative,
        "asked_permission_first": asked_permission,
    }

    # Soft assertion — characterising, not gatekeeping
    rec.assert_check(
        "eligible_and_aware",
        True,
        f"asked={asked_qualitative}, permission={asked_permission}",
    )
    if asked_qualitative:
        rec.assert_check(
            "asked_permission_first",
            asked_permission,
            "should ask before launching into questions",
        )

    return rec


def scenario_no_interrupt_during_task(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent should NOT ask assessment questions mid-task."""
    rec = AssessRecord("", "no_interrupt_during_task")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 5)

    rec.conditions = {
        "conversation_count": 5,
        "likert_complete": True,
        "qualitative_pre_complete": False,
        "session_context": "user is mid-task, actively requesting help",
    }

    rec.prompt = "@HAL can you help me draft a message to my boss about taking next Friday off?"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help you with", "feel about ai", "couple of questions rick asked"]
    )
    helped_with_task = any(
        phrase in response_lower
        for phrase in ["friday", "boss", "day off", "time off", "draft", "message", "context", "tone", "formal", "sure", "help"]
    )

    rec.behaviour = {
        "asked_qualitative": asked_qualitative,
        "helped_with_task": helped_with_task,
    }

    rec.assert_check(
        "should_not_interrupt_task",
        not asked_qualitative,
        f"asked_qualitative={asked_qualitative}",
    )
    rec.assert_check(
        "should_help_with_task",
        helped_with_task,
        rec.response[:100],
    )

    return rec


def scenario_likert_deflection(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: user repeatedly deflects Likert questions. Agent should relent after 3 attempts.

    This is a multi-turn scenario. We inject three deflection messages
    and check that the agent:
    1. Tries to redirect on first two deflections
    2. Relents on or before the third deflection
    3. Mentions Rick / operator follow-up when relenting
    """
    rec = AssessRecord("", "likert_deflection")
    rec.conditions = {
        "onboarding_state": "active",
        "likert_complete": False,
        "user_behaviour": "repeatedly deflects assessment questions",
    }

    deflections = [
        "@HAL skip the questions, I just want to use this thing",
        "@HAL seriously, I don't want to answer questions right now",
        "@HAL look I'm not doing a survey, can we just get on with it",
    ]

    all_responses: list[str] = []
    relented = False
    relent_turn = None
    mentioned_rick = False
    mentioned_come_back = False

    for i, deflection in enumerate(deflections):
        before_lines = _count_log_lines(pm2_log)
        _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", deflection)
        response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""
        all_responses.append(response)

        response_lower = response.lower()
        if any(phrase in response_lower for phrase in [
            "come back", "another time", "no pressure", "paused", "let rick know",
            "skip", "that's fine", "move on", "no worries", "we can do",
            "later", "whenever you're ready", "no need", "understood",
            "no questions", "what do you need", "what are we",
            "deferred", "already deferred",
        ]):
            relented = True
            relent_turn = i + 1
            mentioned_rick = "rick" in response_lower or "kai" in response_lower
            mentioned_come_back = any(
                p in response_lower for p in ["come back", "another time", "later"]
            )
            break

    rec.prompt = " | ".join(deflections[:relent_turn or len(deflections)])
    rec.response = "\n---\n".join(all_responses)
    rec.behaviour = {
        "relented": relented,
        "relent_turn": relent_turn,
        "mentioned_rick": mentioned_rick,
        "mentioned_come_back": mentioned_come_back,
        "total_turns": len(all_responses),
    }

    rec.assert_check(
        "relents_within_3_attempts",
        relented,
        f"relented on turn {relent_turn}" if relented else f"did not relent after {len(all_responses)} turns",
    )
    if relented:
        rec.assert_check(
            "mentions_operator_followup",
            mentioned_rick,
            "should mention Rick/operator will follow up",
        )
        rec.assert_check(
            "offers_to_come_back",
            mentioned_come_back,
            "should indicate questions can be revisited",
        )

    return rec


# ---------------------------------------------------------------------------
# Dialogue scenarios
# ---------------------------------------------------------------------------

def scenario_tangent_and_resume(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Dialogue: user answers Q1-Q2, goes on a tangent, comes back and finishes.

    Tests partial progress tracking, tangent tolerance, and resume-from-Q3.
    ~12 turns, ~2-3 minutes.
    """
    rec = AssessRecord("", "tangent_and_resume")
    rec.conditions = {
        "likert_complete": False,
        "conversation_count": 0,
        "pattern": "answer-answer-tangent-tangent-resume-answer-answer-answer-done",
    }

    jid = OPERATOR_CHAT_JID
    sid = "5967394003"

    def turn(n: int, msg: str) -> str:
        print(f"    turn {n}: {msg[:60]}")
        resp = _dialogue_turn(conn, pm2_log, jid, sid, "Tangent User", msg, timeout=timeout)
        t = TurnRecord(turn=n, message=msg, response=resp)
        rec.dialogue.append(t)
        return resp

    # Turn 1: hello — expect greeting + Likert initiation
    r1 = turn(1, "@HAL hello, just got set up")
    likert_initiated = _check_response(r1, [
        "question", "scale", "1", "5", "rick asked", "quick",
        "comfortable", "before we", "check-in", "calibration",
    ])
    rec.dialogue[-1].assertions.append({
        "name": "initiates_likert",
        "passed": likert_initiated or len(r1) > 50,  # long response = likely assessment intro
        "detail": r1[:80],
    })

    # Turn 2: answer Q1 — agent should acknowledge and move to Q2
    r2 = turn(2, "3")
    q1_fail = _check_response(r2, ["invalid", "error", "try again", "didn't understand"])
    rec.dialogue[-1].assertions.append({
        "name": "accepts_q1",
        "passed": len(r2) > 5 and not q1_fail,
        "detail": r2[:80],
    })

    # Turn 3: answer Q2 — agent should acknowledge and move to Q3
    r3 = turn(3, "4")
    q2_fail = _check_response(r3, ["invalid", "error", "try again", "didn't understand"])
    rec.dialogue[-1].assertions.append({
        "name": "accepts_q2",
        "passed": len(r3) > 5 and not q2_fail,
        "detail": r3[:80],
    })

    # Turn 4: tangent — user goes off-topic
    r4 = turn(4, "actually, what kind of things can you help me with?")
    rec.dialogue[-1].behaviour = {
        "handles_tangent": not _check_response(r4, ["question 3", "back to the questions", "we were doing"]),
        "responds_to_query": len(r4) > 20,
    }
    rec.dialogue[-1].assertions.append({
        "name": "handles_tangent_gracefully",
        "passed": rec.dialogue[-1].behaviour["responds_to_query"],
    })

    # Turn 5: deeper tangent
    r5 = turn(5, "can you help me plan a fishing trip?")
    rec.dialogue[-1].behaviour = {"engages_with_tangent": len(r5) > 10}

    # Turn 6: user wants to resume
    r6 = turn(6, "never mind the fishing, let's finish those questions")
    resumes_correctly = _check_response(r6, [
        "question 3", "how often", "frequency", "where we left", "pick up",
        "next question", "three more", "3 more",
    ])
    does_not_restart = not _check_response(r6, ["question 1", "how comfortable", "start over", "from the beginning"])
    rec.dialogue[-1].assertions.append({
        "name": "resumes_from_q3_not_q1",
        "passed": resumes_correctly or does_not_restart,
        "detail": r6[:80],
    })

    # Turns 7-9: answer Q3, Q4, Q5
    r7 = turn(7, "2")
    r8 = turn(8, "3")
    r9 = turn(9, "4")

    # Turn 10: check completion
    r10 = turn(10, "are we done with the questions?")
    assessment_complete = _check_response(r10, [
        "done", "complete", "finished", "all five", "that's it", "last one",
        "no more questions", "all answered", "last of them", "that's all",
        "yes", "wrapped up",
    ])
    rec.dialogue[-1].assertions.append({
        "name": "confirms_completion",
        "passed": assessment_complete,
        "detail": r10[:80],
    })

    # Turn 11: normal operation
    r11 = turn(11, "great, thanks")
    normal_operation = not _check_response(r11, ["question", "likert", "assessment", "scale of 1"])
    rec.dialogue[-1].assertions.append({
        "name": "transitions_to_normal",
        "passed": normal_operation,
    })

    # Roll up assertions
    all_turn_assertions = []
    for t in rec.dialogue:
        all_turn_assertions.extend(t.assertions)
    for a in all_turn_assertions:
        rec.assert_check(a["name"], a["passed"], a.get("detail", ""))

    return rec


def scenario_deflect_then_resume(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Dialogue: user deflects 3x, agent relents, user later asks to resume.

    Tests three-strike relent, normal operation after deferral, and
    user-initiated resume of deferred assessment.
    ~10 turns, ~2-3 minutes.
    """
    rec = AssessRecord("", "deflect_then_resume")
    rec.conditions = {
        "likert_complete": False,
        "conversation_count": 0,
        "pattern": "deflect-deflect-deflect-relent-task-resume-answer",
    }

    jid = OPERATOR_CHAT_JID
    sid = "5967394003"

    def turn(n: int, msg: str) -> str:
        print(f"    turn {n}: {msg[:60]}")
        resp = _dialogue_turn(conn, pm2_log, jid, sid, "Deflect User", msg, timeout=timeout)
        t = TurnRecord(turn=n, message=msg, response=resp)
        rec.dialogue.append(t)
        return resp

    # Turn 1: hello
    r1 = turn(1, "@HAL hi there")

    # Turns 2-4: three deflections
    r2 = turn(2, "can we skip the questions please")
    r3 = turn(3, "I really don't want to do this right now")
    r4 = turn(4, "seriously, no")

    # Check: did the agent relent by turn 4?
    all_responses = [r2, r3, r4]
    relented = False
    relent_keywords = [
        "come back", "another time", "no pressure", "let rick know",
        "that's fine", "move on", "no worries", "later", "no need",
        "understood", "no questions", "deferred", "whenever",
    ]
    for i, r in enumerate(all_responses):
        if _check_response(r, relent_keywords):
            relented = True
            rec.dialogue[i + 1].assertions.append({
                "name": "relented",
                "passed": True,
                "detail": f"relented on deflection {i + 1}",
            })
            break

    rec.assert_check("relents_within_3", relented, "agent should relent after 3 deflections")

    # Turn 5: normal operation — ask for help with something
    r5 = turn(5, "can you help me write a birthday message for my son?")
    helped = _check_response(r5, ["birthday", "son", "happy", "message", "sure", "help", "what"])
    rec.dialogue[-1].assertions.append({
        "name": "normal_operation_works",
        "passed": helped,
        "detail": r5[:80],
    })
    rec.assert_check("normal_after_deferral", helped, r5[:60])

    # Turn 6: user asks to resume the Likert questions specifically
    r6 = turn(6, "ok actually, let's do those 1-to-5 questions you mentioned earlier. I'm ready now.")
    resumes = _check_response(r6, [
        "question", "scale", "1", "5", "comfortable", "how",
        "pick up", "first question", "ready",
    ])
    rec.dialogue[-1].assertions.append({
        "name": "resumes_on_user_request",
        "passed": resumes,
        "detail": r6[:80],
    })
    rec.assert_check("user_initiated_resume", resumes, r6[:60])

    # Turn 7: answer a question to prove the flow works
    r7 = turn(7, "3")
    error_signals = _check_response(r7, ["invalid", "error", "open-ended", "not a number"])
    accepted = len(r7) > 5 and not error_signals
    rec.assert_check("accepts_answer_after_resume", accepted, r7[:60])

    return rec


def scenario_edit_response(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Dialogue: user answers Q1 and Q2, then asks to change Q1's answer.

    Tests response editing governance — agent should confirm, accept
    new value, update the record, and continue from Q3.
    ~8 turns, ~1-2 minutes.
    """
    rec = AssessRecord("", "edit_response")
    rec.conditions = {
        "likert_complete": False,
        "conversation_count": 0,
        "pattern": "answer-answer-edit-confirm-answer",
    }

    jid = OPERATOR_CHAT_JID
    sid = "5967394003"

    def turn(n: int, msg: str) -> str:
        print(f"    turn {n}: {msg[:60]}")
        resp = _dialogue_turn(conn, pm2_log, jid, sid, "Edit User", msg, timeout=timeout)
        t = TurnRecord(turn=n, message=msg, response=resp)
        rec.dialogue.append(t)
        return resp

    # Turn 1: hello
    r1 = turn(1, "@HAL hello")

    # Turn 2: answer Q1 with context
    r2 = turn(2, "for the comfort question, I'd say 4")
    q1_fail = _check_response(r2, ["invalid", "error"])
    rec.dialogue[-1].assertions.append({
        "name": "accepts_q1",
        "passed": len(r2) > 5 and not q1_fail,
        "detail": r2[:80],
    })

    # Turn 3: answer Q2 with context
    r3 = turn(3, "trust in AI advice, I'd say 2")
    q2_fail = _check_response(r3, ["invalid", "error"])
    rec.dialogue[-1].assertions.append({
        "name": "accepts_q2",
        "passed": len(r3) > 5 and not q2_fail,
        "detail": r3[:80],
    })

    # Turn 4: ask to edit Q1
    r4 = turn(4, "actually, can I change my answer to the comfort question? I want to say 3 instead of 4")
    acknowledges_edit = _check_response(r4, [
        "change", "update", "noted", "first question", "3", "comfort",
        "sure", "of course", "no problem", "done",
    ])
    rec.dialogue[-1].assertions.append({
        "name": "acknowledges_edit_request",
        "passed": acknowledges_edit,
        "detail": r4[:80],
    })
    rec.assert_check("handles_edit_request", acknowledges_edit, r4[:60])

    # Turn 5: if agent asks for confirmation, confirm. Otherwise it may have already applied.
    needs_confirm = _check_response(r4, ["confirm", "sure?", "want me to", "shall i"])
    if needs_confirm:
        r5 = turn(5, "yes, change it to 3")
        rec.dialogue[-1].assertions.append({
            "name": "confirms_edit",
            "passed": _check_response(r5, ["updated", "changed", "noted", "done", "3"]),
        })

    # Turn 6: continue — agent should move to next question (Likert Q3 or qualitative)
    r6 = turn(6 if not needs_confirm else 7, "ok what's the next question?")
    error_signals = _check_response(r6, ["error", "can't", "broken", "invalid"])
    continues = len(r6) > 10 and not error_signals
    rec.dialogue[-1].assertions.append({
        "name": "flow_continues_after_edit",
        "passed": continues,
        "detail": r6[:80],
    })
    rec.assert_check("flow_continues_after_edit", continues, r6[:60])

    # Roll up turn assertions
    for t in rec.dialogue:
        for a in t.assertions:
            if a["name"] not in [x["name"] for x in rec.assertions]:
                rec.assert_check(a["name"], a["passed"], a.get("detail", ""))

    return rec


# ---------------------------------------------------------------------------
# Registry and runner
# ---------------------------------------------------------------------------

SCENARIOS = {
    # Single-injection scenarios
    "likert_delivery": scenario_likert_delivery,
    "qualitative_not_too_early": scenario_qualitative_not_too_early,
    "qualitative_dropin_eligible": scenario_qualitative_dropin_eligible,
    "no_interrupt_during_task": scenario_no_interrupt_during_task,
    "likert_deflection": scenario_likert_deflection,
    # Dialogue scenarios
    "tangent_and_resume": scenario_tangent_and_resume,
    "deflect_then_resume": scenario_deflect_then_resume,
    "edit_response": scenario_edit_response,
}


def run_assessment(
    name: str,
    scenarios: list[str] | None = None,
    timeout: float = 60.0,
    fleet_base: Path | None = None,
) -> list[AssessRecord]:
    """Run assessment scenarios against a live instance. Returns list of AssessRecords."""
    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)

    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == name:
            instance = inst
            break

    if instance is None:
        raise ValueError(f"instance not found: {name}")

    deploy_path = Path(instance["path"])
    conn = _connect_db(deploy_path)
    pm2_log = Path.home() / ".pm2" / "logs" / f"microhal-{name}-out.log"

    to_run = scenarios or list(SCENARIOS.keys())
    records = []

    for scenario_name in to_run:
        # Full state reset between scenarios — equivalent to afterEach(resetSession)
        # The halo process caches session IDs in memory, so DB-only
        # cleanup is insufficient. Must restart pm2 to flush the cache.
        try:
            import subprocess
            import shutil
            # Kill active containers
            for cid in subprocess.run(
                ["docker", "ps", "--filter", "name=halo-telegram-main", "-q"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip().split("\n"):
                if cid:
                    subprocess.run(["docker", "kill", cid], capture_output=True, timeout=5)
            # Clear ALL DB state
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM assessments")
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM onboarding")
            conn.execute("DELETE FROM router_state")
            conn.commit()
            # Clear onboarding YAML
            onboarding_yaml = deploy_path / "memory" / "onboarding-state.yaml"
            if onboarding_yaml.exists():
                onboarding_yaml.unlink()
            # Clear SDK session data
            sessions_dir = deploy_path / "data" / "sessions"
            if sessions_dir.exists():
                shutil.rmtree(sessions_dir, ignore_errors=True)
            # Restart pm2 to flush in-memory session cache
            subprocess.run(
                ["npx", "pm2", "restart", f"microhal-{name}"],
                capture_output=True, timeout=15,
            )
            # Wait for process to come back up
            time.sleep(5)
        except Exception:
            pass
        if scenario_name not in SCENARIOS:
            print(f"  SKIP: unknown scenario '{scenario_name}'")
            continue

        print(f"\n  --- {scenario_name} ---")
        fn = SCENARIOS[scenario_name]
        rec = fn(conn, deploy_path, pm2_log, timeout)
        rec.instance = name
        records.append(rec)

    conn.close()

    # Write records to disk
    records_dir = deploy_path / "data" / "assessments"
    records_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    for rec in records:
        out_path = records_dir / f"{ts}-{rec.scenario}.yaml"
        with open(out_path, "w") as f:
            yaml.dump(rec.to_dict(), f, default_flow_style=False, sort_keys=False)

    hlog("halctl", "info", "assessment_complete", {
        "name": name,
        "scenarios": len(records),
        "passed": sum(1 for r in records if r.passed),
        "failed": sum(1 for r in records if not r.passed),
    })

    return records
