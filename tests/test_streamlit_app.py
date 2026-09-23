"""T-19: Streamlit chat UI with a stub API client (FR-13, NFR-8)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from enrollment_agent import api_client
from enrollment_agent.api_client import ApiError

APP = str(Path(__file__).parents[1] / "src" / "enrollment_agent" / "streamlit_app.py")

TOOL_EVENT = {
    "name": "get_deadlines",
    "args": {"program_name": "MBA"},
    "result": '{"program_name": "Master of Business Administration"}',
}


class StubClient:
    def __init__(self, replies=(), healthy=True):
        self.replies = list(replies)
        self.healthy = healthy
        self.calls = []

    def health(self):
        if not self.healthy:
            raise ApiError("Couldn't reach the API at http://localhost:8000.")
        return {"status": "ok", "model": "stub-model"}

    def chat(self, message, session_id):
        self.calls.append((message, session_id))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def reply(text, session_id="sess-1", tool_events=()):
    return {"session_id": session_id, "reply": text, "tool_events": list(tool_events)}


@pytest.fixture
def app(monkeypatch):
    def start(stub: StubClient) -> AppTest:
        monkeypatch.setattr(api_client, "client_from_env", lambda: stub)
        return AppTest.from_file(APP, default_timeout=15).run()

    return start


def send(at: AppTest, text: str) -> AppTest:
    return at.chat_input[0].set_value(text).run()


def test_message_and_reply_are_shown(app):  # AC-13.1
    at = send(app(StubClient([reply("Hello there!")])), "Hi")

    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert at.chat_message[0].markdown[0].value == "Hi"
    assert at.chat_message[1].markdown[0].value == "Hello there!"


def test_session_id_is_reused(app):  # AC-13.3
    stub = StubClient([reply("one", "sess-1"), reply("two", "sess-1")])
    at = app(stub)

    send(at, "My ID is APP-1042")
    send(at, "What's my status?")

    assert stub.calls == [("My ID is APP-1042", None), ("What's my status?", "sess-1")]
    assert len(at.chat_message) == 4


def test_tool_calls_panel(app):  # AC-13.4
    at = send(app(StubClient([reply("March 1", tool_events=[TOOL_EVENT])])), "MBA deadline?")

    [panel] = at.expander
    assert panel.label == "Tool calls (1)"
    assert any("get_deadlines" in m.value for m in panel.markdown)


def test_reply_without_tools_has_no_panel(app):
    at = send(app(StubClient([reply("Hello")])), "Hi")
    assert len(at.expander) == 0


def test_new_conversation_resets(app):  # AC-13.5
    stub = StubClient([reply("one", "sess-1"), reply("fresh", "sess-2")])
    at = send(app(stub), "Hi")

    at.sidebar.button[0].click().run()

    assert len(at.chat_message) == 0
    assert at.session_state.session_id is None
    send(at, "Hello again")
    assert stub.calls[-1] == ("Hello again", None)


def test_api_error_is_shown_without_assistant_reply(app):  # AC-13.6
    at = send(app(StubClient([ApiError("The language model is unreachable.")])), "Hi")

    assert [m.name for m in at.chat_message] == ["user"]
    assert any("unreachable" in e.value for e in at.main.error)
    assert not at.exception


def test_can_retry_after_error(app):  # AC-13.6
    stub = StubClient([ApiError("boom"), reply("Recovered")])
    at = send(app(stub), "Hi")

    send(at, "Hi")

    assert at.chat_message[-1].markdown[0].value == "Recovered"


def test_sidebar_shows_model_when_api_up(app):  # AC-13.7
    at = app(StubClient())
    assert any("stub-model" in s.value for s in at.sidebar.success)


def test_sidebar_shows_error_when_api_down(app):  # AC-13.7
    at = app(StubClient(healthy=False))
    assert any("Couldn't reach the API" in e.value for e in at.sidebar.error)
    assert not at.exception
