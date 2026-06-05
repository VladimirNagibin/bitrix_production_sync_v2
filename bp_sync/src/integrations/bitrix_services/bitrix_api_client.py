from typing import Any
from urllib.parse import urljoin

from fastapi import status

from core.exceptions.bitrix24 import BitrixApiError, BitrixAuthError
from core.logger import logger

from .bitrix_http_client import DEFAULT_TIMEOUT, BitrixHTTPClient
from .bitrix_oauth_client import BitrixOAuthClient


# ===== Константы =====
MAX_RETRIES = 2
REST_API_BASE = "/rest/"
TOKEN_ERROR_CODES = {"expired_token", "invalid_token"}


class BitrixAPIClient(BitrixHTTPClient):
    """
    Клиент для работы с REST API Bitrix24.

    Обеспечивает вызов API-методов с автоматическим обновлением токена
    и повторными попытками при ошибках аутентификации.
    """

    def __init__(
        self,
        oauth_client: BitrixOAuthClient,
        api_base_url: str = "",
        max_retries: int = MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Инициализирует API-клиент Bitrix24.

        Args:
            oauth_client: OAuth-клиент для управления токенами.
            api_base_url: Базовый URL API (если не указан, строится из
                          portal_domain).
            max_retries: Максимальное количество повторных попыток при
                         ошибках токена.
            timeout: Таймаут HTTP-запросов.
        """
        super().__init__(timeout)
        self.oauth_client = oauth_client
        self.api_base_url = (
            api_base_url or f"{oauth_client.portal_domain}{REST_API_BASE}"
        )
        self.max_retries = max_retries

    async def call_api(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Выполняет вызов REST API Bitrix24.

        Args:
            method: Название метода (например, 'crm.deal.list').
            params: Параметры запроса (будут объединены с токеном).

        Returns:
            Ответ API в виде словаря (содержит поле 'result').

        Raises:
            BitrixAuthError: При ошибке аутентификации после всех попыток.
            BitrixApiError: При ошибке API или неверном формате ответа.
        """
        for attempt in range(self.max_retries + 1):
            try:
                access_token = await self.oauth_client.get_valid_token()
                url = urljoin(self.api_base_url, method)
                payload = {"auth": access_token}
                if params:
                    payload.update(params)
                response = await self.post(url, payload)
                if "error" in response:
                    await self._handle_api_error(response, attempt)
                    continue
                self._ensure_result_in_response(response, method, params)
            except BitrixAuthError as e:
                logger.warning(
                    "Authentication error on attempt "
                    f"{attempt + 1}/{self.max_retries + 1}: {e}"
                )
                if attempt >= self.max_retries:
                    logger.error("Max retries exceeded for token refresh.")
                    raise
                continue
            except BitrixApiError:
                raise
            else:
                return response
        logger.error(
            f"Token refresh failed after retries. {method}: {params}"
        )
        raise BitrixAuthError(message="Token refresh failed after retries")

    async def _handle_api_error(
        self, response: dict[str, Any], attempt: int
    ) -> None:
        """
        Обрабатывает ошибку, возвращённую API Bitrix24.

        Args:
            response: Ответ API, содержащий поле 'error'.
            attempt: Номер текущей попытки (начиная с 0).

        Raises:
            BitrixAuthError: Если ошибка связана с токеном и возможно
                             повторение.
            BitrixApiError: Для всех остальных ошибок API.
        """
        error_code = response.get("error", "unknown_error")
        error_desc = response.get(
            "error_description", "Unknown Bitrix API error"
        )
        status_code = response.get("status_code", status.HTTP_400_BAD_REQUEST)

        if error_code in TOKEN_ERROR_CODES:
            logger.warning(
                f"Token error '{error_code}' detected. "
                "Invalidating token and retrying "
                f"(attempt {attempt + 1}/{self.max_retries + 1})"
            )
            await self._invalidate_current_token()
            raise BitrixAuthError(
                error=error_code,
                error_description=error_desc,
                message="Token invalid or expired",
                status_code=status_code,
            )
        logger.error(f"Bitrix API error [{error_code}]: {error_desc}")
        raise BitrixApiError(
            status_code=status_code,
            error=error_code,
            error_description=error_desc,
        )

    async def _invalidate_current_token(self) -> None:
        """
        Инвалидирует текущий access_token в хранилище.
        """
        try:
            await self.oauth_client.token_storage.delete_token("access_token")
            logger.debug("Access token invalidated successfully.")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to invalidate access token: {e}")

    def _ensure_result_in_response(
        self,
        response: dict[str, Any],
        method: str,
        params: dict[str, Any] | None,
    ) -> None:
        """Проверяет наличие поля 'result' в ответе API."""
        if "result" not in response:
            logger.error(
                f"API response missing 'result' field. "
                f"Method: {method}, Params: {params}, Response: {response}"
            )
            raise BitrixApiError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Response has no 'result' field.",
            )
