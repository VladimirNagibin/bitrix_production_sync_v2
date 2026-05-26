"""
Модуль исключений для работы с базой данных и каналами связи.

Содержит иерархию исключений, специфичных для операций с БД,
подключения, загрузки данных и обработки коммуникационных каналов.
Все сообщения исключений на английском, комментарии и docstrings на русском.
"""

from typing import Any

from fastapi import status

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения, связанные с сущностями =====
class EntityError(BaseAppException):
    """Базовое исключение для ошибок сущностей."""

    # Сообщение по умолчанию
    DEFAULT_MESSAGE = "Entity operation failed"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.ENTITY_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение EntityError.

        Args:
            error_code: Код ошибки (строка или перечисление ErrorCode)
            message: Пользовательское сообщение
            details: Дополнительные детали (словарь, строка и т.п.)
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class SchemaNotFoundError(EntityError):
    """
    Исключение, возникающее когда не удаётся определить класс Pydantic-схемы.
    """

    DEFAULT_MESSAGE = "Schema not found for the given entity type"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует SchemaNotFoundError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.SCHEMA_NOT_FOUND_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


# ===== Исключения, связанные с User сущностью =====
class UserEntityError(EntityError):
    """Базовое исключение для ошибок в моделях пользователей."""

    DEFAULT_MESSAGE = "User entity operation failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует UserEntityError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.USER_ENTITY_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class UserNotFoundError(UserEntityError):
    """Пользователь не найден."""

    DEFAULT_MESSAGE = "User not found"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует UserNotFoundError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code or status.HTTP_404_NOT_FOUND,
        )
        self.error_code = ErrorCode.USER_NOT_FOUND_ERROR
