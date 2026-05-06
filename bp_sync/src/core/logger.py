import inspect
import logging

from logging import config
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pythonjsonlogger.json import JsonFormatter
from seqlog import SeqLogHandler

from core import LogLevel, settings


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------
def create_directory(path: Path) -> None:
    """Создаёт директорию рекурсивно, если её нет."""
    path.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Кастомный фильтр для добавления имени класса и метода
# ----------------------------------------------------------------------
class CallerInfoFilter(logging.Filter):
    """
    Добавляет в запись лога поля:
        - module_name  (имя модуля)
        - class_name   (имя класса, если вызов внутри метода класса)
        - method_name  (имя функции или метода)
    Использует интроспекцию стека.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Ищем вызов логгера в стеке
        # Структура стека: [текущий filter, логгер, ... , вызывающий код]
        caller_frame = None
        frame = None
        try:
            frame = inspect.currentframe()
            # Поднимаемся на 3 кадра вверх:
            # 0: этот filter(), 1: Logger._log(), 2: Logger.debug/info...,
            # 3: место, где вызван логгер
            stack = inspect.stack()
            # Находим первый кадр, который не принадлежит модулю logging
            for frame_info in stack[2:]:  # пропускаем filter и _log
                if (
                    frame_info.filename != __file__
                    and not frame_info.filename.startswith("<")
                ):
                    caller_frame = frame_info.frame
                    break

            if caller_frame:
                # Извлекаем информацию о вызывающем коде
                frame_locals = caller_frame.f_locals
                # Имя метода (функции)
                record.method_name = caller_frame.f_code.co_name
                # Имя модуля (файла)
                record.module_name = caller_frame.f_code.co_filename
                # Имя класса (если есть self или cls в locals)
                obj = frame_locals.get("self") or frame_locals.get("cls")
                if obj:
                    record.class_name = obj.__class__.__name__
                else:
                    record.class_name = ""
            else:
                record.class_name = ""
                record.method_name = ""
                record.module_name = ""
        finally:
            # Очищаем ссылки на кадры, чтобы избежать циклов сборщика мусора
            if frame:
                del frame
            if caller_frame:
                del caller_frame
        return True


# ----------------------------------------------------------------------
# Форматтеры
# ----------------------------------------------------------------------
# JSON-форматтер с добавлением полей из кастомного фильтра
json_formatter = JsonFormatter(
    fmt=(
        "%(asctime)s %(levelname)s %(name)s %(module_name)s %(class_name)s "
        "%(method_name)s %(message)s"
    ),
    # Преобразуем время в ISO формат
    datefmt="%Y-%m-%dT%H:%M:%S",
    # Если нужно добавить дополнительные поля (например, имя процесса),
    # можно расширить этот словарь
    # extra={'hostname': socket.gethostname()}
    # Можно добавить exclude или rename, если нужно
    json_encoder=None,
)


# ----------------------------------------------------------------------
# Функция создания Seq-хендлера
# ----------------------------------------------------------------------
def get_seq_handler() -> SeqLogHandler:
    """Создает и настраивает хендлер для Seq."""
    return SeqLogHandler(
        server_url=settings.seq.url,
        api_key=settings.seq.api_key,
        batch_size=10,  # Отправлять логи пачками
        auto_flush_timeout=1.0,  # Или раз в секунду
        # flush_on_exit=True,  # Отправить оставшиеся логи при завершении
        # fail_on_exception=False,  # Не падать при ошибках отправки
    )


# ----------------------------------------------------------------------
# Базовый словарь конфигурации логгеров (для console и uvicorn)
# ----------------------------------------------------------------------
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # JSON форматтер для консоли и файлов
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": (
                "%(asctime)s %(levelname)s %(name)s %(module_name)s "
                "%(class_name)s %(method_name)s %(message)s"
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        # Если нужно оставить читаемый текст для Uvicorn (опционально),
        # но для Seq обычно всё переводят в JSON.
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": (
                "%(levelprefix)s %(client_addr)s - "
                "'%(request_line)s' %(status_code)s"
            ),
        },
    },
    "handlers": {
        # Консольный вывод (теперь в JSON)
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
        # Хендлер для Seq (будет добавлен программно,
        # так как SeqLogHandler не всегда удобно конфигурировать через dict)
        # "seq": {
        #     "class": "seqlog.SeqLogHandler",
        #     ...
        # }
        # Uvicorn хендлеры
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],  # только консоль, Seq добавим отдельно
            "level": settings.app.log_level,
        },
        "uvicorn.error": {
            "level": LogLevel.INFO,
            "handlers": ["default"],  # Можно также заменить formatter на json
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": LogLevel.INFO,
            "propagate": False,
        },
    },
}


# ----------------------------------------------------------------------
# Инициализация логгера
# ----------------------------------------------------------------------
def setup_logging() -> None:
    """
    Настраивает всё логирование:
        - применяет базовую конфигурацию (консоль + uvicorn)
        - добавляет кастомный фильтр CallerInfoFilter в корневой логгер
        - добавляет Seq-хендлер (если включён)
        - добавляет файловый хендлер с ротацией (если включён)
    """
    # Применяем базовую конфигурацию
    config.dictConfig(LOGGING_CONFIG)

    root_logger = logging.getLogger()
    # Устанавливаем уровень из настроек приложения
    root_logger.setLevel(settings.app.log_level)

    # Добавляем фильтр для обогащения логов информацией о вызывающем коде
    root_logger.addFilter(CallerInfoFilter())

    # Логгер для сообщений о процессе настройки (используем уже настроенный)
    setup_logger = logging.getLogger(__name__)

    # Настройка Seq
    if settings.seq.url:
        try:
            seq_handler = get_seq_handler()
            seq_handler.setLevel(settings.seq.level)
            root_logger.addHandler(seq_handler)
            setup_logger.info(f"Seq logging enabled: {settings.seq.url}")
        except (ConnectionError, TimeoutError, ValueError, OSError) as e:
            setup_logger.error(
                f"Failed to create Seq handler: {e}", exc_info=True
            )
        except Exception as e:
            # Если возникло неожиданное исключение, логируем его тоже
            setup_logger.error(
                f"Unexpected error while creating Seq handler: {e}",
                exc_info=True,
            )

    # Файловый логгер с ротацией (JSON)
    if getattr(settings.app, "log_to_file", False):
        try:
            log_dir = Path(settings.app.base_dir) / "logs"
            create_directory(log_dir)

            file_path = log_dir / "log.json"
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=getattr(
                    settings.app, "logging_file_max_bytes", 10 * 1024 * 1024
                ),
                backupCount=getattr(settings.app, "logging_backup_count", 5),
                encoding="utf-8",
            )
            file_handler.setLevel(settings.app.log_level)
            file_handler.setFormatter(json_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError, ValueError) as e:
            setup_logger.error(
                f"Failed to create file handler: {e}", exc_info=True
            )
        except Exception as e:
            setup_logger.error(
                f"Unexpected error while creating file handler: {e}",
                exc_info=True,
            )


# ----------------------------------------------------------------------
# Глобальный логгер для использования в приложении
# ----------------------------------------------------------------------
# Вызываем настройку при импорте модуля
setup_logging()

# Экспортируемый логгер
logger = logging.getLogger("sync")
