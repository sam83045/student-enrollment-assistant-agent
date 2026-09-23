"""T-17: FastAPI HTTP API (FR-12, NFR-7, NFR-8)."""

import json

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from enrollment_agent import api
from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.config import ConfigError, Settings
from enrollment_agent.tools import lookup_deadlines

from .conftest import answer, tool_call


def client_for(agent, model_name="fake-model") -> TestClient:
    return TestClient(api.create_app(agent, model_name=model_name))


def test_chat_response_shape(fake_model):  # AC-12.1
    client = client_for(
        EnrollmentAgent(
            fake_model([tool_call("get_deadlines", program_name="MBA"), answer("March 1")])
        )
    )

    response = client.post("/chat", json={"message": "MBA deadline?"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"session_id", "reply", "tool_events"}
    assert body["reply"] == "March 1"
    [event] = body["tool_events"]
    assert event["name"] == "get_deadlines"
    assert event["args"] == {"program_name": "MBA"}
    assert json.loads(event["result"]) == lookup_deadlines("MBA")


def test_new_session_then_reuse_keeps_memory(fake_model):  # AC-12.2, AC-12.3
    model = fake_model([answer("Noted."), answer("Your ID is APP-1042.")])
    client = client_for(EnrollmentAgent(model))

    first = client.post("/chat", json={"message": "My ID is APP-1042"}).json()
    assert first["session_id"]

    second = client.post(
        "/chat", json={"message": "What's my ID?", "session_id": first["session_id"]}
    ).json()

    assert second["session_id"] == first["session_id"]
    assert "My ID is APP-1042" in [m.content for m in model.received[1]]


def test_sessions_are_isolated(fake_model):  # AC-12.3
    model = fake_model([answer("a"), answer("b")])
    client = client_for(EnrollmentAgent(model))

    first = client.post("/chat", json={"message": "My ID is APP-1042"}).json()
    second = client.post("/chat", json={"message": "What's my ID?"}).json()

    assert first["session_id"] != second["session_id"]
    assert "My ID is APP-1042" not in [m.content for m in model.received[1]]


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_empty_message_rejected(fake_model, message):  # AC-12.4
    client = client_for(EnrollmentAgent(fake_model([])))
    assert client.post("/chat", json={"message": message}).status_code == 422


def test_missing_message_rejected(fake_model):  # AC-12.4
    client = client_for(EnrollmentAgent(fake_model([])))
    assert client.post("/chat", json={}).status_code == 422


class _FailingAgent:
    def __init__(self, error):
        self.error = error

    def new_session(self):
        return "s"

    async def achat(self, message, session_id):
        raise self.error


_REQUEST = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")


def test_llm_unreachable_returns_503():  # AC-12.5
    client = client_for(_FailingAgent(openai.APIConnectionError(request=_REQUEST)))

    response = client.post("/chat", json={"message": "Hi"})

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"]


def test_other_llm_error_returns_502():  # AC-12.5
    client = client_for(_FailingAgent(openai.APIError("model not loaded", _REQUEST, body=None)))

    response = client.post("/chat", json={"message": "Hi"})

    assert response.status_code == 502
    assert "model not loaded" in response.json()["detail"]


def test_health(fake_model):  # AC-12.6
    response = client_for(EnrollmentAgent(fake_model([])), model_name="qwen").get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "qwen"}


def test_lifespan_builds_agent_from_settings(monkeypatch, fake_model):
    monkeypatch.setattr(
        api, "load_settings", lambda env_file=".env": Settings(model="from-settings", api_key="k")
    )
    monkeypatch.setattr(api, "build_chat_model", lambda settings: fake_model([answer("hi")]))

    with TestClient(api.create_app()) as client:
        assert client.get("/health").json()["model"] == "from-settings"
        assert client.post("/chat", json={"message": "Hello"}).json()["reply"] == "hi"


def test_lifespan_config_error_stops_startup(monkeypatch):
    def broken(env_file=".env"):
        raise ConfigError("Missing required setting(s): LLM_MODEL.")

    monkeypatch.setattr(api, "load_settings", broken)

    with pytest.raises(ConfigError, match="LLM_MODEL"):
        with TestClient(api.create_app()):
            pass
