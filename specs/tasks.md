# Tasks — Student Enrollment Assistant Agent

Implements: [requirements.md](requirements.md) · [design.md](design.md)
Status: **Approved**: Phase 1 (A–E) and Phase 2 (F–G), 2026-09-23

Rules:
- Work top to bottom. Write each task's tests first, then implement until they pass.
- A task is done when its "Done when" line is true and `uv run pytest` is green.
- Check off tasks (`[x]`) as they complete. Commit at the end of each phase after review.

---

## Phase A — Project Setup

- [x] **T-01 Scaffold the uv project** · NFR-1, NFR-4
  - Create a packaged project with a `src/` layout and Python 3.12 (`requires-python >= 3.11`).
  - Add deps: `langchain-core`, `langchain-openai`, `langgraph`, `python-dotenv`; dev: `pytest`.
  - Add the console script `enrollment-agent = enrollment_agent.cli:main`.
  - Configure pytest: `testpaths = tests`, register the `live` marker, skip live tests by default.
  - Add `.gitignore` (`.venv/`, `.env`, `__pycache__/`, `.pytest_cache/`) and `.env.example` (design §6).
  - Done when: `uv sync` succeeds and `uv run pytest` runs (0 tests).

## Phase B — Data and Tools (no LLM)

- [x] **T-02 Mock data** · FR-4 · design §4
  - `data.py`: `PROGRAMS` (4, with aliases), `DEADLINES`, `APPLICANTS` (4).
  - Tests: ≥3 programs incl. CS; ≥3 applicants; APP-1042 is `Documents Pending` with
    non-empty `missing_documents`; every program has deadlines; every applicant's program exists.
  - Done when: AC-4.1–4.3 are covered by passing tests.

- [x] **T-03 Program name matching** · FR-1, FR-3 · design §5.2
  - Normalization, filler-token removal, exact match, then keyword match.
  - Tests: `"M.S. Computer Science"` → ms-cs; `"computer science"` → bs-cs + ms-cs;
    `"cs"` alias; case/punctuation insensitivity; `"all programs"` → all; `"art history"` → none.
  - Done when: matching tests pass.

- [x] **T-04 Lookup functions** · FR-1–3 · design §5.1, §5.3
  - `lookup_program`, `lookup_deadlines`, `lookup_application` returning design §5.3 shapes.
  - Tests: single-match flat dict; multi-match `{"matches": [...]}`; not-found with
    `available_programs`; applicant ID case-insensitive (`app-1042`); unknown applicant.
  - Done when: AC-1.1–1.3, 2.1–2.3, 3.1 are covered by passing tests.

- [x] **T-05 LangChain tool wrappers** · FR-1–3 · design §5.1
  - `@tool` wrappers `get_program_info`, `check_application_status`, `get_deadlines`
    with guidance docstrings; `TOOLS` list.
  - Tests: tool names match the PDF; each schema has the right single string argument;
    `.invoke({...})` returns the same result as the lookup function.
  - Done when: wrapper tests pass.

## Phase C — Agent

- [x] **T-06 Config** · FR-11, NFR-4 · design §6, §11
  - `config.py`: `Settings` loaded from env/`.env`; `max_iterations` defaults to 5.
  - Tests: values read from env; missing `LLM_MODEL` or `OPENAI_API_KEY` raises a clear error.
  - Done when: config tests pass.

- [x] **T-07 Model factory and prompts** · FR-6, FR-8, FR-11 · design §6, §9
  - `llm.py`: `build_chat_model(settings)` → `ChatOpenAI(..., temperature=0)`.
  - `prompts.py`: `SYSTEM_PROMPT` (all design §9 rules) and `ESCALATION_MESSAGE` (exact PDF wording).
  - Tests: factory passes `base_url`/`model`/`api_key` through; the prompt contains the escalation text.
  - Done when: tests pass.

- [x] **T-08 Fake chat model fixture** · NFR-2 · design §12
  - `tests/conftest.py`: `FakeToolChatModel` (subclass of `GenericFakeChatModel` with a
    `bind_tools` that returns the model unchanged); helpers to script `AIMessage`s with `tool_calls`.
  - Done when: the fixture is used by T-09 tests.

- [x] **T-09 LangGraph agent graph** · FR-5, FR-7 · design §7
  - `graph.py`: `build_graph(model, tools, max_iterations, checkpointer)` with `agent` +
    `ToolNode` nodes, `tools_condition`, the system prompt added at call time, the iteration
    cap inside the `agent` node, and `InMemorySaver`.
  - Tests (fake model):
    - no tool call → direct answer
    - one tool call → tool runs → final answer
    - two tool calls in one AI message → both run (AC-5.3)
    - bad tool args → error `ToolMessage`, graph continues (AC-5.5)
    - the system prompt is sent to the model but not stored in state
    - an endless tool loop stops at the cap with `ESCALATION_MESSAGE` and the next turn still works (AC-5.4)
    - history persists across two invocations with the same `thread_id` (AC-7.1)
    - a different `thread_id` starts empty (AC-7.4)
  - Done when: graph tests pass.

- [x] **T-10 EnrollmentAgent facade** · FR-5, NFR-6 · design §8
  - `agent.py`: `ToolEvent`, `TurnResult`, `EnrollmentAgent.chat()`, `new_session()`.
  - Tests: `TurnResult.reply` and `tool_events` (name, args, result) come from this turn's
    messages only; sessions are isolated.
  - Done when: facade tests pass.

## Phase D — Interfaces and Demo

- [x] **T-11 CLI** · FR-9, NFR-3 · design §10
  - `cli.py`: REPL, one session per run, `exit`/`quit`, `--verbose` prints tool events,
    and LLM connection errors print a friendly message.
  - Done when: `uv run enrollment-agent --verbose` chats against LM Studio (manual check).

