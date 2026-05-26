from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


class BitrixContainerError(BaseAppException):
    """
    Базовое исключение для ошибок контейнера зависимостей Bitrix.

    Используется как родительский класс для всех ошибок, связанных с
    инициализацией и работой DI-контейнера Bitrix.
    """

    DEFAULT_MESSAGE = "Bitrix dependency container error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.BITRIX_CONTAINER_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует BitrixContainerError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class BitrixContainerInitError(BitrixContainerError):
    """Ошибка при инициализации контейнера зависимостей Bitrix."""

    DEFAULT_MESSAGE = "Bitrix dependency container initialization failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует BitrixContainerInitializationError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.BITRIX_CONTAINER_INIT_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class BitrixEntityClientInitError(BitrixContainerError):
    """
    Ошибка при создании клиента для работы с конкретной сущностью Bitrix.
    """

    DEFAULT_MESSAGE = "Bitrix entity client initialization failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует BitrixEntityClientInitError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.BITRIX_CONTAINER_ENTITY_INIT_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
