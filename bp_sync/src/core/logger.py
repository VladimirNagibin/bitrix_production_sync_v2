"""Модуль настройки логирования приложения.

Обеспечивает вывод логов в консоль (JSON),
файл с ротацией и удалённый сервер Seq.
Добавляет в каждую запись информацию о модуле, классе и методе вызова.
"""

import inspect
import json
import logging
import logging.config
import threading
import time

from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests

from pythonjsonlogger.json import JsonFormatter
from requests.exceptions import RequestException

from core import settings

from .utils import FILTER_FIELDS, SYSTEM_FIELDS, LogLevel


# ----------------------------------------------------------------------
# Константы настройки
# ----------------------------------------------------------------------
SEQ_BATCH_SIZE = 1
SEQ_AUTO_FLASH_INTERVAL = 2.0
SEQ_TIMEOUT = 5
FILE_MAX_BYTES = 10 * 1024 * 1024
FILE_BACKUP_COUNT = 5


# ----------------------------------------------------------------------
# Хендлер для отправки в Seq (CLEF-формат)
# ----------------------------------------------------------------------
class SeqJsonHandler(logging.Handler):
    """Отправляет логи в Seq через HTTP API в формате CLEF.

    Логи буферизируются и отправляются пачками (batch) для повышения
    производительности. При ошибках отправки буфер очищается,
    чтобы избежать бесконечных повторных попыток.
    Использует блокирующий `requests`, что может
    замедлить работу асинхронных приложений при высокой нагрузке.
    """

    def __init__(
        self,
        server_url: str,
        api_key: str = "",
        batch_size: int = SEQ_BATCH_SIZE,
        auto_flush_interval: float = SEQ_AUTO_FLASH_INTERVAL,
    ) -> None:
        """Инициализирует хендлер.

        Args:
            server_url: Базовый URL сервера Seq (например, http://seq:80).
            api_key: API-ключ для аутентификации (опционально).
            batch_size: Количество событий в одной пачке.
            auto_flush_interval: Максимальное время (сек) между
            автоматическими отправками.
        """
        super().__init__()
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.batch_size = batch_size
        self.auto_flush_interval = auto_flush_interval
        self.batch: list[str] = []
        self._last_flush = 0.0
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.SeqJsonHandler")
        self._fail_count = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Форматирует запись и добавляет в буфер."""
        try:
            msg = self.format(record)
            with self._lock:
                self.batch.append(msg)
                now = time.time()
                if (
                    len(self.batch) >= self.batch_size
                    or (now - self._last_flush) >= self.auto_flush_interval
                ):
                    self._flush_internal()
        except (ValueError, TypeError, AttributeError) as e:
            self._logger.error(
                "Error formatting record: %s", e, exc_info=True
            )
            self.handleError(record)
        except Exception as e:
            self._logger.error(
                "Unexpected error formatting record: %s",
                e,
                exc_info=True,
            )
            self.handleError(record)

    def _flush_internal(self) -> None:
        """
        Выполняет отправку накопленных событий. Вызывается с захваченным lock.
        """
        if not self.batch:
            return

        events: list[dict[str, Any]] = []
        for event_str in self.batch:
            try:
                event = json.loads(event_str)
                # Валидация обязательных полей CLEF
                if "Timestamp" in event and "MessageTemplate" in event:
                    events.append(event)
                else:
                    self._logger.warning(
                        "Invalid event, skipping: %s", event_str[:100]
                    )

            except json.JSONDecodeError:
                self._logger.error(
                    "JSON parse error: %s", event_str[:100], exc_info=True
                )
                continue

        if not events:
            self.batch.clear()
            return

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Seq-ApiKey"] = self.api_key

        try:
            response = requests.post(
                f"{self.server_url}/api/events/raw",
                json={"Events": events},
                headers=headers,
                timeout=SEQ_TIMEOUT,
            )
            response.raise_for_status()
            self.batch.clear()
            self._last_flush = time.time()
            self._fail_count = 0
        except RequestException as e:
            self._logger.error(
                "Network error sending to Seq: %s", e, exc_info=True
            )
            self._fail_count += 1
            # При потере пакета на network error, мы теряем батч,
            # чтобы не забивать буфер и не ломать логирование
            self.batch.clear()
        except (ValueError, TypeError) as e:
            self._logger.error(
                "Data error sending to Seq: %s", e, exc_info=True
            )
            self.batch.clear()
        except Exception as e:
            self._logger.error(
                "Unexpected error sending to Seq: %s", e, exc_info=True
            )
            self.batch.clear()

    def flush(self) -> None:
        """
        Принудительная отправка всех накопленных событий (потокобезопасно).
        """
        with self._lock:
            self._flush_internal()

    def close(self) -> None:
        """Гарантированная отправка оставшихся логов при закрытии."""
        try:
            if self.batch:
                self._logger.info(
                    "Closing Seq handler, flushing %d events", len(self.batch)
                )
                self.flush()
        finally:
            super().close()


# ----------------------------------------------------------------------
# Форматтер для Seq в стандарте CLEF
# ----------------------------------------------------------------------
class SeqClefFormatter(logging.Formatter):
    """
    Форматтер для Seq в формате CLEF (Compact Log Event Format).

    Документация: https://docs.datalust.co/docs/sending-raw-json
    """

    def __init__(self) -> None:
        super().__init__(datefmt="%Y-%m-%dT%H:%M:%S.%f")

    def formatTime(
        self, record: logging.LogRecord, datefmt: str | None = None
    ) -> str:
        """
        Возвращает время события в формате ISO 8601 с миллисекундами и
        суффиксом Z (UTC).
        """
        dt = datetime.fromtimestamp(record.created, tz=UTC)
        return dt.strftime(datefmt or "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись в JSON-событие с защитой от падений."""
        try:
            return self._format_impl(record)
        except Exception as e:  # noqa: BLE001
            # Fallback: если всё упало, возвращаем безопасный минимальный JSON
            return json.dumps(
                {
                    "Timestamp": self.formatTime(record),
                    "MessageTemplate": str(record.getMessage()),
                    "Level": "ERROR",
                    "Properties": {
                        "RenderingError": str(e),
                        "OriginalMessage": str(record.msg),
                    },
                },
                ensure_ascii=False,
            )

    def _format_impl(self, record: logging.LogRecord) -> str:
        """Реальная логика форматирования."""

        # Обязательные поля CLEF
        event: dict[str, Any] = {
            "Timestamp": self.formatTime(record),  # @t
            "MessageTemplate": str(record.getMessage()),  # @mt
            "Level": record.levelname,
        }

        # Исключение (если есть)
        if record.exc_info:
            event["Exception"] = self.formatException(record.exc_info)  # @x

        # Формируем контекстные свойства
        properties: dict[str, Any] = {
            "Logger": record.name,
            "ProcessId": record.process,
            "ThreadId": record.thread,
            "FileName": record.filename,
            "LineNumber": record.lineno,
            "Function": record.funcName,
        }

        #  Кастомные поля из фильтра (module_name, class_name, method_name)
        for attr, dest in FILTER_FIELDS:
            val = getattr(record, attr, None)
            if val:
                properties[dest] = val

        # Все поля из extra (исключая системные)
        for key, value in record.__dict__.items():
            if key not in properties and key not in SYSTEM_FIELDS:
                # Сериализуем сложные объекты в строки
                if isinstance(value, str | int | float | bool | type(None)):
                    properties[key] = value
                else:
                    try:
                        properties[key] = json.dumps(
                            value, default=str, ensure_ascii=False
                        )
                    except Exception:  # noqa: BLE001
                        properties[key] = str(value)

        # Добавляем свойства к событиям
        if properties:
            event["Properties"] = properties

        return json.dumps(event, ensure_ascii=False)


