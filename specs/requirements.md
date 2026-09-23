# Requirements — Student Enrollment Assistant Agent

Source: [assets/Agentic AI Case Study.pdf](../assets/Agentic%20AI%20Case%20Study.pdf)
Status: **Approved**: Phase 1 (FR-1..11) and Phase 2 (FR-12..13), 2026-09-23

## 1. Overview

A conversational AI agent for a university admissions office. It answers prospective
students' questions about programs, deadlines, and application status. Every factual
answer must come from a tool call over mock data — never from the LLM's own knowledge.
Questions outside the tools' scope are escalated to an enrollment counselor.

## 2. Scope

**In scope**
- Three tools backed by hardcoded mock data.
- An LLM-driven agent loop with tool calling.
- Multi-turn session memory.
- Graceful escalation for unsupported questions.
- A CLI chat and a scripted run of the 5-turn demo conversation with a full log.
- Switchable LLM provider (OpenAI API or a local OpenAI-compatible LLM).
- Phase 2: a FastAPI HTTP API and a Streamlit chat UI (FR-12, FR-13).

**Out of scope**
- Real databases, authentication, or persistence across sessions or server restarts.
- Actually connecting the user to a counselor (the agent only offers to).
- Streaming replies, containers, and switching the LLM provider from the UI.

## 3. Functional Requirements

### Tools

**FR-1 `get_program_info(program_name: str)`**
Returns a dict with `program_name`, `duration`, `tuition`, `prerequisites`.
- AC-1.1 An exact program name (case-insensitive) returns that program's details.
- AC-1.2 A partial/keyword name (e.g. `"computer science"`) returns all matching programs.
- AC-1.3 An unknown program returns a structured "not found" result (no exception)
  that includes the list of available program names.

**FR-2 `check_application_status(applicant_id: str)`**
Returns a dict with `applicant_name`, `program`, `status`, `next_step`, and
`missing_documents` (list; empty if none).
- AC-2.1 A known ID (case-insensitive, e.g. `app-1042`) returns that applicant's record.
- AC-2.2 `status` is one of: `Under Review`, `Accepted`, `Documents Pending`, `Rejected`.
- AC-2.3 An unknown ID returns a structured "not found" result (no exception).
- *Note: `missing_documents` extends the PDF's return spec so Turn 5 can be answered from a tool.*

**FR-3 `get_deadlines(program_name: str)`**
Returns a dict with `program_name`, `application_deadline`,
`document_submission_deadline`, `decision_notification_date` (ISO dates).
- AC-3.1 Same name-matching rules as FR-1 (exact, partial, not found).

**FR-4 Mock data**
- AC-4.1 At least 3 programs, including at least one Computer Science program.
- AC-4.2 At least 3 applicants, including `APP-1042` with status `Documents Pending`
  and a non-empty `missing_documents` list.
- AC-4.3 Every program has deadline data; every applicant references an existing program.

### Agent

**FR-5 Agent loop**
- AC-5.1 On each user message, the agent sends the conversation plus tool schemas to the LLM.
- AC-5.2 If the LLM requests tool calls, the agent executes them and returns results to the LLM;
  this repeats until the LLM produces a final text answer.
- AC-5.3 The loop supports multiple tool calls in one turn (parallel or sequential).
- AC-5.4 The loop is bounded (max iterations per turn) to prevent runaway calls.
- AC-5.5 Tool errors or invalid arguments are returned to the LLM as error results, not crashes.

**FR-6 Grounding**
- AC-6.1 Program details, deadlines, and application data in answers come only from tool results.
- AC-6.2 If a tool returns "not found", the agent says so and does not invent data.

**FR-7 Multi-turn memory**
- AC-7.1 The full conversation (user, assistant, tool calls, tool results) is kept for the session.
- AC-7.2 The agent resolves references to earlier turns (e.g. "that" → program from a prior turn).
- AC-7.3 Once an applicant ID is provided, the agent does not ask for it again in the session.
- AC-7.4 A new session starts with empty memory.

**FR-8 Escalation**
- AC-8.1 Questions the tools cannot answer (e.g. fee waivers, financial aid, visas) get a response
  equivalent to: *"I'd recommend speaking with an enrollment counselor for that. Would you
  like me to connect you?"*
- AC-8.2 The agent does not answer such questions from general LLM knowledge.

### Interfaces

**FR-9 CLI chat** — interactive single-session chat in the terminal; `exit`/`quit` ends it.

**FR-10 Demo run**
- AC-10.1 A script runs the 5-turn conversation below in one session.
- AC-10.2 It writes a log to `docs/demo_log.md` containing, per turn: user input, each tool call
  (name + arguments), each tool result, and the agent's final response.