- [x] **T-12 Demo script** · FR-10 · design §10
  - `demo.py` (turns, runner, log renderer) + `scripts/run_demo.py` (`--env-file`, `--output`):
    runs the 5 turns in one session and writes a Markdown log
    (header: model, base URL, timestamp; per turn: input, tool calls + args + results, reply, latency).
  - Done when: the script produces a complete log against LM Studio (`docs/demo_log_lmstudio.md`).

- [x] **T-13 Live end-to-end test** · FR-6–8, FR-10 · design §12
  - `tests/test_demo_live.py` (`@pytest.mark.live`): the 5 per-turn behavioral assertions.
  - Done when: `uv run pytest -m live` passes against LM Studio. If the 4B model is flaky,
    record which turns fail and why before tuning the prompt.

- [ ] **T-14 Official demo log** · FR-10
  - Create `.env.openai` (git-ignored) with the OpenAI settings, then run
    `uv run python scripts/run_demo.py --env-file .env.openai` and commit `docs/demo_log.md`.
  - Done when: the log shows correct behavior for all 5 turns.

## Phase E — Documentation

- [x] **T-15 README**
  - Overview, setup (`uv sync`, `.env`), switching LM Studio ↔ OpenAI, running the CLI, demo
    and tests, project layout, and links to the specs and demo log.
  - Done when: a fresh clone can follow the README to run the demo.

---

# Phase 2 — Web Interfaces (FR-12, FR-13)

## Phase F — HTTP API

- [ ] **T-16 Web dependencies** · design §15.1
  - `uv add fastapi uvicorn streamlit httpx`; add the `enrollment-api = enrollment_agent.api:main`
    console script.
  - Done when: `uv sync` succeeds and the existing 80 tests still pass.

- [ ] **T-16b Async agent path** · D-9 · design §15.2
  - `graph.py`: the `agent` node supports sync and async (a `RunnableLambda` with `afunc`), with
    the iteration cap shared. `agent.py`: `EnrollmentAgent.achat()` sharing helpers with `chat()`.
  - Tests (async, `anyio`, fake model): reply + tool events, memory across turns, iteration cap.
  - Done when: new tests and all existing tests pass (sync behavior unchanged).

- [ ] **T-17 FastAPI app** · FR-12, NFR-7, NFR-8 · design §15.2
  - `api.py`: `create_app()`, the Pydantic schemas, async `POST /chat` (`await agent.achat`), `GET /health`, the error
    mapping, a lifespan that builds the agent from settings, module-level `app`, and `main()`
    with `--host/--port/--env-file`.
  - Tests (`test_api.py`, fake model):
    - response has `session_id`, `reply`, `tool_events` (AC-12.1)
    - no `session_id` → a new one is returned; reusing it keeps memory (AC-12.2, 12.3)
    - two sessions are isolated (AC-12.3)
    - empty or whitespace message → 422 (AC-12.4)
    - connection error → 503; other LLM error → 502, both with `detail` (AC-12.5)
    - `/health` returns status and model (AC-12.6)
  - Done when: tests pass, and `uv run enrollment-api` answers a `/chat` request against
    LM Studio (manual check with `curl` or `/docs`).

## Phase G — Chat UI

- [ ] **T-18 API client** · FR-13 · design §15.3
  - `api_client.py`: `ApiClient.chat()`, `ApiClient.health()`, `ApiError`.
  - Tests (`test_api_client.py`, `httpx.MockTransport`): request payloads (with and without
    `session_id`), JSON parsing, `ApiError` on connection error, timeout, and 4xx/5xx
    (message includes `detail`).
  - Done when: tests pass.

- [ ] **T-19 Streamlit chat UI** · FR-13 · design §15.4
  - `streamlit_app.py`: history, chat input, spinner, tool-call expander, sidebar with API
    status and **New conversation**, error display.
  - Tests (`test_streamlit_app.py`, `AppTest` + stub client):
    - a sent message shows the user and assistant messages (AC-13.1)
    - the second message sends the `session_id` from the first reply (AC-13.3)
    - a reply with tool events shows a "Tool calls" expander (AC-13.4)
    - **New conversation** clears the history and `session_id` (AC-13.5)
    - an `ApiError` shows an error message and no assistant reply (AC-13.6)
    - the sidebar shows the model when the API is up and an error when it is down (AC-13.7)
  - Done when: tests pass.

- [ ] **T-20 End-to-end check and docs** · FR-12, FR-13
  - Run LM Studio, `enrollment-api` and the Streamlit app together; play the 5-turn demo in
    the browser and confirm the tool panels and memory work.
  - README: add the web usage (start API, start UI, `API_URL`), and update the architecture
    diagram, layout and roadmap.
  - Done when: the demo works in the browser and the README steps reproduce it.

---

## Traceability

| Requirement | Tasks |
|---|---|
| FR-1–3 | T-03, T-04, T-05 |
| FR-4 | T-02 |
| FR-5 | T-09, T-10 |
| FR-6, FR-8 | T-07, T-13 |
| FR-7 | T-09, T-13 |
| FR-9 | T-11 |
| FR-10 | T-12, T-13, T-14 |
| FR-11 | T-06, T-07 |
| FR-12 | T-16, T-16b, T-17, T-20 |
| FR-13 | T-18, T-19, T-20 |
| NFR-1, NFR-4 | T-01, T-06 |
| NFR-2 | T-02–T-10 |
| NFR-3 | T-11, T-12 |
| NFR-5 | T-09 |
| NFR-6 | T-10, T-17 |
| NFR-7 | T-17 |
| NFR-8 | T-17, T-18, T-19 |
