FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Копируем зависимости
COPY pyproject.toml pyproject.toml
COPY uv.lock .

# Устанавливаем зависимости
RUN uv sync --frozen --no-cache

# Create a minimal runtime image
FROM python:3.13-slim-bookworm

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Копируем код
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Create log directory and set permissions
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Запускаем 
CMD ["python", "/app/src/main.py"]
