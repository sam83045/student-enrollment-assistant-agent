# Design — Student Enrollment Assistant Agent

Implements: [requirements.md](requirements.md)
Status: **Approved**: Phase 1 (§1–14) and Phase 2 (§15), 2026-09-23

## 1. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 (`requires-python >= 3.11`) |
| Packaging / env | uv (`pyproject.toml` + `uv.lock`) |
| LLM access | `langchain-openai` `ChatOpenAI` with configurable `base_url` (OpenAI API or local OpenAI-compatible server) |
| Tools | `langchain-core` `@tool` |
| Agent loop + memory | `langgraph` `StateGraph` + `ToolNode` + in-memory checkpointer |
| Config | `python-dotenv` |
| Tests | `pytest` |
| Interface — phase 1 | CLI |
| Interface — phase 2 | FastAPI + uvicorn (HTTP API), Streamlit (chat UI) calling the API via httpx (§15) |

Exact versions are pinned in `uv.lock` when the project is set up.

## 2. Architecture

```
 ┌───────────────────────────── interfaces ─────────────────────────────┐
 │  cli.py (phase 1)   run_demo.py   [streamlit_app.py]  [api.py]  (later)│
 └───────────────┬──────────────────────────────────────────────────────┘
                 │ chat(message, session_id) -> TurnResult
        ┌────────▼─────────┐
        │ EnrollmentAgent  │  agent.py — facade, UI-independent (NFR-6)
        └────────┬─────────┘
                 │ graph.invoke(..., thread_id=session_id)
   ┌─────────────▼──────────────────────────────┐
   │ LangGraph StateGraph (graph.py)            │
   │                                            │
   │  START ─► [agent] ──tools_condition──► END │
   │             ▲  │                           │
   │             │  ▼ (tool calls)              │
   │           [tools]  ToolNode                │
   │                                            │
   │  checkpointer: InMemorySaver  (memory)     │
   └──────┬─────────────────────────┬───────────┘
          │                         │
   ChatOpenAI.bind_tools()     tools.py ─► data.py
   (llm.py)                    (@tool, mock data)
```

## 3. Project Layout

```
src/enrollment_agent/
  __init__.py
  config.py        # load .env → Settings
  data.py          # mock PROGRAMS, DEADLINES, APPLICANTS
  tools.py         # pure lookup functions + LangChain @tool wrappers (TOOLS list)
  llm.py           # build_chat_model(settings) -> ChatOpenAI
  prompts.py       # SYSTEM_PROMPT, ESCALATION_MESSAGE
  graph.py         # build_graph(model, tools, checkpointer) -> compiled StateGraph
  agent.py         # EnrollmentAgent facade, TurnResult, ToolEvent
  cli.py           # interactive chat (FR-9)
  demo.py          # DEMO_TURNS, run_demo(), render_log(): shared by script and live test
scripts/
  run_demo.py      # 5-turn demo → docs/demo_log.md (FR-10); --env-file, --output
tests/
  conftest.py      # FakeToolChatModel fixture
  test_data.py     # FR-4 mock data integrity
  test_tools.py    # FR-1..3 matching, lookups, tool wrappers (no LLM)
  test_agent.py    # FR-5..8 with fake model
  test_demo_live.py# FR-10 against a real LLM, marked @pytest.mark.live
docs/demo_log.md   # generated
.env.example  .gitignore  pyproject.toml  uv.lock  README.md
```

Dependencies: `langchain-core`, `langchain-openai`, `langgraph`, `python-dotenv`.
Dev: `pytest`. Later phase: `streamlit`, `fastapi`, `uvicorn`.

## 4. Mock Data (`data.py`) — FR-4

Programs are keyed by a canonical ID. Two CS programs exercise multi-match (A-4).

| id | program_name | duration | tuition | prerequisites |
|---|---|---|---|---|
| `bs-cs` | B.S. Computer Science | 4 years | $38,000 / year | High school diploma; Math through Pre-Calculus; SAT/ACT optional |
| `ms-cs` | M.S. Computer Science | 2 years | $45,000 / year | Bachelor's in CS or related field; Data Structures & Algorithms; GPA ≥ 3.0 |
| `mba` | Master of Business Administration | 2 years | $52,000 / year | Bachelor's degree; 2+ years work experience; GMAT/GRE |
| `bs-me` | B.S. Mechanical Engineering | 4 years | $40,000 / year | High school diploma; Physics; Calculus |

