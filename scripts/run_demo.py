"""Run the 5-turn case-study conversation and write a Markdown log (FR-10).

Usage:
    uv run python scripts/run_demo.py                          # provider from .env
    uv run python scripts/run_demo.py --env-file .env.openai --output docs/demo_log.md
"""

import argparse
from datetime import datetime
from pathlib import Path

from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.config import ConfigError, load_settings
from enrollment_agent.demo import DemoTurn, render_log, run_demo
from enrollment_agent.llm import build_chat_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", default=".env", help="settings file (default: .env)")
    parser.add_argument("--output", default="docs/demo_log.md", help="log file to write")
    args = parser.parse_args()

    try:
        settings = load_settings(args.env_file)
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from None

    print(f"Running demo with {settings.model} at {settings.base_url or 'OpenAI default'}")
    agent = EnrollmentAgent(build_chat_model(settings), settings.max_iterations)

    def progress(turn: DemoTurn) -> None:
        tools = ", ".join(e.name for e in turn.result.tool_events) or "no tools"
        print(f"  Turn {turn.number}: {tools} ({turn.seconds:.1f} s)")

    turns = run_demo(agent, on_turn=progress)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    log = render_log(
        turns, model=settings.model, base_url=settings.base_url, timestamp=datetime.now()
    )
    output.write_text(log, encoding="utf-8", newline="\n")
    print(f"Log written to {output}")


if __name__ == "__main__":
    main()
