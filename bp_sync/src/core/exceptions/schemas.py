from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения, связанные со схемой данных ======
class SchemaError(BaseAppException):
    """Базовое исключение для ошибок при работе со схемой данных."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Schema error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.SCHEMA_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение SchemaError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class ComparisonError(SchemaError):
    """Базовое исключение для ошибок при сравнении сущностей."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Comparison schemas error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение ComparisonError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(
            error_code=ErrorCode.COMPARISON_ERROR,
            message=final_message,
            details=details,
            status_code=status_code,
        )


class FieldComparisonError(ComparisonError):
    """Исключение, возникающее при ошибке сравнения конкретного поля."""

    def __init__(
        self,
        field_name: str,
        reason: str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует FieldComparisonError.

        Args:
            field_name: Имя поля настроек
            reason: Причина ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        self.field_name = field_name
        self.reason = reason
        if message is None:
            message = f"Invalid comparison for '{field_name}': {reason}"

        super().__init__(
            message=message,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.FIELD_COMPARISON_ERROR


class PaginationError(SchemaError):
    """Исключение для ошибок при работе с пагинацией."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Pagination error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение PaginationError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(
            error_code=ErrorCode.PAGINATION_ERROR,
            message=final_message,
            details=details,
            status_code=status_code,
        )


class SchemaValidationError(SchemaError):
    """Raised when schema validation fails."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Schema validation error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение SchemaValidationError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(
            error_code=ErrorCode.SCHEMA_VALIDATION_ERROR,
            message=final_message,
            details=details,
            status_code=status_code,
        )


class NegativeValueError(SchemaValidationError):
    """Raised when a non-negative field gets a negative value."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Negative value error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение NegativeValueError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(
            message=final_message,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.NEGATIVE_VALUE_ERROR