Each program also has `aliases` for matching (e.g. `["cs", "computer science", "bscs"]`).

Deadlines (ISO dates) exist for every program id.

| id | application_deadline | document_submission_deadline | decision_notification_date |
|---|---|---|---|
| `bs-cs` | 2027-01-15 | 2027-02-01 | 2027-03-31 |
| `ms-cs` | 2027-02-01 | 2027-02-15 | 2027-04-15 |
| `mba` | 2027-03-01 | 2027-03-15 | 2027-05-01 |
| `bs-me` | 2027-01-15 | 2027-02-01 | 2027-03-31 |

Applicants:

| applicant_id | applicant_name | program | status | next_step | missing_documents |
|---|---|---|---|---|---|
| `APP-1042` | Jordan Lee | `ms-cs` | Documents Pending | Submit missing documents by 2027-02-15 | Official transcripts; Two letters of recommendation |
| `APP-1043` | Priya Sharma | `bs-cs` | Under Review | Await decision by 2027-03-31 | — |
| `APP-1044` | Marcus Chen | `mba` | Accepted | Pay enrollment deposit by 2027-05-15 | — |
| `APP-1045` | Aisha Okafor | `bs-me` | Rejected | Contact admissions for feedback | — |

## 5. Tools (`tools.py`) — FR-1..3

### 5.1 Two layers

- **Plain functions** hold the lookup logic: `lookup_program`, `lookup_deadlines`,
  `lookup_application`. They take and return plain Python values and are unit-tested
  directly (NFR-2).
- **LangChain tools** wrap them: `get_program_info`, `check_application_status` and
  `get_deadlines` are decorated with `@tool`. The name, type hints and docstring become the
  schema the LLM sees, so docstrings are written as usage guidance. For example:
  *"Look up one or more university programs by name or subject keyword (e.g. 'computer
  science'). Returns duration, tuition and prerequisites."*
- `TOOLS = [get_program_info, check_application_status, get_deadlines]`.

### 5.2 Program name matching (shared by FR-1, FR-3)

1. Normalize: lowercase, strip punctuation, collapse whitespace.
2. Remove filler tokens: `program(s)`, `degree(s)`, `in`, `of`, `the`, `a`, `an`, `all`.
3. **Nothing left** (e.g. `"programs"`, `"all"`) → all programs.
4. **Exact** match on normalized `program_name` or any alias → those programs.
5. Otherwise **keyword** match: every remaining query token appears in the name or an alias
   → all such programs.
6. No matches → not found.

`"computer science"` → `bs-cs`, `ms-cs`. `"M.S. Computer Science"` → `ms-cs`.
`"all programs"` → all four.

### 5.3 Return shapes

Shapes stay flat and match the PDF for the common single-match case.

```jsonc
// single match — get_program_info
{"program_name": "M.S. Computer Science", "duration": "2 years",
 "tuition": "$45,000 / year", "prerequisites": ["...", "..."]}

// multiple matches — either program tool
{"matches": [ {<single-match dict>}, ... ]}

// get_deadlines single match
{"program_name": "...", "application_deadline": "2027-02-01",
 "document_submission_deadline": "2027-02-15", "decision_notification_date": "2027-04-15"}

// check_application_status
{"applicant_id": "APP-1042", "applicant_name": "Jordan Lee",
 "program": "M.S. Computer Science", "status": "Documents Pending",
 "next_step": "...", "missing_documents": ["Official transcripts", "..."]}

// not found (any tool)
{"error": "not_found", "message": "No program matches 'art history'.",
 "available_programs": ["B.S. Computer Science", ...]}   // programs only
```

Applicant IDs are normalized with `strip().upper()` (AC-2.1).

### 5.4 Tool errors (AC-5.5)

"Not found" is a normal return value, not an exception. Bad arguments and unexpected
exceptions are caught by `ToolNode` (`handle_tool_errors=True`) and sent back to the LLM
as a `ToolMessage` error, so the graph never crashes on a tool failure.

## 6. LLM (`llm.py`) — FR-11

