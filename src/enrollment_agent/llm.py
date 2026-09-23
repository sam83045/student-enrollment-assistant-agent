"""Chat model factory for any OpenAI-compatible endpoint (FR-11, design §6)."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from enrollment_agent.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    """OpenAI API, LM Studio or Ollama — selected purely by ``settings.base_url``."""
    return ChatOpenAI(
        model=settings.model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        temperature=0,
    )
