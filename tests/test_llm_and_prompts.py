"""T-07: model factory and system prompt (FR-6, FR-8, FR-11)."""

from enrollment_agent.config import Settings
from enrollment_agent.llm import build_chat_model
from enrollment_agent.prompts import ESCALATION_MESSAGE, SYSTEM_PROMPT


def test_build_chat_model_passes_settings_through():
    settings = Settings(
        base_url="http://localhost:1234/v1", model="qwen_qwen3.5-4b", api_key="lm-studio"
    )

    model = build_chat_model(settings)

    assert model.model_name == "qwen_qwen3.5-4b"
    assert model.openai_api_base == "http://localhost:1234/v1"
    assert model.openai_api_key.get_secret_value() == "lm-studio"
    assert model.temperature == 0


def test_escalation_message_matches_case_study():  # AC-8.1
    assert ESCALATION_MESSAGE == (
        "I'd recommend speaking with an enrollment counselor for that. "
        "Would you like me to connect you?"
    )


def test_system_prompt_contains_escalation_message():  # AC-8.1
    assert ESCALATION_MESSAGE in SYSTEM_PROMPT


def test_system_prompt_names_every_tool():
    for name in ["get_program_info", "check_application_status", "get_deadlines"]:
        assert name in SYSTEM_PROMPT
