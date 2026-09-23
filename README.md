# Student Enrollment Assistant Agent

A conversational AI agent for a university admissions office. It answers prospective
students' questions about **programs**, **deadlines** and **application status** by calling
tools over mock data. It never answers those facts from the LLM's own knowledge. It keeps
context within a session, and it hands off to an enrollment counselor when a question is
outside what its tools cover.

Built with **LangGraph + LangChain** on **Python 3.12**, using spec-driven development.
It runs on the **OpenAI API** or a **local LLM** (LM Studio / Ollama) with no code changes.

- Case study brief: [assets/Agentic AI Case Study.pdf](assets/Agentic%20AI%20Case%20Study.pdf)
- Demo logs: [OpenAI](docs/demo_log.md) · [LM Studio, local](docs/demo_log_lmstudio.md)

## How it works

```
 user ─► CLI / demo script ─► EnrollmentAgent.chat(message, session_id)
                                     │
                     ┌───────────────▼────────────────┐
                     │  LangGraph StateGraph          │
                     │                                │
                     │  START ─► agent ─► END         │
                     │            ▲  │ tool calls     │
                     │            │  ▼                │
                     │           tools (ToolNode)     │
                     │                                │
                     │  memory: checkpointer / thread │
                     └───────┬───────────────┬────────┘
                             │               │
                  ChatOpenAI (any       get_program_info
                  OpenAI-compatible     get_deadlines
                  endpoint)             check_application_status ─► mock data
```

1. **Reason**: the `agent` node sends the conversation, the system prompt and the tool
   schemas to the LLM.
2. **Act**: if the LLM requests tool calls, the `tools` node runs them. Several calls in
   one step are supported.
3. **Observe**: tool results go back to the LLM, and the loop repeats until the LLM
   answers in plain text. The loop is capped at `AGENT_MAX_ITERATIONS` model calls per turn.
4. **Remember**: a LangGraph checkpointer keeps the full history for each session, so
   "that" and a previously given applicant ID are resolved without asking again.
5. **Escalate**: for questions the tools can't answer, the agent replies: *"I'd recommend
   speaking with an enrollment counselor for that. Would you like me to connect you?"*

### Tools

| Tool | Input | Returns |
|---|---|---|
| `get_program_info` | `program_name` | Program name, duration, tuition, prerequisites |
| `check_application_status` | `applicant_id` | Applicant name, program, status, next step, missing documents |
| `get_deadlines` | `program_name` | Application deadline, document deadline, decision date |

Program names match loosely: `"computer science"` returns both CS programs, and
`"all programs"` lists everything. Unknown names or IDs return a structured `not_found`
result instead of raising an error.

Mock data: 4 programs (B.S./M.S. Computer Science, MBA, B.S. Mechanical Engineering)
and 4 applicants (`APP-1042` … `APP-1045`). See [data.py](src/enrollment_agent/data.py).

## Setup

Requires [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if it is missing.

```powershell
uv sync
Copy-Item .env.example .env      # macOS/Linux: cp .env.example .env
```

### Choose an LLM provider

Any OpenAI-compatible endpoint works. Set it in `.env`:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` | `OPENAI_API_KEY` |
|---|---|---|---|
| LM Studio (default) | `http://localhost:1234/v1` | `qwen_qwen3.5-4b` | any value, e.g. `lm-studio` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | your key |
| Ollama | `http://localhost:11434/v1` | `qwen2.5-coder:7b` | any value, e.g. `ollama` |

The local model must support tool calling. `qwen_qwen3.5-4b` passes the full demo on a
4 GB GPU.

To keep several providers side by side, create extra files such as `.env.openai` and pass
`--env-file .env.openai`. Files named `.env.*` are git-ignored.

## Usage

**Chat in the terminal**

```powershell
uv run enrollment-agent            # add --verbose to see tool calls and results
```

Type `exit` or `quit` to end the session.

**Run the case-study demo and write a log**

```powershell
uv run python scripts/run_demo.py                                   # provider from .env → docs/demo_log.md
uv run python scripts/run_demo.py --env-file .env.openai            # OpenAI
uv run python scripts/run_demo.py --output docs/demo_log_lmstudio.md
```

**Tests**

```powershell
uv run pytest            # 80 offline tests with a fake model, no LLM or network needed
uv run pytest -m live    # 5 end-to-end checks of the demo against the configured LLM
```

## Demo conversation

| Turn | User | Agent behavior |
|---|---|---|
| 1 | Hi, what programs do you offer in computer science? | `get_program_info("computer science")`: lists B.S. and M.S. CS |
| 2 | What's the application deadline for that? | Resolves "that" from turn 1, then `get_deadlines` for both programs |
| 3 | I already applied. My ID is APP-1042. What's my status? | `check_application_status("APP-1042")`: Documents Pending |
| 4 | Can I get a fee waiver? | No tool; escalates to an enrollment counselor |
| 5 | What documents do I still need to submit? | Answers from session memory without asking for the ID again |

Full input/output logs, including every tool call and result:
[docs/demo_log.md](docs/demo_log.md) (OpenAI) and
[docs/demo_log_lmstudio.md](docs/demo_log_lmstudio.md) (local).

## Project layout

```
specs/                  requirements.md → design.md → tasks.md (spec-driven development)
src/enrollment_agent/
  data.py               mock programs, deadlines, applicants
  tools.py              lookup functions + LangChain @tool wrappers
  prompts.py            system prompt and escalation message
  graph.py              LangGraph StateGraph (agent + ToolNode, memory, iteration cap)
  agent.py              EnrollmentAgent facade, UI-independent
  llm.py, config.py     ChatOpenAI factory, .env settings
  cli.py                terminal chat
  demo.py               demo turns, runner, Markdown log
scripts/run_demo.py     demo entry point
tests/                  unit, graph, CLI and live tests
docs/                   generated demo logs
```

## Development process

The project follows spec-driven development. Each stage was reviewed before the next began:

1. [Requirements](specs/requirements.md): functional requirements with numbered acceptance criteria.
2. [Design](specs/design.md): architecture, tool contracts, graph, memory, decisions.
3. [Tasks](specs/tasks.md): test-first tasks, each traced back to its requirements.

Tests are written from the acceptance criteria before the implementation.

## Roadmap

- Streamlit chat UI and FastAPI endpoint (FR-12). Both will reuse `EnrollmentAgent` unchanged.
- Persistent sessions via a SQLite checkpointer.
