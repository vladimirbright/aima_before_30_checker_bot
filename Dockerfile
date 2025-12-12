# Multi-stage build for AIMA Status Checker

# Stage 1: Builder - Export dependencies
FROM python:3.11-slim as builder

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

WORKDIR /app

# Copy poetry files
COPY pyproject.toml ./

# Export dependencies to requirements.txt
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes --without dev

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements from builder
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
