"""The case-study demo conversation and its Markdown log (FR-10, design §10)."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from enrollment_agent.agent import EnrollmentAgent, TurnResult

DEMO_TURNS = [
    "Hi, what programs do you offer in computer science?",
    "What's the application deadline for that?",
    "I already applied. My ID is APP-1042. What's my status?",
    "Can I get a fee waiver?",
    "What documents do I still need to submit?",
]


@dataclass
class DemoTurn:
    number: int
    user: str
    result: TurnResult
    seconds: float


def run_demo(
    agent: EnrollmentAgent,
    turns: list[str] = DEMO_TURNS,
    on_turn: Callable[[DemoTurn], None] | None = None,
) -> list[DemoTurn]:
    """Run every turn in a single session and return the transcript."""
    session_id = agent.new_session()
    transcript = []
    for number, text in enumerate(turns, 1):
        start = time.perf_counter()
        result = agent.chat(text, session_id)
        turn = DemoTurn(number, text, result, time.perf_counter() - start)
        transcript.append(turn)
        if on_turn:
            on_turn(turn)
    return transcript


def _pretty(result: str | None) -> str:
    try:
        return json.dumps(json.loads(result), indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(result)


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def render_log(
    turns: list[DemoTurn], *, model: str, base_url: str | None, timestamp: datetime
) -> str:
    lines = [
        "# Demo Log: Student Enrollment Assistant Agent",
        "",
        f"- **Model:** `{model}`",
        f"- **Endpoint:** `{base_url}`" if base_url else "- **Endpoint:** OpenAI default",
        f"- **Run at:** {timestamp:%Y-%m-%d %H:%M}",
        f"- **Session:** one session, {len(turns)} turns",
    ]
    for turn in turns:
        lines += ["", f"## Turn {turn.number}", "", "**User:**", "", _quote(turn.user), ""]
        if turn.result.tool_events:
            lines.append("**Tool calls:**")
            for i, event in enumerate(turn.result.tool_events, 1):
                lines += [
                    "",
                    f"{i}. `{event.name}` with `{json.dumps(event.args, ensure_ascii=False)}`",
                    "",
                    "   ```json",
                    *(f"   {line}" for line in _pretty(event.result).splitlines()),
                    "   ```",
                ]
        else:
            lines.append("_No tool calls._")
        lines += ["", "**Agent:**", "", _quote(turn.result.reply), "", f"_{turn.seconds:.1f} s_"]
    return "\n".join(lines) + "\n"
