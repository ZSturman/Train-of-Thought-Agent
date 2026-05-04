# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install build dependencies and the package with the api extra.
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir ".[api]"

# Run as a non-root user (security hardening).
RUN useradd --create-home --uid 1000 appuser
USER appuser

# Default storage is local JSON; override TOT_STORAGE_BACKEND=firestore to
# use Firestore (requires google-cloud-firestore: pip install 'tot-agent[firestore]').
ENV TOT_STORAGE_BACKEND=local
ENV TOT_RUNTIME_DIR=/app/runtime

EXPOSE 8080

CMD ["uvicorn", "location_agent.api:app", "--host", "0.0.0.0", "--port", "8080"]
