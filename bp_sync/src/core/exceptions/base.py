from typing import Any

# from core.logger import logger
from .enums import ErrorCode


# ===== Вспомогательная функция для логирования исключений =====
# def _log_exception_creation(
#     exception_class: str, message: str, details: Any = None
# ) -> None:
#     """
#     Логирует создание исключения с использованием структурированного
#     JSON-логирования.

#     Args:
#         exception_class: Имя класса исключения (например, 'ConnectionError')
#         message: Сообщение об ошибке
#         details: Дополнительные детали ошибки (словарь, строка и т.п.)
#     """
#     # ----- Формирование структурированных полей для JSON-лога -----
#     extra_fields = {
#         "exception_class": exception_class,
#         "exception_message": message,
#     }
#     if details is not None:
#         extra_fields["details"] = details

#     logger.debug("Exception created", extra=extra_fields)


# ===== Базовое исключение =====
class BaseAppException(Exception):
    """Базовое исключение для всех ошибок приложения."""

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        self.error_code = str(error_code)
        self.message = message or self.__class__.__name__
        self.details = details
        status_code = status_code
        super().__init__(self.message)

        # ----- Логирование создания исключения -----
        # _log_exception_creation(
        #     self.__class__.__name__, self.message, self.details
        # )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} code='{self.error_code}' "
            f"message='{self.message}'>"
        )
