# syntax=docker/dockerfile:1
# One image for both services (FR-14, design §16.2):
#   api: enrollment-api (default CMD)
#   ui:  streamlit run src/enrollment_agent/streamlit_app.py

# --- builder: install locked dependencies with uv ---------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, so this layer is cached until uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock .python-version README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- runtime: slim Python with the prebuilt virtualenv ----------------------
FROM python:3.12-slim-bookworm

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000 8501

CMD ["enrollment-api", "--host", "0.0.0.0", "--port", "8000"]
