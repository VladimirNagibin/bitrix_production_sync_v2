from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ----------------------------------------------------------------------
# Исключения, связанные с базой данных
# ----------------------------------------------------------------------


class DatabaseError(BaseAppException):
    """Базовое исключение для ошибок работы с БД."""

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.ERROR_WORKING_WITH_DB,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Ошибка при работе с БД"
        super().__init__(error_code, msg, details, status_code)


class DatabaseConnectionError(DatabaseError):
    """Ошибка подключения к базе данных."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Не удалось подключиться к базе данных"
        super().__init__(
            error_code=ErrorCode.DB_CONNECTION_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class DatabaseLoadError(DatabaseError):
    """Ошибка при загрузке данных в БД."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Ошибка загрузки данных в БД"
        super().__init__(
            error_code=ErrorCode.ERROR_LOADING_DATA_TO_DB,
            message=msg,
            details=details,
            status_code=status_code,
        )
