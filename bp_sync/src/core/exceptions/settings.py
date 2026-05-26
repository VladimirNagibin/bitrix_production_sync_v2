"""
Модуль исключений, связанных с конфигурацией приложения.

Содержит иерархию исключений для ошибок загрузки, валидации и использования
настроек.
"""

from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ===== Базовое исключение конфигурации =====
class SettingsError(BaseAppException):
    """Базовое исключение для ошибок конфигурации."""

    DEFAULT_MESSAGE = "Configuration error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.SETTINGS_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует SettingsError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


# ===== Исключения для некорректных значений =====
class InvalidSettingsValueError(SettingsError):
    """
    Исключение, возникающее при некорректном значении параметра настроек.
    """

    DEFAULT_MESSAGE = "Invalid settings value"

    def __init__(
        self,
        field_name: str,
        value: Any,
        reason: str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует InvalidSettingsValueError.

        Args:
            field_name: Имя поля настроек
            value: Некорректное значение
            reason: Причина ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        self.field_name = field_name
        self.value = value
        self.reason = reason

        if message is None:
            message = f"Invalid value for '{field_name}': {value}. {reason}"

        super().__init__(
            error_code=ErrorCode.INVALID_SETTINGS_VALUE_ERROR,
            message=message,
            details=details,
            status_code=status_code,
        )


# ===== Исключения загрузки настроек =====
class SettingsLoadError(SettingsError):
    """
    Исключение, возникающее при ошибке загрузки настроек из окружения.
    """

    DEFAULT_MESSAGE = "Failed to load settings"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует SettingsLoadError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.SETTINGS_LOAD_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


# ===== Исключения валидации production-окружения =====
class ProductionSettingsError(SettingsError):
    """
    Исключение, возникающее при ошибке валидации настроек для production
    окружения.
    """

    DEFAULT_MESSAGE = "Production settings validation failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует ProductionSettingsError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.PRODUCTION_SETTINGS_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
