from typing import Any

from .enums import ErrorCode


class BaseAppException(Exception):
    """Базовое исключение для всех ошибок приложения."""

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.error_code = str(error_code)
        self.message = message or self.__class__.__name__
        self.details = details
        super().__init__(self.message)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} code='{self.error_code}' "
            f"message='{self.message}'>"
        )
