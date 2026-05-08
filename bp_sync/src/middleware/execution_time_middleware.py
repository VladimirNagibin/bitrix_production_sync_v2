import json
import time

from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import JSONResponse, Response

from core.logger import logger


class ExecutionTimeMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)

        # Работаем только с JSON-ответами
        if response.headers.get("content-type", "").startswith(
            "application/json"
        ):
            # Читаем всё тело ответа
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                data = json.loads(body.decode())
                if isinstance(data, dict):
                    data["execution_time"] = (
                        time.perf_counter() - start_time
                    ) * 1000.0

                    # Удаляем старый заголовок Content-Length,
                    # чтобы избежать конфликта
                    headers = dict(response.headers)
                    headers.pop("content-length", None)

                    return JSONResponse(
                        content=data,
                        status_code=response.status_code,
                        headers=headers,
                        media_type=response.media_type,
                    )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(
                    "Failed to parse JSON response: %s", e, exc_info=True
                )
                # Если не удалось распарсить JSON – возвращаем неизменное тело

            # Возвращаем исходное тело (без изменения) как обычный Response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
