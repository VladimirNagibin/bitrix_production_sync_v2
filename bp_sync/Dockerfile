# Общий этап для копирования файлов зависимостей
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /app
COPY pyproject.toml uv.lock ./

# ---- Продакшен-зависимости (без dev) ----
FROM base AS prod-deps
RUN uv sync --frozen --no-cache --no-dev --no-optional

# ---- Dev-зависимости (все, включая инструменты) ----
FROM base AS dev-deps
RUN uv sync --frozen --no-cache --all-extras --group dev

# ---- Финальный образ для продакшена ----
FROM python:3.13-slim-bookworm AS production

WORKDIR /app

# Создаём непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем только продакшен-окружение
COPY --from=prod-deps --chown=appuser:appuser /app/.venv /app/.venv

# Копируем исходный код
COPY --chown=appuser:appuser src/ ./src/

# Переменные окружения
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Создаём лог-директорию
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

CMD ["python", "/app/src/main.py"]

# ---- Образ для разработки (с dev-зависимостями) ----
FROM python:3.13-slim-bookworm AS development

WORKDIR /app

# Устанавливаем системные утилиты для удобства отладки
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Копируем окружение с dev-зависимостями
COPY --from=dev-deps /app/.venv /app/.venv

# Копируем исходный код (можно переопределить volume для монтирования)
COPY src/ ./src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Для разработки часто удобнее работать от root (но можно и appuser)
# USER appuser

EXPOSE 8000

# Для разработки можно запускать с --reload
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
CMD ["python", "/app/src/main.py"]
