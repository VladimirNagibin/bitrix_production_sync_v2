from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar, cast

from fastapi import status

from core.exceptions.bitrix24 import BitrixApiError, BitrixAuthError
from core.logger import logger


# ===== Типы =====
T = TypeVar("T")
AsyncFunc = TypeVar(
    "AsyncFunc", bound=Callable[..., Coroutine[Any, Any, Any]]
)


def handle_bitrix_errors() -> Callable[[AsyncFunc], AsyncFunc]:
    """
    Декоратор для обработки ошибок при вызовах API Bitrix24.

    Перехватывает любые неожиданные исключения и преобразует их в
    BitrixApiError с HTTP-статусом 500 Internal Server Error.
    Ошибки аутентификации (BitrixAuthError) и предопределённые ошибки API
    (BitrixApiError) пробрасываются без изменений.

    Returns:
        Декоратор, оборачивающий асинхронную функцию.
    """

    def decorator(func: AsyncFunc) -> AsyncFunc:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except (BitrixAuthError, BitrixApiError):
                raise
            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                raise BitrixApiError(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=(
                        "Internal server error while calling Bitrix24 API: "
                        f"{e}"
                    ),
                ) from e

        return cast("AsyncFunc", wrapper)

    return decorator
