"""UI-independent facade over the agent graph (NFR-6, design §8)."""

import uuid
from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from enrollment_agent.config import DEFAULT_MAX_ITERATIONS
from enrollment_agent.graph import build_graph
from enrollment_agent.tools import TOOLS


@dataclass
class ToolEvent:
    name: str
    args: dict
    result: str | None = None


@dataclass
class TurnResult:
    reply: str
    tool_events: list[ToolEvent] = field(default_factory=list)


def _text(content: str | list) -> str:
    """Flatten message content that some providers return as a list of parts."""
    if isinstance(content, str):
        return content
    return "".join(
        part if isinstance(part, str) else part.get("text", "")
        for part in content
    )


class EnrollmentAgent:
    def __init__(
        self,
        model: BaseChatModel,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self._graph = build_graph(model, TOOLS, max_iterations, checkpointer)
        self._recursion_limit = 2 * max_iterations + 5  # safety net; the cap lives in the graph

    def new_session(self) -> str:
        return uuid.uuid4().hex

    def chat(self, message: str, session_id: str) -> TurnResult:
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": self._recursion_limit,
        }
        before = len(self._graph.get_state(config).values.get("messages", []))
        state = self._graph.invoke({"messages": [HumanMessage(message)]}, config)
        new_messages = state["messages"][before:]

        events: dict[str, ToolEvent] = {}
        for msg in new_messages:
            if isinstance(msg, AIMessage):
                for call in msg.tool_calls:
                    events[call["id"]] = ToolEvent(call["name"], call["args"])
            elif isinstance(msg, ToolMessage) and msg.tool_call_id in events:
                events[msg.tool_call_id].result = _text(msg.content)

        return TurnResult(reply=_text(new_messages[-1].content), tool_events=list(events.values()))
