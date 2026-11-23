# Build the locked Python environment with the PostgreSQL headers needed by psycopg 3.
FROM python:3.12-slim AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Keep the runtime small; psycopg dynamically loads the system libpq library.
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && /opt/venv/bin/python -c "from psycopg import pq; assert pq.version() > 0; print('libpq:', pq.version())" \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations

USER app
EXPOSE 8000

# Compose applies the migration before it starts Uvicorn. Keep the image's
# default command useful for running the API directly once the DB is migrated.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