```python
def build_chat_model(settings: Settings) -> BaseChatModel:
    return ChatOpenAI(model=settings.model, base_url=settings.base_url,
                      api_key=settings.api_key, temperature=0)
```

`ChatOpenAI` serves both the OpenAI API and local servers (Ollama, LM Studio), because both
speak the OpenAI Chat Completions protocol. Switching providers only changes `.env`:

```env
# Local development (default): LM Studio
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen_qwen3.5-4b
OPENAI_API_KEY=lm-studio                  # any non-empty value for local

# OpenAI API (official demo log)
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini
# OPENAI_API_KEY=sk-...

AGENT_MAX_ITERATIONS=5
```

**Local runtime (verified 2026-09-23):** LM Studio at `localhost:1234`, model `qwen_qwen3.5-4b`.
It is trained for tool use, is 2.9 GB loaded, and fits the 4 GB RTX 3050 Ti. A smoke test
returned a correct `get_deadlines` tool call in about 6 s. Ollama is also installed at
`localhost:11434` as a fallback.

The rest of the code depends only on `BaseChatModel`, so tests can pass in a fake model.

## 7. Agent Graph (`graph.py`) — FR-5, FR-7

### 7.1 State

`MessagesState`: a `messages` list with the `add_messages` reducer. It holds user, AI
(including tool calls) and tool-result messages.

### 7.2 Nodes and edges

| Element | Implementation |
|---|---|
| `agent` node | `model.bind_tools(TOOLS).invoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])` → returns the AI message |
| `tools` node | `ToolNode(TOOLS)`: runs every tool call in the last AI message (AC-5.3) |
| `START → agent` | fixed edge |
| `agent → tools / END` | `tools_condition`: go to `tools` if the AI message has tool calls, else `END` |
| `tools → agent` | fixed edge, so the model reads the tool results and answers |

The system prompt is added on every model call rather than stored in state. The saved
history stays clean, and a prompt change applies to existing sessions.

### 7.3 Graph shape

The graph is built explicitly with `StateGraph`, not with a one-line prebuilt agent. It is
about 15 lines, and it shows the reason → act → observe loop clearly (NFR-5).

### 7.4 Memory (FR-7)

- Compiled with `checkpointer=InMemorySaver()`.
- Each session is a LangGraph thread: `config={"configurable": {"thread_id": session_id}}`.
- Each turn passes only the new user message; the checkpointer restores the earlier
  messages, including tool results. The LLM therefore resolves "that" (Turn 2) and
  APP-1042 (Turn 5) from history (AC-7.1–7.3).
- A new `session_id` starts with empty memory (AC-7.4).
- Later phase: replace it with `SqliteSaver` for persistence if the web UI needs it.
  Nothing else changes.

### 7.5 Iteration cap (AC-5.4)

The `agent` node counts the AI messages since the last user message. When the count
reaches `max_iterations`, the node returns `AIMessage(ESCALATION_MESSAGE)` without calling
the model, and `tools_condition` routes to `END`.

This keeps the saved history valid. Stopping the graph with `recursion_limit` instead would
leave AI tool calls without tool results, and OpenAI-compatible APIs reject that history on
the next turn. `recursion_limit` is still set (`2 * max_iterations + 5`) as a safety net only.

## 8. Agent Facade (`agent.py`) — NFR-6

```python
@dataclass
class ToolEvent:   name: str; args: dict; result: str

@dataclass
class TurnResult:  reply: str; tool_events: list[ToolEvent]

class EnrollmentAgent:
    def __init__(self, model: BaseChatModel, max_iterations: int = 5,
                 checkpointer: BaseCheckpointSaver | None = None): ...
    def chat(self, message: str, session_id: str) -> TurnResult: ...
    def new_session(self) -> str: ...         # returns a fresh uuid
```

`chat` invokes the graph and then takes the messages added during this turn:
- `AIMessage.tool_calls` paired with the matching `ToolMessage` results become `ToolEvent`s.
- The final `AIMessage.content` becomes `reply`.

Every interface (CLI, demo, Streamlit, FastAPI) uses only this class.

## 9. Prompt: Grounding and Escalation (`prompts.py`) — FR-6, FR-8

The system prompt tells the model to:
- Answer only from tool results; never use general knowledge for university facts.
- Call a tool whenever the question involves programs, deadlines, or application status.
- Reuse identifiers (program, applicant ID) already given in the conversation; never re-ask.
- When several programs match, answer for all of them (A-4).
- If a tool returns `not_found`, say so and offer the available options.
- For anything the tools can't answer (fee waivers, financial aid, scholarships, visas,
  housing, transfer credits, …), reply with `ESCALATION_MESSAGE`:
  *"I'd recommend speaking with an enrollment counselor for that. Would you like me to connect you?"*
- Be concise and friendly.

## 10. Interfaces

**CLI (`cli.py`, FR-9, phase 1)**: `uv run enrollment-agent [--verbose]` (a console script).
A REPL with one session per run; `exit`/`quit` ends it. `--verbose` prints tool calls and
results (NFR-3).

**Demo (`scripts/run_demo.py`, FR-10)**: `uv run python scripts/run_demo.py`. Runs the
5 turns in one session and writes `docs/demo_log.md`. Each turn gets a section with the
user input, each tool call (name, arguments, result), the agent reply and the latency. The
header records the model, base URL and timestamp.

Options:
- `--env-file` selects the provider without editing `.env`, e.g. `.env.openai`. Files named
  `.env.*` are git-ignored, except `.env.example`.
- `--output` sets the log path. Logs are kept for both providers: `docs/demo_log.md` (OpenAI,
  official) and `docs/demo_log_lmstudio.md` (local).

**Phase 2 (FR-12, FR-13)**: FastAPI API and Streamlit UI; see §15.

## 11. Error Handling

| Failure | Behavior |
|---|---|
| Tool "not found" | Normal result; LLM explains and offers options |
| Bad tool args / tool exception | `ToolNode` returns an error `ToolMessage` to the LLM |
| Iteration cap reached | `agent` node returns `ESCALATION_MESSAGE`; history stays valid |
| LLM API error (network, auth, model missing) | Raised to caller; CLI prints a clear message and continues |
| Missing `LLM_MODEL` / `OPENAI_API_KEY` | `config.py` fails fast with an actionable message |

## 12. Testing Strategy

| Layer | File | LLM | Covers |
|---|---|---|---|
| Tools | `test_tools.py` | none | AC-1.x–4.x: matching, not-found, case handling, data integrity |
| Agent graph | `test_agent.py` | fake model with scripted `AIMessage`s (incl. `tool_calls`) | AC-5.x: single/multi tool calls, cap, bad args; AC-7.x: history kept per thread, new session empty |
| End-to-end | `test_demo_live.py` | real (skipped unless `-m live`) | FR-10 per-turn expectations |

**Fake model**: `langchain_core`'s `GenericFakeChatModel` can't bind tools, so the test
suite subclasses it with a `bind_tools` that returns the model unchanged. The fake returns
scripted `AIMessage`s in order.

**Live demo assertions** (behavior only; live output is not deterministic):
1. `get_program_info` called; reply mentions "Computer Science".
2. `get_deadlines` called for CS program(s); reply contains a deadline date.
3. `check_application_status` called with `APP-1042`; reply mentions "Documents Pending".
4. No tool calls; reply mentions "counselor".
5. Reply lists a missing document; it does not ask for the applicant ID.

## 13. Traceability

| Requirement | Design section | Tests |
|---|---|---|
| FR-1..3 | 5 | test_tools |
| FR-4 | 4 | test_tools |
| FR-5 | 7.2, 7.5 | test_agent |
| FR-6, FR-8 | 9 | test_demo_live |
| FR-7 | 7.4 | test_agent, test_demo_live |
| FR-9, FR-10 | 10 | manual, test_demo_live |
| FR-11 | 6 | manual (run against both providers) |
| FR-12 | 15.2 | test_api |
| FR-13 | 15.3, 15.4 | test_api_client, test_streamlit_app, manual |

## 14. Design Decisions

All decisions approved 2026-09-23 as listed (first column chosen).

