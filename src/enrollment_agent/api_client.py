"""HTTP client for the enrollment API, used by the Streamlit UI (FR-13, design §15.3)."""

import os

import httpx

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 180.0  # local models can be slow


class ApiError(Exception):
    """An API failure with a message that is safe to show to the user."""


class ApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ):
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )

    def chat(self, message: str, session_id: str | None) -> dict:
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        return self._request("POST", "/chat", json=payload)

    def health(self) -> dict:
        return self._request("GET", "/health")

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise ApiError("The assistant took too long to respond. Please try again.") from None
        except httpx.HTTPError:
            raise ApiError(
                f"Couldn't reach the API at {self._http.base_url}. Is `enrollment-api` running?"
            ) from None

        if response.is_success:
            return response.json()
        raise ApiError(_error_detail(response))


def client_from_env() -> ApiClient:
    """Client for the API at ``$API_URL`` (default http://localhost:8000)."""
    return ApiClient(os.getenv("API_URL", DEFAULT_API_URL))


def _error_detail(response: httpx.Response) -> str:
    try:
        detail = response.json()["detail"]
    except (ValueError, KeyError, TypeError):
        return f"The API returned an error (HTTP {response.status_code})."
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(item.get("msg", str(item)) for item in detail)
    return str(detail)
