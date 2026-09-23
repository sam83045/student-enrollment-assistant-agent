"""T-11: CLI chat loop (FR-9, NFR-3)."""

import httpx
import openai

from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.cli import repl

from .conftest import answer, tool_call


def run_repl(agent, inputs, verbose=False):
    lines = iter(inputs)
    output = []

    def fake_input(prompt):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    repl(agent, verbose=verbose, input_fn=fake_input, output_fn=output.append)
    return "\n".join(output)


def test_chats_until_exit(fake_model):
    agent = EnrollmentAgent(fake_model([answer("Hello!"), answer("Bye!")]))

    out = run_repl(agent, ["Hi", "", "Thanks", "exit", "never sent"])

    assert "Hello!" in out
    assert "Bye!" in out
    assert "never sent" not in out


def test_quit_and_eof_end_session(fake_model):
    agent = EnrollmentAgent(fake_model([]))
    assert "Goodbye" in run_repl(agent, ["QUIT"])
    assert "Goodbye" in run_repl(agent, [])  # EOF / Ctrl+Z


def test_one_session_keeps_memory(fake_model):
    model = fake_model([answer("Noted."), answer("Your ID is APP-1042.")])
    agent = EnrollmentAgent(model)

    run_repl(agent, ["My ID is APP-1042", "What's my ID?"])

    assert "My ID is APP-1042" in [m.content for m in model.received[1]]


def test_verbose_prints_tool_calls(fake_model):
    agent = EnrollmentAgent(
        fake_model([tool_call("get_deadlines", program_name="MBA"), answer("March 1")])
    )

    quiet = run_repl(agent, ["MBA deadline?"])
    assert "get_deadlines" not in quiet

    agent = EnrollmentAgent(
        fake_model([tool_call("get_deadlines", program_name="MBA"), answer("March 1")])
    )
    verbose = run_repl(agent, ["MBA deadline?"], verbose=True)
    assert "get_deadlines" in verbose
    assert "2027-03-01" in verbose


class _UnreachableAgent:
    def new_session(self):
        return "s"

    def chat(self, message, session_id):
        raise openai.APIConnectionError(request=httpx.Request("POST", "http://localhost:1234/v1"))


def test_connection_error_is_friendly_and_loop_continues():
    out = run_repl(_UnreachableAgent(), ["Hi", "Hello again"])

    assert out.count("Couldn't reach the language model") == 2
    assert "Traceback" not in out
