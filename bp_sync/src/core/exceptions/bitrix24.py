from typing import Any

from fastapi import status

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения, связанные с Bitrix24 =====
class Bitrix24Error(BaseAppException):
    """Базовое исключение для ошибок работы Bitrix24."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Bitrix24 error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.BITRIX24_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение Bitrix24Error.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


# ----- ошибки обработки полей -----
class BitrixValidationError(Bitrix24Error):
    """ "Базовое исключение для ошибок валидации Bitrix."""

    def __init__(
        self,
        field_name: str | None = None,
        value: Any | None = None,
        reason: str | None = None,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует BitrixValidationError.

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
            error_code=ErrorCode.BITRIX_VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=status_code,
        )


class BitrixParseError(BitrixValidationError):
    """Ошибка парсинга значения поля."""

    def __init__(
        self,
        field_name: str | None = None,
        value: Any | None = None,
        reason: str | None = None,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            field_name=field_name,
            value=value,
            reason=reason,
            message=message,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.BITRIX_PARSE_ERROR


class BitrixTypeError(BitrixValidationError):
    """Ошибка несоответствия типа значения."""

    def __init__(
        self,
        field_name: str | None = None,
        value: Any | None = None,
        reason: str | None = None,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            field_name=field_name,
            value=value,
            reason=reason,
            message=message,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.BITRIX_TYPE_ERROR


class BitrixAuthError(Bitrix24Error):
    """Ошибка аутентификации в Битрикс24."""

    DEFAULT_MESSAGE = "Bitrix authentication failed"

    def __init__(
        self,
        error: str = "Unknown error",
        error_description: str = "Unknown Bitrix API error",
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = status.HTTP_401_UNAUTHORIZED,
    ) -> None:
        """
        Инициализирует BitrixAuthError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        self.error = error
        self.error_description = error_description
        super().__init__(
            error_code=ErrorCode.BITRIX_AUTH_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class BitrixApiError(Bitrix24Error):
    """Ошибка при запросах по Api."""

    DEFAULT_MESSAGE = "Bitrix api error"

    def __init__(
        self,
        error: str = "Unknown error",
        error_description: str = "Unknown Bitrix API error",
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.error = error
        self.error_description = error_description
        super().__init__(
            error_code=ErrorCode.BITRIX_API_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )

    def is_expected_error(self, expected_error: str) -> bool:
        """Проверяет, является ли ошибка заданного типа"""
        return bool(self.error_description == expected_error)

    def is_not_found_error(self) -> bool:
        """Проверяет, является ли ошибка ошибкой 'Not Found'"""
        status_code = getattr(self, "status_code", None)
        return bool(
            isinstance(status_code, int)
            and status_code == status.HTTP_400_BAD_REQUEST
            and self.is_expected_error("Not found")
        )
