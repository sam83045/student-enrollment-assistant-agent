"""Shared test helpers: a fake tool-calling chat model (T-08, NFR-2)."""

import itertools
from collections.abc import Iterable

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import Field


class FakeToolChatModel(GenericFakeChatModel):
    """Returns scripted AIMessages in order and records every prompt it receives."""

    received: list[list[BaseMessage]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


_ids = itertools.count(1)


def tool_call(name: str, **args) -> AIMessage:
    """An AI message requesting a single tool call."""
    return tool_calls((name, args))


def tool_calls(*calls: tuple[str, dict]) -> AIMessage:
    """An AI message requesting several tool calls at once."""
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"call_{next(_ids)}"} for n, a in calls],
    )


def answer(text: str) -> AIMessage:
    return AIMessage(content=text)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_model():
    """Factory: ``fake_model([msg, msg, ...])`` or ``fake_model(infinite_iterator)``."""

    def make(script: Iterable[AIMessage]) -> FakeToolChatModel:
        return FakeToolChatModel(messages=iter(script))

    return make