| # | Decision | Alternative (not chosen) |
|---|---|---|
| D-1 | Single match returns a flat dict (PDF format); multiple return `{"matches": [...]}` | Always return a list |
| D-2 | Memory = LangGraph checkpointer (full message history per thread) | Also extract facts (applicant ID) into custom state |
| D-3 | Escalation decided by the LLM via system prompt | Add a rule-based pre-filter node |
| D-4 | Iteration cap exceeded → escalation message | Return an error message |
| D-5 | `temperature=0` for more repeatable demos | Model default |
| D-6 | Explicit `StateGraph` (agent + ToolNode) | Prebuilt agent helper (fewer lines, loop hidden) |
| D-7 | `ChatOpenAI` + `base_url` for local LLM too (LM Studio default) | Native `ChatOllama` / LM Studio SDK (a second code path) |
| D-8 | LangSmith tracing off by default; enabled via env vars if wanted | Always on |

## 15. Web Interfaces (Phase 2) — FR-12, FR-13

### 15.1 Components

```
 browser ──► Streamlit app ──► ApiClient ──HTTP──► FastAPI app ──► EnrollmentAgent ──► LLM
             streamlit_app.py  api_client.py       api.py          (one instance,
             :8501             (httpx)             :8000            InMemorySaver)
```

- The FastAPI process owns the only `EnrollmentAgent`, so all session memory lives there
  (NFR-7). Restarting the API clears every session.
- Streamlit never imports the agent. It only knows the API address (`API_URL`).
- `EnrollmentAgent`, the graph and the tools are unchanged (AC-12.7).

New files:

```
src/enrollment_agent/
  api.py             # create_app(), app, main() → `enrollment-api` console script
  api_client.py      # ApiClient, ApiError (used by the UI)
  streamlit_app.py   # chat UI
tests/
  test_api.py        # FastAPI TestClient + fake model
  test_api_client.py # httpx.MockTransport, no server
  test_streamlit_app.py  # streamlit AppTest with a stub client
```

New dependencies: `fastapi`, `uvicorn`, `streamlit`, `httpx` (already installed through
`openai`, now declared explicitly).

### 15.2 HTTP API (`api.py`) — FR-12

**App factory**: `create_app(agent: EnrollmentAgent | None = None, model_name: str | None = None)`.
- Tests pass an agent built on the fake model.
- With no agent, a lifespan handler calls `load_settings()` at startup and builds the agent
  from it. A `ConfigError` stops startup with its message.
- The agent and model name are stored on `app.state`.
- Module-level `app = create_app()` lets `uvicorn enrollment_agent.api:app` work too.

**Schemas** (Pydantic):

```python
class ChatRequest(BaseModel):
    message: str          # stripped; must be non-empty (AC-12.4 → 422)
    session_id: str | None = None

class ToolEventOut(BaseModel):
    name: str; args: dict; result: str | None

class ChatResponse(BaseModel):
    session_id: str; reply: str; tool_events: list[ToolEventOut]

class HealthResponse(BaseModel):
    status: Literal["ok"]; model: str
```

**Endpoints**:

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/chat` | `session_id = request.session_id or agent.new_session()`, then `agent.chat(...)`, returns `ChatResponse` |
| `GET` | `/health` | `{"status": "ok", "model": <model name>}` |
| `GET` | `/docs` | FastAPI's built-in interactive docs |

**Error mapping (AC-12.5)**:

| Exception | HTTP | `detail` |
|---|---|---|
| Empty message (validation) | 422 | FastAPI validation error |
| `openai.APIConnectionError` | 503 | "The language model is unreachable. Check that LM Studio (or the configured endpoint) is running." |
| other `openai.APIError` | 502 | "The language model returned an error: …" |

**Concurrency (D-9)**: the endpoints are `async def` and `await agent.achat(...)`, so a slow
LLM call doesn't block the event loop or tie up a thread. Different sessions run
concurrently. Two requests on the *same* session at the same time are not supported; the
UI sends one message at a time.

**Async agent path**: this is the only change to the Phase 1 code, and it keeps the sync
behavior.
- `graph.py`: the `agent` node is a `RunnableLambda` with both a sync function (`model.invoke`)
  and an async one (`await model.ainvoke`). They share the iteration-cap logic. `ToolNode`
  and `InMemorySaver` already support async.
- `agent.py`: `EnrollmentAgent.achat(message, session_id)` mirrors `chat()` using
  `graph.aget_state` / `graph.ainvoke`. The two share the config and result-extraction helpers.
- The CLI and demo keep using `chat()`.

**Session IDs**: the server creates them (`uuid4().hex`). An unknown `session_id` from a
client simply starts an empty conversation under that ID; the API never returns 404 for it.

**Running**: `uv run enrollment-api [--host 127.0.0.1] [--port 8000] [--env-file .env]`
starts uvicorn with the app.

### 15.3 API client (`api_client.py`) — FR-13

```python
class ApiError(Exception): ...      # message is safe to show to the user

