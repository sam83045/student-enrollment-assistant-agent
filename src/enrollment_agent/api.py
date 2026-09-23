"""FastAPI HTTP API over the agent (FR-12, design §15.2).

Usage: uv run enrollment-api [--host 127.0.0.1] [--port 8000] [--env-file .env]
"""

import argparse
import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import openai
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, StringConstraints

from enrollment_agent.agent import EnrollmentAgent
from enrollment_agent.config import load_settings
from enrollment_agent.llm import build_chat_model

ENV_FILE_VAR = "ENROLLMENT_ENV_FILE"  # lets `main()` pass --env-file to the lifespan


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    session_id: str | None = None


class ToolEventOut(BaseModel):
    name: str
    args: dict
    result: str | None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_events: list[ToolEventOut]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model: str


def create_app(agent: EnrollmentAgent | None = None, model_name: str | None = None) -> FastAPI:
    """Build the app. Without ``agent``, one is built from settings at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.agent is None:
            settings = load_settings(os.getenv(ENV_FILE_VAR, ".env"))
            app.state.agent = EnrollmentAgent(build_chat_model(settings), settings.max_iterations)
            app.state.model_name = settings.model
        yield

    app = FastAPI(
        title="Student Enrollment Assistant API",
        description="Chat with the enrollment agent. Reuse `session_id` to keep context.",
        lifespan=lifespan,
    )
    app.state.agent = agent
    app.state.model_name = model_name or "unknown"

    @app.post("/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request) -> ChatResponse:
        agent: EnrollmentAgent = request.app.state.agent
        session_id = body.session_id or agent.new_session()
        try:
            result = await agent.achat(body.message, session_id)
        except openai.APIConnectionError:
            raise HTTPException(
                503,
                "The language model is unreachable. "
                "Check that LM Studio (or the configured endpoint) is running.",
            ) from None
        except openai.APIError as exc:
            raise HTTPException(502, f"The language model returned an error: {exc}") from None

        return ChatResponse(
            session_id=session_id,
            reply=result.reply,
            tool_events=[ToolEventOut(**vars(e)) for e in result.tool_events],
        )

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        return HealthResponse(status="ok", model=request.app.state.model_name)

    return app


app = create_app()


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Student Enrollment Assistant API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--env-file", default=".env", help="settings file (default: .env)")
    args = parser.parse_args(argv)

    os.environ[ENV_FILE_VAR] = args.env_file
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
