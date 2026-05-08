from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """
    Базовая модель ответа API с общими полями.
    """

    details: dict[str, Any] | None = Field(
        default=None, description="Дополнительные детали ответа"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Время ответа сервера в формате ISO 8601",
    )
    execution_time: float | None = Field(
        default=None, description="Время выполнения запроса в миллисекундах"
    )
    request_id: str | None = Field(
        default=None,
        description="Уникальный идентификатор запроса для трассировки",
    )


class SuccessResponse(BaseResponse):
    """
    Модель для успешного ответа API.
    """

    success: bool = Field(
        default=True,
        description="Флаг успешного выполнения операции",
    )
    message: str = Field(..., description="Сообщение об успешном выполнении")
    data: Any | None = Field(
        default=None, description="Основные данные ответа (payload)"
    )


class ErrorResponse(BaseResponse):
    """
    Модель для ответа API с ошибкой.
    """

    success: bool = Field(
        default=False,
        description="Флаг успешного выполнения операции",
    )
    error_code: str = Field(
        ...,
        description=(
            "Код ошибки для программной обработки (например, 'NOT_FOUND')"
        ),
    )
    message: str = Field(
        ..., description="Описание ошибки, понятное пользователю"
    )
    data: Any | None = Field(
        default=None, description="Дополнительные данные об ошибке"
    )
