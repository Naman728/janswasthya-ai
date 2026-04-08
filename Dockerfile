# Hugging Face Spaces — self-contained build (no GHCR openenv-base).
# Context: repository root. Code: janswasthya_env/ → /app (flat layout for server.app).

FROM python:3.10-slim-bookworm

WORKDIR /app

# curl: HEALTHCHECK; git: sometimes needed for VCS deps (openenv-core is PyPI-only here)
RUN apt-get update && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy environment package (pyproject.toml, server/, models.py, …)
COPY janswasthya_env/ /app/

# Install runtime deps from pyproject (same as local uv sync would resolve)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir "openenv-core[core]>=0.2.2"

# Flat layout: /app/server, /app/models.py → `uvicorn server.app:app`
ENV PYTHONPATH=/app

EXPOSE 7860

# Long start_period: HF cold start + heavy imports (openenv, fastapi)
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD curl -fsS http://127.0.0.1:7860/health > /dev/null || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