class ApiClient:
    def __init__(self, base_url: str, timeout: float = 180.0,
                 transport: httpx.BaseTransport | None = None): ...
    def chat(self, message: str, session_id: str | None) -> dict   # ChatResponse JSON
    def health(self) -> dict                                       # HealthResponse JSON
```

- The 180 s timeout covers slow local models; a turn on LM Studio takes up to about 13 s.
- Connection failures, timeouts and non-2xx responses all raise `ApiError`. For non-2xx
  responses the message includes the API's `detail` (AC-13.6).
- `transport` lets tests use `httpx.MockTransport` instead of a real server.

### 15.4 Streamlit app (`streamlit_app.py`) — FR-13

**State** (`st.session_state`):
- `session_id`: `None` until the first reply, then the value returned by the API (AC-13.3).
- `messages`: a list of `{"role": "user" | "assistant", "content": str, "tool_events": list}`.

**Layout**:
- **Sidebar**: the API status from `health()`, showing "Connected · model `…`" or an error
  (AC-13.7); a **New conversation** button that clears `messages` and `session_id` (AC-13.5).
- **Main**: title and a short caption, then the history rendered with `st.chat_message`, then
  `st.chat_input("Ask about programs, deadlines or your application…")`.
- **Tool panel (AC-13.4)**: under each assistant message with tool events, an
  `st.expander("Tool calls (n)")`. For each event it shows the tool name, the arguments
  (`st.json`) and the result (`st.json` when it parses, otherwise text).

**Send flow**:
1. Append and show the user message.
2. Show `st.spinner("Thinking…")` while calling `client.chat(message, session_id)`.
3. On success, store the `session_id` and append and show the assistant message.
4. On `ApiError`, show `st.error(message)`. The user message stays in the history so the user
   can retry, but no assistant message is added (AC-13.6).

**Client construction**: `api_client.client_from_env()` builds
`ApiClient(os.getenv("API_URL", "http://localhost:8000"))`. The app stores the client in
`st.session_state`, one per browser session. Tests replace `client_from_env` with a stub.

**Running**: `uv run streamlit run src/enrollment_agent/streamlit_app.py` (port 8501).

### 15.5 Testing

| File | How | Covers |
|---|---|---|
| `test_agent.py` (extended) | `anyio` async tests, fake model | `achat` matches `chat`: reply, tool events, memory, iteration cap |
| `test_api.py` | `TestClient(create_app(agent_with_fake_model, "fake-model"))` | AC-12.1–12.6: response shape, new vs. reused session, memory, isolation, 422, 503/502 mapping, health |
| `test_api_client.py` | `httpx.MockTransport` | request payloads, success parsing, `ApiError` on connection error / timeout / 4xx–5xx with `detail` |
| `test_streamlit_app.py` | `streamlit.testing.v1.AppTest` with a stub client | AC-13.1, 13.3–13.7: chat renders, session ID reused, tool panel shown, new conversation resets, error shown |
| Manual | LM Studio + both servers | full 5-turn demo through the browser |

### 15.6 Phase 2 decisions

All approved 2026-09-23. D-9 was changed from the proposed sync endpoints to async.

| # | Decision | Alternative (not chosen) |
|---|---|---|
| D-9 | `async def` endpoints + `EnrollmentAgent.achat` (async graph path) | Sync endpoints in the thread pool |
| D-10 | Server-generated session IDs; unknown IDs start an empty conversation | Track issued IDs and return 404 for unknown ones |
| D-11 | Web dependencies as regular project dependencies | Optional `web` extra (`uv sync --extra web`) |
| D-12 | UI logic tested with `AppTest` and a stub client | Manual UI testing only |
