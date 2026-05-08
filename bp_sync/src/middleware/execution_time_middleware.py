import json
import time
import uuid

from typing import cast

from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import JSONResponse, Response

from core.logger import logger


class ExecutionTimeMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Middleware для измерения времени выполнения запроса и добавления его в
    JSON-ответ.

    Перехватывает каждый запрос, замеряет время его обработки. Если ответ
    имеет Content-Type 'application/json', считывает тело ответа, парсит его,
    добавляет поле 'execution_time' (в миллисекундах) и возвращает
    обновленный ответ.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Обрабатывает входящий запрос и исходящий ответ."""
        start_time = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Передаем управление следующему middleware или эндпоинту
        response = await call_next(request)

        execution_time = round((time.perf_counter() - start_time) * 1000.0, 4)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Execution-Time-Ms"] = str(execution_time)

        # Модифицируем только JSON-ответы
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            body_iterator = getattr(response, "body_iterator", None)
            if body_iterator is None:
                logger.warning(
                    "Response missing body_iterator, cannot modify JSON"
                )
                return response

            body = b""
            try:
                async for chunk in body_iterator:
                    # chunk должен быть bytes, используем cast для указания
                    # типа
                    body += cast("bytes", chunk)
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Error reading response body: %s", e, exc_info=True
                )
                return response

            try:
                # Пытаемся распарсить JSON для добавления метрики времени
                data = json.loads(body.decode())

                if isinstance(data, dict):
                    data["execution_time"] = execution_time
                    data["request_id"] = request_id
                    # Формируем новый ответ с обновленным телом.
                    # Удаляем Content-Length, так как длина изменилась.
                    headers = dict(response.headers)
                    headers.pop("content-length", None)

                    return JSONResponse(
                        content=data,
                        status_code=response.status_code,
                        headers=headers,
                        media_type=response.media_type,
                    )
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse JSON response for modification: %s", e
                )
            except UnicodeDecodeError as e:
                logger.error("Failed to decode response body to UTF-8: %s", e)
            except (ValueError, TypeError) as e:
                # Неожиданный формат данных (например, data не dict)
                logger.error(
                    "Unexpected data format in JSON response: %s",
                    e,
                    exc_info=True,
                )
            except Exception as e:  # noqa: BLE001
                # Логируем любые неожиданные ошибки при модификации
                logger.error(
                    "Unexpected error in ExecutionTimeMiddleware: %s",
                    e,
                    exc_info=True,
                )

            # Если не смогли модифицировать JSON, возвращаем исходное тело
            # как есть
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
