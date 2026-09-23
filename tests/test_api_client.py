"""T-18: HTTP client used by the Streamlit UI (FR-13, NFR-8)."""

import json

import httpx
import pytest

from enrollment_agent.api_client import ApiClient, ApiError

CHAT_REPLY = {"session_id": "abc", "reply": "Hello", "tool_events": []}


def client_with(handler) -> ApiClient:
    return ApiClient("http://api.test", transport=httpx.MockTransport(handler))


def test_chat_without_session_id_sends_message_only():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=CHAT_REPLY)

    result = client_with(handler).chat("Hi", None)

    assert seen["url"] == "http://api.test/chat"
    assert seen["body"] == {"message": "Hi"}
    assert result == CHAT_REPLY


def test_chat_with_session_id_sends_it():
    seen = {}

    def handler(request: httpx.Request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=CHAT_REPLY)

    client_with(handler).chat("Hi again", "abc")

    assert seen["body"] == {"message": "Hi again", "session_id": "abc"}


def test_health_returns_json():
    def handler(request: httpx.Request):
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "model": "qwen"})

    assert client_with(handler).health() == {"status": "ok", "model": "qwen"}


def test_trailing_slash_in_base_url_is_ignored():
    def handler(request: httpx.Request):
        assert str(request.url) == "http://api.test/health"
        return httpx.Response(200, json={"status": "ok", "model": "m"})

    ApiClient("http://api.test/", transport=httpx.MockTransport(handler)).health()


def test_connection_error_raises_api_error():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ApiError, match="Couldn't reach the API"):
        client_with(handler).chat("Hi", None)


def test_timeout_raises_api_error():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ApiError, match="took too long"):
        client_with(handler).chat("Hi", None)


@pytest.mark.parametrize("status", [502, 503])
def test_server_error_detail_is_included(status):
    def handler(request):
        return httpx.Response(status, json={"detail": "The language model is unreachable."})

    with pytest.raises(ApiError, match="The language model is unreachable."):
        client_with(handler).chat("Hi", None)


def test_non_json_error_falls_back_to_status():
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    with pytest.raises(ApiError, match="500"):
        client_with(handler).health()


def test_validation_error_detail_list_is_readable():
    def handler(request):
        return httpx.Response(
            422, json={"detail": [{"msg": "String should have at least 1 character"}]}
        )

    with pytest.raises(ApiError, match="at least 1 character"):
        client_with(handler).chat(" ", None)
