from typing import Any, cast

import httpx

from fastapi import status

from core.exceptions.bitrix24 import BitrixApiError, BitrixAuthError
from core.logger import logger


# ===== Константы и алиасы =====
DEFAULT_TIMEOUT = 10
AUTH_ERROR_STATUSES = (
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
)
JsonResponse = dict[str, Any]


class BitrixHTTPClient:
    """
    Асинхронный HTTP-клиент для взаимодействия с API Bitrix24.

    Обеспечивает методы GET и POST с автоматической обработкой ошибок,
    валидацией JSON и логированием.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Инициализирует клиент.

        Args:
            timeout: Таймаут HTTP-запросов в секундах.
        """
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._last_status_code: int = 0

    async def __aenter__(self) -> "BitrixHTTPClient":
        """Асинхронный вход в контекстный менеджер — создаёт HTTP-сессию."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        """Асинхронный выход — закрывает HTTP-сессию."""
        if self._client:
            await self._client.aclose()

    # ----- Публичные методы -----

    async def get(
        self, url: str, params: dict[str, Any] | None = None
    ) -> JsonResponse:
        """
        Выполняет GET-запрос к API Bitrix24.

        Args:
            url: Полный URL запроса.
            params: Query-параметры.

        Returns:
            Ответ сервера в виде JSON-объекта.

        Raises:
            BitrixAuthError: При ошибке аутентификации (401, 403).
            BitrixApiError: При других HTTP-ошибках, проблемах с сетью или
            JSON.
        """
        return await self._request("GET", url, params=params)

    async def post(
        self, url: str, payload: dict[str, Any] | None = None
    ) -> JsonResponse:
        """
        Выполняет POST-запрос к API Bitrix24.

        Args:
            url: Полный URL запроса.
            payload: Тело запроса (будет отправлено как JSON).

        Returns:
            Ответ сервера в виде JSON-объекта (дополнительно содержит поле
            'status_code').

        Raises:
            BitrixAuthError: При ошибке аутентификации (401, 403).
            BitrixApiError: При других HTTP-ошибках, проблемах с сетью или
            JSON.
        """
        response = await self._request("POST", url, json=payload)
        # Добавляем статус-код в тело ответа
        assert isinstance(response, dict)
        response["status_code"] = self._last_status_code
        return response

    # ----- Приватные методы ядра -----

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> JsonResponse:
        """
        Базовый метод для выполнения HTTP-запроса.

        Args:
            method: HTTP-метод ("GET" или "POST").
            url: URL запроса.
            params: Query-параметры (только для GET).
            json: JSON-тело (только для POST).

        Returns:
            Распарсенный JSON-ответ.

        Raises:
            BitrixAuthError: При ошибке аутентификации.
            BitrixApiError: При любых других ошибках.
        """
        # Нормализуем метод
        normalized_method = method.upper()
        if normalized_method not in ("GET", "POST"):
            raise BitrixApiError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_description=f"Unsupported HTTP method: {method}",
                message=f"Invalid method '{method}' for Bitrix24 API request",
            )

        # Проверяем, что клиент создан (если используется контекстный
        # менеджер)
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        try:
            if normalized_method == "GET":
                response = await self._client.get(url, params=params)
            else:  # normalized_method == "POST":
                response = await self._client.post(
                    url,
                    json=json,
                    headers={"Content-Type": "application/json"},
                )

            # Сохраняем статус-код для возможного добавления в ответ POST
            self._last_status_code = response.status_code

            # Обрабатываем некорректные статусы
            await self._raise_for_status(response)

            # Парсим и валидируем JSON
            return await self._parse_json_response(response)

        except httpx.RequestError as e:
            logger.error(f"Network error during {method} {url}: {e}")
            raise BitrixApiError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Unable to connect to Bitrix24",
            ) from e
        except (BitrixAuthError, BitrixApiError):
            # Пробрасываем уже обработанные ошибки дальше
            raise
        except Exception as e:
            # Любая непредвиденная ошибка (ValueError, TypeError и т.д.)
            logger.exception(f"Unexpected error in {method} {url}: {e}")
            raise BitrixApiError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal client error",
            ) from e

    async def _raise_for_status(self, response: httpx.Response) -> None:
        """
        Анализирует HTTP-статус ответа и возбуждает соответствующее
        исключение.

        Args:
            response: Объект ответа httpx.

        Raises:
            BitrixAuthError: Если статус 401 или 403.
            BitrixApiError: Если статус 4xx или 5xx (кроме авторизационных).
        """
        if 200 <= response.status_code < 300:
            return

        # Пытаемся извлечь тело ошибки в формате JSON (Bitrix24)
        try:
            error_body = response.json()
            error_description = error_body.get(
                "error_description", response.text
            )
            error = error_body.get("error", "HTTP_STATUS_ERROR")
        except Exception:  # noqa: BLE001
            error_description = response.text
            error = "HTTP_STATUS_ERROR"

        if response.status_code in AUTH_ERROR_STATUSES:
            logger.warning(
                f"Authentication error {response.status_code}: "
                f"{error_description}"
            )
            raise BitrixAuthError(
                error=error,
                error_description=error_description,
                message=(
                    f"Authentication failed with status "
                    f"{response.status_code}"
                ),
                status_code=response.status_code,
            )
        else:
            logger.error(
                f"API error {response.status_code}: {error_description}"
            )
            raise BitrixApiError(
                error=error,
                error_description=error_description,
                status_code=response.status_code,
                message=f"Bitrix API error: {response.text}",
            )

    @staticmethod
    async def _parse_json_response(response: httpx.Response) -> JsonResponse:
        """
        Парсит ответ в JSON и проверяет, что это объект (dict).

        Args:
            response: Объект ответа httpx.

        Returns:
            JSON-объект.

        Raises:
            BitrixApiError: Если ответ не является JSON-объектом.
        """
        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise BitrixApiError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message="Invalid JSON from Bitrix24",
            ) from e

        if not isinstance(data, dict):
            logger.error(f"Expected JSON object, got {type(data).__name__}")
            raise BitrixApiError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message="Response is not a JSON object",
            )
        return cast("JsonResponse", data)

    # async def _get(
    #     self, url: str, params: dict[str, Any] | None = None
    # ) -> JsonResponse:
    #     try:
    #         async with httpx.AsyncClient(timeout=self.timeout) as client:
    #             response = await client.get(url, params=params)
    #             # response.raise_for_status()
    #             json_data = response.json()
    #             if not isinstance(json_data, dict):
    #                 raise ValueError(
    #                     "Expected JSON object, got "
    #                     f"{type(json_data).__name__}"
    #                 )
    #             return cast("JsonResponse", json_data)
    #     except httpx.HTTPStatusError as e:
    #         detail = e.response.json().get("error_description", str(e))
    #         logger.error(f"HTTP error: {e.response.status_code}")
    #         raise BitrixAuthError(
    #             f"HTTP error {e.response.status_code}", detail=detail
    #         )
    #     except httpx.RequestError as e:
    #         logger.error(f"Network error: {e}")
    #         raise BitrixAuthError("Network error during token request")
    #     except ValueError as e:
    #         logger.error(f"Invalid JSON response: {e}")
    #         raise BitrixAuthError("Invalid response format from Bitrix24")
    #     except Exception as e:
    #         logger.error(f"Unexpected error: {e}")
    #         raise BitrixApiError(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             error_description="Unexpected error",
    #         )

    # async def _post(
    #     self, url: str, payload: dict[str, Any]
    # ) -> JsonResponse:
    #     try:
    #         async with httpx.AsyncClient(timeout=self.timeout) as client:
    #             response = await client.post(
    #                 url,
    #                 json=payload,
    #                 headers={"Content-Type": "application/json"},
    #             )
    #             # response.raise_for_status()
    #             json_data = response.json()
    #             if not isinstance(json_data, dict):
    #                 raise ValueError(
    #                     "Expected JSON object, got "
    #                     f"{type(json_data).__name__}"
    #                 )
    #             json_data["status_code"] = response.status_code
    #             return cast("JsonResponse", json_data)
    #     except httpx.HTTPStatusError as e:
    #         logger.error(
    #             f"API HTTP error {e.response.status_code}: "
    #             f"{e.response.text}"
    #         )
    #         raise BitrixApiError(
    #             status_code=e.response.status_code,
    #             error_description=f"Bitrix API error: {e.response.text}",
    #         )
    #     except httpx.RequestError as e:
    #         logger.error(f"Network error: {e}")
    #         raise BitrixApiError(
    #             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #             error_description="Unable to connect to Bitrix24",
    #         )
    #     except ValueError as e:
    #         logger.error(f"Invalid JSON response: {e}")
    #         raise BitrixApiError(
    #             status_code=status.HTTP_502_BAD_GATEWAY,
    #             error_description="Invalid response from Bitrix24",
    #         )
    #     except Exception as e:
    #         logger.error(f"Unexpected error: {e}")
    #         raise BitrixApiError(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             error_description="Unexpected error",
    #         )