| Turn | User input | Expected behavior |
|---|---|---|
| 1 | "Hi, what programs do you offer in computer science?" | Calls `get_program_info`; lists CS program(s) with details. |
| 2 | "What's the application deadline for that?" | Resolves "that" from Turn 1; calls `get_deadlines`. |
| 3 | "I already applied. My ID is APP-1042. What's my status?" | Calls `check_application_status("APP-1042")`; reports status and next step. |
| 4 | "Can I get a fee waiver?" | No tool call; escalates to a counselor. |
| 5 | "What documents do I still need to submit?" | Uses APP-1042 without asking again; lists missing documents. |

**FR-11 LLM provider configuration**
- AC-11.1 Provider is set via environment: `LLM_BASE_URL`, `LLM_MODEL`, `OPENAI_API_KEY`.
- AC-11.2 Works with the OpenAI API and with local OpenAI-compatible servers (e.g. Ollama)
  without code changes.

### Web interfaces (Phase 2)

**FR-12 HTTP API (FastAPI)**: the only backend that runs the agent.
- AC-12.1 `POST /chat` with `{message, session_id?}` returns `{session_id, reply, tool_events}`,
  where each tool event has `name`, `args` and `result`.
- AC-12.2 A request without `session_id` starts a new session and returns its ID.
- AC-12.3 Requests with the same `session_id` share memory; different IDs are isolated.
- AC-12.4 An empty or whitespace-only message is rejected with HTTP 422.
- AC-12.5 If the LLM is unreachable the API returns HTTP 503; other LLM errors return 502.
  Both carry a readable `detail` message.
- AC-12.6 `GET /health` returns `{status: "ok", model}`.
- AC-12.7 The API reuses `EnrollmentAgent` unchanged (NFR-6).

**FR-13 Chat UI (Streamlit)**: a thin client of the FR-12 API.
- AC-13.1 A chat page shows the conversation for the current browser session.
- AC-13.2 The UI talks to the agent only through the API; the API address comes from the
  `API_URL` environment variable (default `http://localhost:8000`).
- AC-13.3 The UI keeps the `session_id` from the first reply and sends it with every later
  message, so the agent remembers context.
- AC-13.4 Each assistant reply that used tools has a collapsible "Tool calls" panel listing
  each tool's name, arguments and result.
- AC-13.5 A "New conversation" button clears the chat and starts a new session.
- AC-13.6 If the API is down or returns an error, the UI shows a readable message instead of
  crashing, and the user can retry.
- AC-13.7 The sidebar shows whether the API is reachable and which model it uses.

## 4. Non-Functional Requirements

- **NFR-1 Stack:** Python 3.12 (`requires-python >= 3.11`), managed with **uv**.
- **NFR-2 Testability:** Tools are pure functions testable without an LLM; the agent graph is
  testable with a fake chat model.
- **NFR-3 Observability:** Tool calls and results are logged (debug level in CLI, always in demo log).
- **NFR-4 Secrets:** API keys come from `.env` / environment only; `.env` is git-ignored.
- **NFR-5 Agent framework:** LangChain (models, tools) and LangGraph (agent loop, memory).
  The graph is built explicitly (not a one-line prebuilt agent) so the loop stays visible.
- **NFR-6 UI independence:** The agent is independent of any interface, so CLI, Streamlit and
  FastAPI can all use it.
- **NFR-7 Web sessions:** Session memory lives in the API process (in-memory checkpointer)
  and is lost when the API restarts. Concurrent sessions must not interfere with each other.
- **NFR-8 Web testability:** The API is tested with a fake model (no LLM); the UI's HTTP
  client is tested without a running server.

## 5. Assumptions & Open Decisions

| # | Item | Default chosen | Change? |
|---|---|---|---|
| A-1 | Interface | CLI first; FastAPI + Streamlit in Phase 2 | |
| A-2 | Spec format | Plain Markdown (`requirements` → `design` → `tasks`) | |
| A-3 | `missing_documents` field | Added to FR-2 | |
| A-4 | Ambiguous "that" when several CS programs match | Agent answers for all matches | Or: ask which one |
| A-5 | Escalation | Offer only; no real hand-off | |
| A-6 | Web architecture | Streamlit → HTTP → FastAPI → agent (confirmed 2026-09-23) | |
| A-7 | Web session persistence | In-memory only (confirmed) | SQLite checkpointer later |
| A-8 | Web extras | Tool-call panel only (confirmed); no streaming, Docker or provider switch | |
