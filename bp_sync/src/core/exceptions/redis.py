from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


class RedisManagerError(BaseAppException):
    """Базовое исключение для ошибок Redis клиента."""

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.REDIS_CLIENT_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Ошибка при работе с Redis"
        super().__init__(error_code, msg, details, status_code=status_code)


class RedisManagerConnectionError(RedisManagerError):
    """Ошибка подключения к Redis (сетевые проблемы, таймаут и т.д.)."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Не удалось подключиться к Redis"
        super().__init__(
            error_code=ErrorCode.REDIS_CONNECTION_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class RedisManagerAuthError(RedisManagerError):
    """Ошибка аутентификации в Redis (неверный пароль)."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Ошибка аутентификации в Redis"
        super().__init__(
            error_code=ErrorCode.REDIS_AUTH_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class RedisManagerNotInitializedError(RedisManagerError):
    """Redis клиент не был инициализирован."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Redis клиент не был инициализирован"
        super().__init__(
            error_code=ErrorCode.REDIS_NOT_INIT_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class RedisManagerTimeoutError(RedisManagerError):
    """Тайм-аут операции Redis."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Тайм-аут операции Redis"
        super().__init__(
            error_code=ErrorCode.REDIS_TIME_OUT_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )
