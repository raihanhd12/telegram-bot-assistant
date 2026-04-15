FROM dhi.io/python:3.12-dev AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.3.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV=/app/venv \
    PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv "$VIRTUAL_ENV"
RUN pip install --upgrade pip \
    && pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml ./

RUN poetry install --only main --no-root \
    && pip uninstall -y poetry pip

FROM dhi.io/python:3.12 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/venv \
    PATH="/app/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY . .

USER nonroot

# Run migrations and start the bot
CMD ["python", "-c", "import subprocess; subprocess.check_call(['alembic', 'upgrade', 'head']); import main; main.main()"]