# ----------------------------------------------------------------------
# Фильтр для добавления информации о вызывающем коде
# ----------------------------------------------------------------------
class CallerInfoFilter(logging.Filter):
    """
    Фильтр, добавляющий в запись поля module_name, class_name, method_name.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            stack = inspect.stack()
            for frame_info in stack[1:]:
                filename = frame_info.filename
                if (
                    filename == __file__
                    or "logging" in filename
                    or "/logging/" in filename
                    or "\\logging\\" in filename
                ):
                    continue
                record.module_name = filename
                record.method_name = frame_info.function

                # Пытаемся найти self или cls
                frame_locals = frame_info.frame.f_locals
                obj = frame_locals.get("self") or frame_locals.get("cls")
                record.class_name = obj.__class__.__name__ if obj else ""
                break
            else:
                record.module_name = ""
                record.class_name = ""
                record.method_name = ""
        except Exception as e:  # noqa: BLE001
            # Ошибки интроспекции – не ломаем логирование, заполняем пустыми
            logging.getLogger(__name__).debug(
                "Introspection error: %s", e, exc_info=True
            )
            record.module_name = record.class_name = record.method_name = ""
        return True


# ----------------------------------------------------------------------
# Форматтер для консоли и файла
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
# Конфигурация логирования (dictConfig)
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
    """Создаёт файловый хендлер с ротацией. Возвращает None при ошибке."""
    try:
        log_dir = Path(settings.app.base_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            log_dir / "log.json",
            maxBytes=getattr(
                settings.app, "logging_file_max_bytes", FILE_MAX_BYTES
            ),
            backupCount=getattr(
                settings.app, "logging_backup_count", FILE_BACKUP_COUNT
            ),
            encoding="utf-8",
        )
        handler.setFormatter(json_formatter)
        handler.addFilter(CallerInfoFilter())
        handler.setLevel(settings.app.log_level)
    except (OSError, PermissionError, ValueError) as e:
        logging.getLogger(__name__).error(
            "Failed to create file handler: %s", e, exc_info=True
        )
        return None
    except Exception as e:
        logging.getLogger(__name__).error(
            "Unexpected error creating file handler: %s",
            e,
            exc_info=True,
        )
        return None
    else:
        return handler


def _create_seq_handler() -> logging.Handler | None:
    """
    Создаёт хендлер для отправки логов в Seq. Возвращает None при ошибке.
    """
    if not settings.seq.url:
        return None

    try:
        handler = SeqJsonHandler(
            server_url=settings.seq.url,
            api_key=settings.seq.api_key,
            batch_size=SEQ_BATCH_SIZE,
        )
        handler.setFormatter(SeqClefFormatter())
        handler.setLevel(
            getattr(logging, settings.seq.level.upper(), logging.INFO)
        )
        handler.addFilter(CallerInfoFilter())
    except (ValueError, TypeError, OSError) as e:
        logging.getLogger(__name__).error(
            "Seq handler configuration error: %s", e, exc_info=True
        )
        return None
    except Exception as e:
        logging.getLogger(__name__).error(
            "Unexpected error creating Seq handler: %s",
            e,
            exc_info=True,
        )
        return None
    else:
        return handler


# ----------------------------------------------------------------------
# Патчинг хендлеров (инициализация)
# ----------------------------------------------------------------------
def patch_logging_handlers() -> None:
    """
    Добавляет файловый и Seq хендлеры к корневому логгеру (без дублирования).
    """
    root = logging.getLogger()

    # Флаги успешного создания для логирования в конце
    file_enabled = False
    seq_enabled = False
    seq_url = ""

    # 1. Файловый хендлер
    if getattr(settings.app, "log_to_file", False):
        already_has_file = any(
            isinstance(h, RotatingFileHandler) for h in root.handlers
        )
        if not already_has_file:
            file_handler = _create_file_handler()
            if file_handler:
                root.addHandler(file_handler)
                file_enabled = True

    # 2. Seq хендлер
    if settings.seq.url:
        already_has_seq = any(
            isinstance(h, SeqJsonHandler) for h in root.handlers
        )
        if not already_has_seq:
            seq_handler = _create_seq_handler()
            if seq_handler:
                root.addHandler(seq_handler)
                seq_enabled = True
                seq_url = settings.seq.url

    # 3. Логируем статус только ПОСЛЕ настройки,
    # чтобы логи попали в новый хендлер
    if file_enabled:
        logging.getLogger(__name__).info("File logging enabled")

    if seq_enabled:
        logging.getLogger(__name__).info("Seq logging enabled: %s", seq_url)


# ----------------------------------------------------------------------
# Настройка уровня логов внешних библиотек
# ----------------------------------------------------------------------
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ----------------------------------------------------------------------
# Инициализация модуля
# ----------------------------------------------------------------------
_init_done = False


def _init_logging() -> None:
    """Инициализация логирования при импорте модуля."""
    global _init_done
    if _init_done:
        return

    logging.config.dictConfig(LOGGING_CONFIG)
    patch_logging_handlers()

    # Настройка логгера приложения
    sync_logger = logging.getLogger("sync")
    sync_logger.propagate = True
    sync_logger.setLevel(getattr(settings.app, "log_level", LogLevel.INFO))

    # Регистрируем принудительный сброс буферов при завершении
    import atexit

    def flush_all() -> None:
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
        logging.shutdown()

    atexit.register(flush_all)
    _init_done = True


# ----------------------------------------------------------------------
# Точка входа настройки
# ----------------------------------------------------------------------
_init_logging()

# Глобальный логгер
logger = logging.getLogger("sync")
