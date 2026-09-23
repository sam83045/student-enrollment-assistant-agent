"""Interactive CLI chat (FR-9, NFR-3, design §10).

Usage: uv run enrollment-agent [--verbose] [--env-file PATH]
"""

import argparse
import json
from collections.abc import Callable

import openai

from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.config import ConfigError, load_settings
from enrollment_agent.llm import build_chat_model

EXIT_COMMANDS = {"exit", "quit"}


def repl(
    agent: EnrollmentAgent,
    *,
    verbose: bool = False,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run one chat session until the user types exit/quit or sends EOF."""
    session_id = agent.new_session()
    output_fn("Student Enrollment Assistant. Type 'exit' to quit.\n")

    while True:
        try:
            text = input_fn("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            result = agent.chat(text, session_id)
        except openai.APIConnectionError:
            output_fn(
                "[error] Couldn't reach the language model. "
                "Check that LM Studio (or your configured endpoint) is running.\n"
            )
            continue
        except openai.APIError as exc:
            output_fn(f"[error] The language model returned an error: {exc}\n")
            continue

        if verbose:
            for event in result.tool_events:
                output_fn(f"  [tool] {event.name}({json.dumps(event.args)})")
                output_fn(f"         -> {event.result}")
        output_fn(f"Assistant: {result.reply}\n")

    output_fn("Goodbye!")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chat with the Student Enrollment Assistant.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show tool calls and results")
    parser.add_argument("--env-file", default=".env", help="settings file (default: .env)")
    args = parser.parse_args(argv)

    try:
        settings = load_settings(args.env_file)
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from None

    agent = EnrollmentAgent(build_chat_model(settings), settings.max_iterations)
    repl(agent, verbose=args.verbose)


if __name__ == "__main__":
    main()
