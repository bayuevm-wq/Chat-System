# ============================================================
# Multi-stage Dockerfile for Distributed Chat System
# ============================================================
# Stage 1: Build dependencies
# Stage 2: Slim runtime image
# ============================================================

# ── Stage 1: Builder ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy project files and install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime ────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create non-root user for security
RUN groupadd -r chatapp && useradd -r -g chatapp -d /app -s /sbin/nologin chatapp

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Set ownership
RUN chown -R chatapp:chatapp /app

# Switch to non-root user
USER chatapp

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/live || exit 1

# Run with single worker per container (scale via Docker replicas)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
