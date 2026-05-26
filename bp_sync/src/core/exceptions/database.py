"""
Модуль исключений для работы с базой данных и каналами связи.

Содержит иерархию исключений, специфичных для операций с БД,
подключения, загрузки данных и обработки коммуникационных каналов.
"""

from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения, связанные с базой данных =====
class DatabaseError(BaseAppException):
    """Базовое исключение для ошибок работы с БД."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Database operation failed"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.ERROR_WORKING_WITH_DB,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение DatabaseError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class DatabaseConnectionError(DatabaseError):
    """Ошибка подключения к базе данных."""

    DEFAULT_MESSAGE = "Unable to connect to the database"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует DatabaseConnectionError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.DB_CONNECTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class DatabaseLoadError(DatabaseError):
    """Ошибка при загрузке данных в БД."""

    DEFAULT_MESSAGE = "Failed to load data into the database"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует DatabaseLoadError.

        Args:
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.ERROR_LOADING_DATA_TO_DB,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


# ===== Исключения, связанные с CommunicationChannel =====
class CommunicationError(DatabaseError):
    """Базовое исключение для ошибок коммуникационных каналов."""

    DEFAULT_MESSAGE = "Communication channel error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.DB_COMMUNICATION_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CommunicationError.

        Args:
            error_code: Код ошибки (по умолчанию DB_COMMUNICATION_ERROR)
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code, message or self.DEFAULT_MESSAGE, details, status_code
        )


class CommunicationChannelTypeError(CommunicationError):
    """Ошибка, связанная с типом канала связи."""

    DEFAULT_MESSAGE = "Invalid communication channel type"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CommunicationChannelTypeError.

        Args:
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали (например, переданный тип)
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.DB_INVALID_COMMUNICATION_TYPE,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class CommunicationChannelValueError(CommunicationError):
    """Ошибка значения канала связи (некорректные данные)."""

    DEFAULT_MESSAGE = "Invalid communication channel value"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.DB_INVALID_COMMUNICATION_VALUE,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
