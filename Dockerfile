FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
RUN uv sync --frozen --no-dev

COPY app/ ./app/
COPY frontend/ ./frontend/

EXPOSE 8000

CMD uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
