"""Settings loaded from the environment / .env (FR-11, NFR-4, design §6)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_MAX_ITERATIONS = 5


class ConfigError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    model: str
    api_key: str
    base_url: str | None = None  # None → OpenAI's default endpoint
    max_iterations: int = DEFAULT_MAX_ITERATIONS


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Build Settings from environment variables, loading ``env_file`` first if given.

    Existing environment variables take precedence over values in the file.
    """
    if env_file is not None:
        load_dotenv(env_file, override=False)

    missing = [name for name in ("LLM_MODEL", "OPENAI_API_KEY") if not os.getenv(name)]
    if missing:
        raise ConfigError(
            f"Missing required setting(s): {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in."
        )

    raw_iterations = os.getenv("AGENT_MAX_ITERATIONS", str(DEFAULT_MAX_ITERATIONS))
    try:
        max_iterations = int(raw_iterations)
    except ValueError:
        max_iterations = 0
    if max_iterations < 1:
        raise ConfigError(
            f"AGENT_MAX_ITERATIONS must be a positive integer, got {raw_iterations!r}."
        )

    return Settings(
        model=os.environ["LLM_MODEL"],
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("LLM_BASE_URL") or None,
        max_iterations=max_iterations,
    )
