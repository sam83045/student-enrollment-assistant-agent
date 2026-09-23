"""T-06: settings loading (FR-11, NFR-4)."""

import pytest

from enrollment_agent.config import ConfigError, load_settings

ENV_VARS = ["LLM_BASE_URL", "LLM_MODEL", "OPENAI_API_KEY", "AGENT_MAX_ITERATIONS"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # setenv first so monkeypatch also undoes values that load_dotenv sets during a test
    for name in ENV_VARS:
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)


def test_reads_values_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen_qwen3.5-4b")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", "3")

    settings = load_settings(env_file=None)

    assert settings.base_url == "http://localhost:1234/v1"
    assert settings.model == "qwen_qwen3.5-4b"
    assert settings.api_key == "lm-studio"
    assert settings.max_iterations == 3


def test_defaults(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    settings = load_settings(env_file=None)

    assert settings.base_url is None  # OpenAI default endpoint
    assert settings.max_iterations == 5


def test_reads_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_MODEL=from-file\nOPENAI_API_KEY=key-from-file\n")

    settings = load_settings(env_file=env_file)

    assert settings.model == "from-file"
    assert settings.api_key == "key-from-file"


@pytest.mark.parametrize("missing", ["LLM_MODEL", "OPENAI_API_KEY"])
def test_missing_required_value_raises_clear_error(monkeypatch, missing):
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigError, match=missing):
        load_settings(env_file=None)


@pytest.mark.parametrize("value", ["zero", "0", "-1"])
def test_invalid_max_iterations_raises(monkeypatch, value):
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", value)

    with pytest.raises(ConfigError, match="AGENT_MAX_ITERATIONS"):
        load_settings(env_file=None)
