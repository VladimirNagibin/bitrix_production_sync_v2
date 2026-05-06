import inspect
import logging
import logging.config

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pythonjsonlogger.json import JsonFormatter
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    RequestException,
)
from requests.exceptions import (
    Timeout as RequestsTimeout,
)
from seqlog import SeqLogHandler

from core import settings


# ----------------------------------------------------------------------
# Кастомный фильтр для добавления имени класса и метода
# ----------------------------------------------------------------------
class CallerInfoFilter(logging.Filter):
    """Добавляет в запись лога module_name, class_name, method_name."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            stack = inspect.stack()
            # Ищем первый вызов за пределами этого модуля и модуля logging
            for frame_info in stack[1:]:
                filename = frame_info.filename
                if filename == __file__ or "logging" in filename:
                    continue
                record.module_name = filename
                record.method_name = frame_info.function
                # Пытаемся найти self или cls в locals кадра
                frame_locals = frame_info.frame.f_locals
                obj = frame_locals.get("self") or frame_locals.get("cls")
                record.class_name = obj.__class__.__name__ if obj else ""
                # Нашли нужный кадр – выходим
                break
            else:
                record.module_name = ""
                record.class_name = ""
                record.method_name = ""
        except Exception as e:  # noqa: BLE001
            logging.getLogger(__name__).debug(
                f"CallerInfoFilter error: {e}", exc_info=True
            )
            record.module_name = record.class_name = record.method_name = ""
        return True


# ----------------------------------------------------------------------
# Форматтер для JSON
# ----------------------------------------------------------------------
json_formatter = JsonFormatter(
    fmt=(
        "%(asctime)s %(levelname)s %(name)s %(module_name)s %(class_name)s "
        "%(method_name)s %(message)s"
    ),
    datefmt="%Y-%m-%dT%H:%M:%S",
    json_encoder=None,
)


# ----------------------------------------------------------------------
# Единая конфигурация логирования (включает все хендлеры и фильтры)
# ----------------------------------------------------------------------
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "caller_info": {"()": CallerInfoFilter},
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": (
                "%(asctime)s %(levelname)s %(name)s %(module_name)s "
                "%(class_name)s %(method_name)s %(message)s"
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": (
                "%(levelprefix)s %(client_addr)s - '%(request_line)s' "
                "%(status_code)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
            "filters": ["caller_info"],
        },
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": settings.app.log_level,
            "propagate": True,
        },
        "uvicorn.error": {
            "level": settings.app.log_level,
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": settings.app.log_level,
            "handlers": ["access"],
            "propagate": False,
        },
    },
}


# ----------------------------------------------------------------------
# Функции для создания дополнительных хендлеров
# ----------------------------------------------------------------------
def _create_file_handler() -> RotatingFileHandler | None:
    """
    Создаёт и возвращает файловый хендлер с ротацией, или None при ошибке.
    """
    try:
        log_dir = Path(settings.app.base_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        file_path = log_dir / "log.json"
        handler = RotatingFileHandler(
            file_path,
            maxBytes=getattr(
                settings.app, "logging_file_max_bytes", 10 * 1024 * 1024
            ),
            backupCount=getattr(settings.app, "logging_backup_count", 5),
            encoding="utf-8",
        )
        handler.setFormatter(json_formatter)
        handler.addFilter(CallerInfoFilter())
        handler.setLevel(settings.app.log_level)
    except (OSError, PermissionError, ValueError) as e:
        logging.getLogger(__name__).error(
            f"Failed to create file handler: {e}", exc_info=True
        )
        return None
    else:
        return handler


def _create_seq_handler() -> SeqLogHandler | None:
    """Создаёт и возвращает Seq-хендлер, или None при ошибке."""
    if not settings.seq.url:
        return None

    try:
        handler = SeqLogHandler(
            server_url=settings.seq.url,
            api_key=settings.seq.api_key,
            batch_size=10,
            auto_flush_timeout=1.0,
        )
        handler.setLevel(
            getattr(logging, settings.seq.level.upper(), logging.INFO)
        )
        handler.addFilter(CallerInfoFilter())
    except (
        RequestsConnectionError,
        RequestsTimeout,
        RequestException,
        OSError,
        ValueError,
    ) as e:
        logging.getLogger(__name__).error(
            f"Failed to create Seq handler: {e}", exc_info=True
        )
        return None
    except Exception as e:
        # Неожиданная ошибка — логируем, но не останавливаем приложение
        logging.getLogger(__name__).error(
            f"Unexpected error while creating Seq handler: {e}", exc_info=True
        )
        return None
    else:
        return handler


# ----------------------------------------------------------------------
# Патчинг дополнительных хендлеров
# ----------------------------------------------------------------------
def patch_logging_handlers() -> None:
    """
    Добавляет файловый и Seq хендлеры к корневому логгеру.
    Предотвращает дублирование хендлеров при многократном вызове.
    """
    root = logging.getLogger()

    # Проверяем, не добавлен ли уже файловый хендлер
    if getattr(settings.app, "log_to_file", False):
        already_has_file = any(
            isinstance(h, RotatingFileHandler) for h in root.handlers
        )
        if not already_has_file:
            file_handler = _create_file_handler()
            if file_handler:
                root.addHandler(file_handler)

    # Seq хендлер
    if settings.seq.url:
        already_has_seq = any(
            isinstance(h, SeqLogHandler) for h in root.handlers
        )
        if not already_has_seq:
            seq_handler = _create_seq_handler()
            if seq_handler:
                root.addHandler(seq_handler)
                logging.getLogger(__name__).info(
                    f"Seq logging enabled: {settings.seq.url}"
                )


# ----------------------------------------------------------------------
# Отключаем излишний DEBUG от библиотек
# ----------------------------------------------------------------------
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("seqlog").setLevel(logging.WARNING)


# ----------------------------------------------------------------------
# Автоматическая инициализация при импорте модуля
# ----------------------------------------------------------------------
def _init_logging() -> None:
    """Применяет конфигурацию и добавляет дополнительные хендлеры."""
    logging.config.dictConfig(LOGGING_CONFIG)
    patch_logging_handlers()
    # Убеждаемся, что логгер "sync" проксирует записи в root
    sync_logger = logging.getLogger("sync")
    sync_logger.propagate = True
    sync_logger.setLevel(getattr(settings.app, "log_level", "INFO"))


# Вызываем инициализацию при импорте модуля
_init_logging()


# ----------------------------------------------------------------------
# Глобальный логгер приложения
# ----------------------------------------------------------------------
logger = logging.getLogger("sync")
