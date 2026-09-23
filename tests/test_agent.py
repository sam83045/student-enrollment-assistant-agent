"""T-10: EnrollmentAgent facade (FR-5, NFR-6)."""

import json

from enrollment_agent.agent import EnrollmentAgent, ToolEvent, TurnResult
from enrollment_agent.tools import lookup_application, lookup_deadlines

from .conftest import answer, tool_call


def test_chat_returns_reply_and_tool_events(fake_model):
    agent = EnrollmentAgent(
        fake_model([tool_call("get_deadlines", program_name="MBA"), answer("It's March 1.")])
    )

    result = agent.chat("MBA deadline?", agent.new_session())

    assert isinstance(result, TurnResult)
    assert result.reply == "It's March 1."
    assert len(result.tool_events) == 1
    event = result.tool_events[0]
    assert isinstance(event, ToolEvent)
    assert event.name == "get_deadlines"
    assert event.args == {"program_name": "MBA"}
    assert json.loads(event.result) == lookup_deadlines("MBA")


def test_tool_events_only_include_current_turn(fake_model):
    agent = EnrollmentAgent(
        fake_model(
            [
                tool_call("check_application_status", applicant_id="APP-1042"),
                answer("Documents Pending"),
                answer("You're welcome!"),
            ]
        )
    )
    session = agent.new_session()

    first = agent.chat("Status for APP-1042?", session)
    second = agent.chat("Thanks", session)

    assert [e.name for e in first.tool_events] == ["check_application_status"]
    assert json.loads(first.tool_events[0].result) == lookup_application("APP-1042")
    assert second.tool_events == []
    assert second.reply == "You're welcome!"


def test_new_session_ids_are_unique(fake_model):
    agent = EnrollmentAgent(fake_model([]))
    assert agent.new_session() != agent.new_session()


def test_sessions_are_isolated(fake_model):
    model = fake_model([answer("a"), answer("b")])
    agent = EnrollmentAgent(model)

    agent.chat("My ID is APP-1042", agent.new_session())
    agent.chat("What's my ID?", agent.new_session())

    assert "My ID is APP-1042" not in [m.content for m in model.received[1]]
