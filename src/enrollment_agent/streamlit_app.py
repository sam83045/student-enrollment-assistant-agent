"""Streamlit chat UI, a thin client of the enrollment API (FR-13, design §15.4).

Usage: uv run streamlit run src/enrollment_agent/streamlit_app.py
"""

import json

import streamlit as st

from enrollment_agent import api_client
from enrollment_agent.api_client import ApiError

st.set_page_config(page_title="Enrollment Assistant", page_icon="🎓")

state = st.session_state
if "client" not in state:
    state.client = api_client.client_from_env()
if "messages" not in state:
    state.messages = []
    state.session_id = None


def new_conversation() -> None:
    state.messages = []
    state.session_id = None


def render_tool_events(events: list[dict]) -> None:
    with st.expander(f"Tool calls ({len(events)})"):
        for event in events:
            st.markdown(f"**`{event['name']}`**")
            st.caption("Arguments")
            st.json(event["args"])
            st.caption("Result")
            try:
                st.json(json.loads(event["result"]))
            except (TypeError, ValueError):
                st.code(event["result"] or "")


def render(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tool_events"):
            render_tool_events(message["tool_events"])


with st.sidebar:
    st.header("Enrollment Assistant")
    try:
        health = state.client.health()
        st.success(f"API connected · model `{health['model']}`")
    except ApiError as exc:
        st.error(str(exc))
    st.button("New conversation", on_click=new_conversation, width="stretch")
    st.caption("Answers come from the admissions tools. Each reply's tool calls are listed under it.")

st.title("🎓 Student Enrollment Assistant")
st.caption("Ask about programs, deadlines or your application status.")

for message in state.messages:
    render(message)

if prompt := st.chat_input("Ask about programs, deadlines or your application…"):
    user_message = {"role": "user", "content": prompt}
    state.messages.append(user_message)
    render(user_message)

    try:
        with st.spinner("Thinking…"):
            data = state.client.chat(prompt, state.session_id)
    except ApiError as exc:
        st.error(str(exc))
    else:
        state.session_id = data["session_id"]
        assistant_message = {
            "role": "assistant",
            "content": data["reply"],
            "tool_events": data["tool_events"],
        }
        state.messages.append(assistant_message)
        render(assistant_message)
