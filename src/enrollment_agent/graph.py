"""LangGraph agent: reason → act → observe loop with per-thread memory (FR-5, FR-7, design §7)."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from enrollment_agent.config import DEFAULT_MAX_ITERATIONS
from enrollment_agent.prompts import ESCALATION_MESSAGE, SYSTEM_PROMPT


def _model_calls_this_turn(messages: list) -> int:
    """AI messages since the latest user message."""
    count = 0
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            break
        if isinstance(message, AIMessage):
            count += 1
    return count


def build_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    model_with_tools = model.bind_tools(tools)

    def capped(state: MessagesState) -> bool:
        return _model_calls_this_turn(state["messages"]) >= max_iterations

    def prompt(state: MessagesState) -> list:
        return [SystemMessage(SYSTEM_PROMPT), *state["messages"]]

    def agent(state: MessagesState) -> dict:
        if capped(state):
            return {"messages": [AIMessage(ESCALATION_MESSAGE)]}
        return {"messages": [model_with_tools.invoke(prompt(state))]}

    async def aagent(state: MessagesState) -> dict:
        if capped(state):
            return {"messages": [AIMessage(ESCALATION_MESSAGE)]}
        return {"messages": [await model_with_tools.ainvoke(prompt(state))]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", RunnableLambda(agent, afunc=aagent, name="agent"))
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, ["tools", END])
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer or InMemorySaver())
