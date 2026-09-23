"""T-13: live end-to-end run of the case-study conversation (FR-6..8, FR-10).

Run with: uv run pytest -m live
Uses the provider configured in .env. Assertions check behavior, not exact wording.
"""

import re

import pytest

from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.config import ConfigError, load_settings
from enrollment_agent.demo import run_demo
from enrollment_agent.llm import build_chat_model

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def turns():
    try:
        settings = load_settings()
    except ConfigError as exc:
        pytest.skip(f"LLM not configured: {exc}")
    agent = EnrollmentAgent(build_chat_model(settings), settings.max_iterations)
    return {t.number: t for t in run_demo(agent)}


def tool_names(turn):
    return [e.name for e in turn.result.tool_events]


def test_turn1_lists_computer_science_programs(turns):
    turn = turns[1]
    assert "get_program_info" in tool_names(turn)
    assert "Computer Science" in turn.result.reply


def test_turn2_resolves_that_and_gives_deadline(turns):
    turn = turns[2]
    assert "get_deadlines" in tool_names(turn)
    for event in turn.result.tool_events:
        assert "computer science" in event.args["program_name"].lower()
    assert "2027" in turn.result.reply


def test_turn3_checks_status_for_given_id(turns):
    turn = turns[3]
    calls = [e for e in turn.result.tool_events if e.name == "check_application_status"]
    assert calls and calls[0].args["applicant_id"].upper() == "APP-1042"
    assert "documents pending" in turn.result.reply.lower()


def test_turn4_escalates_without_tools(turns):
    turn = turns[4]
    assert tool_names(turn) == []
    assert "counselor" in turn.result.reply.lower()


def test_turn5_lists_missing_documents_without_asking_for_id(turns):
    reply = turns[5].result.reply.lower()
    assert "transcript" in reply
    assert "recommendation" in reply
    assert not re.search(r"(provide|share|what is|what's|need) your (applicant )?id", reply)
