# Multi-stage Dockerfile for FastAPI Backend
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as runner

WORKDIR /app

# Create non-root user and persistent data directory
RUN useradd -u 1000 -m appuser && \
    mkdir -p /data && \
    chown -R appuser:appuser /data /app

# Copy python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LITELLM_LOCAL_MODEL_COST_MAP=true

# Copy application source
COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8000

# Render injects $PORT; default to 8000 for local Docker Compose
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
