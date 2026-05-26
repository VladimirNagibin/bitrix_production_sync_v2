"""
Модуль исключений для Redis клиента.

Содержит иерархию исключений, возникающих при работе с Redis:
ошибки подключения, аутентификации, таймауты, неинициализированный клиент
и т.д.
"""

from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ====== Исключения, связанные с Redis =======
class RedisManagerError(BaseAppException):
    """Базовое исключение для ошибок Redis клиента."""

    DEFAULT_MESSAGE = "Redis operation failed"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.REDIS_CLIENT_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует RedisManagerError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class RedisManagerConnectionError(RedisManagerError):
    """
    Исключение, возникающее при ошибке подключения к Redis
    (сетевые проблемы, таймаут и т.д.).
    """

    DEFAULT_MESSAGE = "Failed to connect to Redis"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует RedisManagerConnectionError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.REDIS_CONNECTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class RedisManagerAuthError(RedisManagerError):
    """
    Исключение, возникающее при ошибке аутентификации в Redis.
    """

    DEFAULT_MESSAGE = "Redis authentication failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует RedisManagerAuthError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.REDIS_AUTH_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class RedisManagerNotInitializedError(RedisManagerError):
    """Исключение, возникающее когда Redis клиент не был инициализирован."""

    DEFAULT_MESSAGE = "Redis client not initialized"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует RedisManagerNotInitializedError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.REDIS_NOT_INIT_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class RedisManagerTimeoutError(RedisManagerError):
    """
    Исключение, возникающее при превышении времени ожидания операции Redis.
    """

    DEFAULT_MESSAGE = "Redis operation timeout"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует RedisManagerTimeoutError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.REDIS_TIME_OUT_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
