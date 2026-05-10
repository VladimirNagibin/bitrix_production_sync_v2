from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ----------------------------------------------------------------------
# Исключения, связанные с конфигурацией
# ----------------------------------------------------------------------


class SettingsError(BaseAppException):
    """Базовое исключение для ошибок конфигурации."""

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.SETTINGS_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        msg = message or "Ошибка при работе с конфигурацией"
        super().__init__(error_code, msg, details, status_code=status_code)


class InvalidSettingsValueError(SettingsError):
    """Некорректное значение параметра настроек."""

    def __init__(
        self,
        field_name: str,
        value: Any,
        reason: str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ):
        self.field_name = field_name
        self.value = value
        self.reason = reason
        msg = message or f"Ошибка в настройке {field_name}={value}: {reason}"
        super().__init__(
            error_code=ErrorCode.INVALID_SETTINGS_VALUE_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )
