# Multi-stage build for AIMA Status Checker

# Stage 1: Builder - Install dependencies with Poetry
FROM python:3.11-slim as builder

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /app

# Copy dependency files (poetry.lock* allows build even if lock file is missing)
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to create virtualenv in project directory
RUN poetry config virtualenvs.in-project true

# Install dependencies with hash verification from poetry.lock
# --no-root: Don't install the project itself, only dependencies
# --only main: Skip dev dependencies
RUN poetry install --no-root --only main

# Stage 2: Runtime - Copy venv and run application
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app ./app

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application using virtual environment's Python
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
