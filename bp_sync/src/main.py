import logging.config

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.health_checker import health_router
from core import settings
from core.logger import LOGGING_CONFIG, logger, patch_logging_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управление жизненным циклом приложения."""
    logger.info(f"Initializing {app.title} ...")
    yield
    logger.info(f"Closing {app.title} ...")


def setup_routes(app: FastAPI) -> None:
    """Настройка маршрутов приложения."""
    app.include_router(health_router, prefix="/api/health", tags=["health"])


def create_app() -> FastAPI:
    """Фабрика для создания приложения."""
    app = FastAPI(
        title=settings.app.project_name,
        docs_url="/api/openapi",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    setup_routes(app)

    # Монтируем папку static по URL /static
    static_dir = Path(settings.app.base_dir) / "static"
    if static_dir.exists() and static_dir.is_dir():
        app.mount(
            "/static", StaticFiles(directory=str(static_dir)), name="static"
        )
    else:
        logger.warning(f"Static directory not found: {static_dir}")

    return app


def start_server() -> None:
    # 1. Применяем базовую конфигурацию (консоль)
    logging.config.dictConfig(LOGGING_CONFIG)
    # 2. Добавляем файловый и Seq хендлеры
    patch_logging_handlers()
    # 3. Запускаем Uvicorn, запрещая ему менять логирование
    uvicorn.run(
        "main:app",
        host=settings.app.host,
        port=settings.app.port,
        log_config=None,  # LOGGING_CONFIG,
        log_level=None,  # settings.app.log_level.lower(),
        reload=settings.app.reload,
    )


app = create_app()


if __name__ == "__main__":
    logger.info("Starting server...")
    start_server()
