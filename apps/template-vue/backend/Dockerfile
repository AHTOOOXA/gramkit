# Multi-stage Dockerfile for Template Vue Backend in Monorepo Workspace
#
# This Dockerfile handles the monorepo structure where:
# - Core infrastructure: /workspace/core/backend/
# - Template Vue application: /workspace/apps/template-vue/backend/
#
# Build stage installs dependencies, runtime stage runs the application

FROM python:3.14-slim as builder

# Install build dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

WORKDIR /workspace

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Copy core backend (needed for local editable install)
COPY core/backend/ ./core/backend/

# Copy template-vue backend (needed for local editable install)
COPY apps/template-vue/backend/ ./apps/template-vue/backend/

# Install dependencies with cache mount for faster rebuilds
# Note: Must copy source before sync because local packages are editable installs
# Using BuildKit cache mount to persist uv's cache between builds
WORKDIR /workspace/apps/template-vue/backend
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras

# Runtime stage - minimal Python image
FROM python:3.14-slim

# Install postgresql-client for pg_dump (database backups)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy entire workspace structure from builder (includes .venv)
COPY --from=builder /workspace/ /workspace/

# Set Python path to include both core and app source directories
# This allows imports from both packages
ENV PYTHONPATH=/workspace/core/backend/src:/workspace/apps/template-vue/backend/src:$PYTHONPATH

# Use virtual environment Python directly
ENV PATH="/workspace/.venv/bin:$PATH"

# Default working directory for runtime
WORKDIR /workspace/apps/template-vue/backend

# Default command (overridden in docker-compose for different services)
CMD ["python", "-u", "src/app/webhook/app.py"]
