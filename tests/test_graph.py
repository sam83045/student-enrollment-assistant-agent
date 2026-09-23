"""T-09: LangGraph agent loop and memory with a fake model (FR-5, FR-7)."""

import itertools
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from enrollment_agent.graph import build_graph
from enrollment_agent.prompts import ESCALATION_MESSAGE, SYSTEM_PROMPT
from enrollment_agent.tools import TOOLS, lookup_deadlines

from .conftest import answer, tool_call, tool_calls


def run(graph, text, thread="t1"):
    config = {"configurable": {"thread_id": thread}}
    return graph.invoke({"messages": [HumanMessage(text)]}, config)["messages"]


def test_direct_answer_without_tools(fake_model):
    graph = build_graph(fake_model([answer("Hello!")]), TOOLS)

    messages = run(graph, "Hi")

    assert [type(m) for m in messages] == [HumanMessage, AIMessage]
    assert messages[-1].content == "Hello!"


def test_single_tool_call_then_answer(fake_model):  # AC-5.2
    graph = build_graph(
        fake_model([tool_call("get_deadlines", program_name="MBA"), answer("March 1")]), TOOLS
    )

    messages = run(graph, "MBA deadline?")

    assert [type(m) for m in messages] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
    assert json.loads(messages[2].content) == lookup_deadlines("MBA")
    assert messages[-1].content == "March 1"


def test_tool_result_is_sent_back_to_model(fake_model):  # AC-5.2
    model = fake_model([tool_call("get_deadlines", program_name="MBA"), answer("ok")])
    graph = build_graph(model, TOOLS)

    run(graph, "MBA deadline?")

    second_prompt = model.received[1]
    assert isinstance(second_prompt[-1], ToolMessage)
    assert "2027-03-01" in second_prompt[-1].content


def test_multiple_tool_calls_in_one_message(fake_model):  # AC-5.3
    graph = build_graph(
        fake_model(
            [
                tool_calls(
                    ("get_program_info", {"program_name": "MBA"}),
                    ("check_application_status", {"applicant_id": "APP-1042"}),
                ),
                answer("done"),
            ]
        ),
        TOOLS,
    )

    messages = run(graph, "MBA info and my status APP-1042")

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    assert {m.name for m in tool_messages} == {"get_program_info", "check_application_status"}


def test_bad_tool_arguments_return_error_and_continue(fake_model):  # AC-5.5
    graph = build_graph(
        fake_model([tool_call("get_deadlines", wrong_arg="x"), answer("Sorry, try again.")]),
        TOOLS,
    )

    messages = run(graph, "deadline?")

    error = next(m for m in messages if isinstance(m, ToolMessage))
    assert error.status == "error"
    assert messages[-1].content == "Sorry, try again."


def test_system_prompt_sent_but_not_stored(fake_model):
    model = fake_model([answer("Hi")])
    graph = build_graph(model, TOOLS)

    messages = run(graph, "Hello")

    assert isinstance(model.received[0][0], SystemMessage)
    assert model.received[0][0].content == SYSTEM_PROMPT
    assert not any(isinstance(m, SystemMessage) for m in messages)


def test_iteration_cap_escalates_and_session_recovers(fake_model):  # AC-5.4
    endless = itertools.chain(
        (tool_call("get_program_info", program_name="cs") for _ in range(3)),
        [answer("Back to normal")],
    )
    model = fake_model(endless)
    graph = build_graph(model, TOOLS, max_iterations=3)

    first = run(graph, "loop forever")

    assert first[-1].content == ESCALATION_MESSAGE
    assert len(model.received) == 3  # model called exactly max_iterations times
    assert all(  # every tool call got a result: history is valid
        any(isinstance(m, ToolMessage) and m.tool_call_id == c["id"] for m in first)
        for ai in first
        if isinstance(ai, AIMessage)
        for c in ai.tool_calls
    )

    second = run(graph, "hello again")
    assert second[-1].content == "Back to normal"


def test_history_persists_within_thread(fake_model):  # AC-7.1
    model = fake_model([answer("first"), answer("second")])
    graph = build_graph(model, TOOLS)

    run(graph, "My ID is APP-1042", thread="s1")
    run(graph, "What's my status?", thread="s1")

    second_prompt_texts = [m.content for m in model.received[1]]
    assert "My ID is APP-1042" in second_prompt_texts
    assert "first" in second_prompt_texts


def test_new_thread_starts_empty(fake_model):  # AC-7.4
    model = fake_model([answer("first"), answer("second")])
    graph = build_graph(model, TOOLS)

    run(graph, "My ID is APP-1042", thread="s1")
    messages = run(graph, "What's my status?", thread="s2")

    assert [m.content for m in messages] == ["What's my status?", "second"]
    assert "My ID is APP-1042" not in [m.content for m in model.received[1]]
