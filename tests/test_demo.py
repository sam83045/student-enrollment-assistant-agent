"""T-12: demo runner and log rendering (FR-10)."""

from datetime import datetime

from enrollment_agent.agent import EnrollmentAgent, ToolEvent, TurnResult
from enrollment_agent.demo import DEMO_TURNS, DemoTurn, render_log, run_demo

from .conftest import answer, tool_call


def test_demo_turns_match_case_study():
    assert DEMO_TURNS == [
        "Hi, what programs do you offer in computer science?",
        "What's the application deadline for that?",
        "I already applied. My ID is APP-1042. What's my status?",
        "Can I get a fee waiver?",
        "What documents do I still need to submit?",
    ]


def test_run_demo_uses_one_session(fake_model):
    model = fake_model([answer(f"reply {i}") for i in range(1, 6)])

    turns = run_demo(EnrollmentAgent(model))

    assert [t.number for t in turns] == [1, 2, 3, 4, 5]
    assert [t.result.reply for t in turns] == [f"reply {i}" for i in range(1, 6)]
    last_prompt = [m.content for m in model.received[-1]]
    assert DEMO_TURNS[0] in last_prompt  # turn 5 saw turn 1: same session


def test_run_demo_reports_progress(fake_model):
    seen = []
    run_demo(EnrollmentAgent(fake_model([answer("x")] * 5)), on_turn=seen.append)
    assert [t.number for t in seen] == [1, 2, 3, 4, 5]


def test_render_log_contains_everything():
    turns = [
        DemoTurn(
            1,
            "MBA deadline?",
            TurnResult(
                "It's March 1.",
                [ToolEvent("get_deadlines", {"program_name": "MBA"}, '{"a": 1}')],
            ),
            2.5,
        ),
        DemoTurn(2, "Fee waiver?", TurnResult("Talk to a counselor.", []), 1.0),
    ]

    log = render_log(
        turns, model="gpt-x", base_url=None, timestamp=datetime(2026, 9, 23, 14, 5)
    )

    assert "`gpt-x`" in log
    assert "OpenAI default" in log
    assert "2026-09-23 14:05" in log
    assert "## Turn 1" in log and "## Turn 2" in log
    assert "MBA deadline?" in log
    assert "`get_deadlines`" in log
    assert '"program_name": "MBA"' in log
    assert '"a": 1' in log  # pretty-printed result
    assert "It's March 1." in log
    assert "2.5 s" in log
    assert "_No tool calls._" in log


def test_render_log_multiline_reply_stays_quoted():
    turns = [DemoTurn(1, "Hi", TurnResult("line one\n\nline two"), 1.0)]
    log = render_log(turns, model="m", base_url="http://x/v1", timestamp=datetime.now())
    assert "> line one\n>\n> line two" in log
