from typing import Any
from urllib.parse import urlencode

from fastapi import status

from core import settings
from core.exceptions.bitrix24 import BitrixApiError, BitrixAuthError
from core.logger import logger
from services.token_services.token_storage import TokenStorage

from .bitrix_http_client import DEFAULT_TIMEOUT, BitrixHTTPClient


# ===== Константы =====
OAUTH_ENDPOINT = "/oauth/authorize/"
TOKEN_ENDPOINT = "/oauth/token/"  # noqa: S105
DEFAULT_TTL_ACCESS_TOKEN = 3600


class BitrixOAuthClient(BitrixHTTPClient):
    """
    OAuth-клиент для авторизации и управления токенами Bitrix24.

    Наследует HTTP-клиент, добавляет специфическую логику:
    - получение access_token по коду авторизации
    - обновление access_token через refresh_token
    - хранение токенов в Redis через TokenStorage
    - генерация URL для перенаправления пользователя
    """

    def __init__(
        self,
        token_storage: TokenStorage,
        portal_domain: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Инициализирует OAuth-клиент Bitrix24.

        Args:
            portal_domain: Базовый URL портала (например, https://xxx.bitrix24.ru).
            client_id: ID приложения Bitrix24.
            client_secret: Секретный ключ приложения.
            redirect_uri: URI для перенаправления после авторизации.
            token_storage: Хранилище токенов.
            timeout: Таймаут HTTP-запросов.
        """
        super().__init__(timeout)
        self.portal_domain = (
            portal_domain.rstrip("/")
            if portal_domain
            else str(settings.bitrix24.portal_url).rstrip("/")
        )
        self.client_id = client_id or settings.bitrix24.client_id
        self.client_secret = client_secret or settings.bitrix24.client_secret
        self.redirect_uri = redirect_uri or settings.bitrix24.redirect_uri
        self.token_url = f"{self.portal_domain}{TOKEN_ENDPOINT}"
        self.token_storage = token_storage

    async def get_valid_token(self) -> str:
        """
        Возвращает действующий access_token.

        Сначала пытается получить access_token из хранилища.
        Если его нет или он истёк, пытается обновить через refresh_token.
        Если ни одного токена нет – выбрасывает исключение с предложением
        пройти авторизацию заново.

        Returns:
            Действующий access_token.

        Raises:
            BitrixAuthError: Если нет ни access, ни refresh токена,
                             или refresh не удался.
        """
        # Пытаемся взять access_token из хранилища
        if access_token := await self.token_storage.get_token("access_token"):
            return access_token

        # Если access нет, пробуем обновить через refresh
        if refresh_token := await self.token_storage.get_token(
            "refresh_token"
        ):
            return await self._refresh_access_token(refresh_token)

        # Если нет никаких токенов – требуется полная переавторизация
        logger.warning(
            "No valid tokens available, re-authentication required."
        )
        raise BitrixAuthError(
            error="AUTHENTICATION_REQUIRED",
            message="No valid tokens available",
            error_description=(
                f"Please re-authorize at: {self.get_auth_url()}"
            ),
            details={"auth_url": self.get_auth_url()},
        )

    async def _refresh_access_token(self, refresh_token: str) -> str:
        """
        Обновляет access_token с помощью refresh_token.

        Args:
            refresh_token: Действующий refresh_token.

        Returns:
            Новый access_token.

        Raises:
            BitrixAuthError: Если refresh_token недействителен.
            BitrixApiError: При проблемах сети.
        """
        form_data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        return await self._exchange_token(form_data, "refresh")

    async def fetch_token(self, auth_code: str) -> str:
        """
        Обменивает авторизационный код на пару токенов (access + refresh).

        Args:
            auth_code: Временный код, полученный после авторизации
            пользователя.

        Returns:
            Полученный access_token.

        Raises:
            BitrixAuthError: Если код недействителен или сервер вернул ошибку.
            BitrixApiError: При проблемах сети или некорректном ответе.
        """
        form_data: dict[str, Any] = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": auth_code,
        }
        return await self._exchange_token(form_data, "authorization")

    async def _exchange_token(
        self, form_data: dict[str, str], operation: str
    ) -> str:
        """
        Выполняет POST-запрос к token endpoint с данными в формате
        form-urlencoded.
        Сохраняет полученные токены и возвращает access_token.

        Args:
            form_data: Параметры запроса (grant_type, client_id, и т.д.).
            operation: Название операции для логирования
            ("authorization" или "refresh").

        Returns:
            Полученный access_token.

        Raises:
            BitrixAuthError: Если ответ содержит ошибку OAuth.
            BitrixApiError: При проблемах с запросом или парсингом ответа.
        """
        # token_data = await self._post(self.token_url, payload=params)
        token_data = await self.get(self.token_url, params=form_data)
        self._validate_token_response(token_data)
        access_token = self._extract_access_token(token_data)
        await self._save_tokens(token_data)

        logger.info(
            f"Token {operation} successful",
            extra={"grant_type": form_data["grant_type"]},
        )
        return access_token

    def _validate_token_response(self, token_data: dict[str, str]) -> None:
        """
        Проверяет ответ токенного эндпоинта на наличие ошибок.

        Args:
            token_data: JSON-ответ от Bitrix24.

        Raises:
            BitrixAuthError: Если поле 'error' присутствует.
        """
        if "error" in token_data:
            error_msg = token_data.get(
                "error_description", "Unknown OAuth error"
            )
            error_code = token_data.get("error", "OAUTH_TOKEN_ERROR")
            logger.error(f"Bitrix OAuth error [{error_code}]: {error_msg}")
            raise BitrixAuthError(
                error=error_code,
                error_description=error_msg,
                message="OAuth token exchange failed",
                details={"auth_url": self.get_auth_url()},
            )

    def _extract_access_token(self, token_data: dict[str, str]) -> str:
        """
        Извлекает access_token из ответа и проверяет его тип.

        Args:
            token_data: JSON-ответ с токенами.

        Returns:
            Значение access_token.

        Raises:
            BitrixAuthError: Если поле отсутствует или не является строкой.
        """
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            logger.error(
                f"Invalid access_token: expected non-empty string, got "
                f"{type(access_token).__name__}"
            )
            raise BitrixAuthError(
                error_description=(
                    "Missing or invalid access_token in response"
                ),
                message="Invalid token response format",
                details={"auth_url": self.get_auth_url()},
            )
        return access_token

    async def _save_tokens(self, token_data: dict[str, str]) -> None:
        """
        Сохраняет access_token и refresh_token в хранилище.

        Args:
            token_data: Ответ с токенами (должен содержать access_token,
                        refresh_token и expires_in).

        Raises:
            BitrixApiError: Если не удалось сохранить токены.
        """
        try:
            # Сохраняем access_token с TTL из expires_in
            expires_in = int(
                token_data.get("expires_in", DEFAULT_TTL_ACCESS_TOKEN)
            )
            await self.token_storage.save_token(
                token_data["access_token"],
                "access_token",
                expire_seconds=expires_in,
            )

            # Сохраняем refresh_token (долгоживущий, TTL по умолчанию)
            await self.token_storage.save_token(
                token_data["refresh_token"],
                "refresh_token",
            )
            logger.debug("Tokens saved to storage successfully")
        except KeyError as e:
            logger.error(f"Missing required field in token response: {e}")
            raise BitrixAuthError(
                error_description=f"Token response missing field: {e}",
                message="Incomplete token data",
                details={"auth_url": self.get_auth_url()},
            ) from e
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            raise BitrixApiError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Token storage failure",
            ) from e

    def get_auth_url(self) -> str:
        """
        Генерирует URL для авторизации пользователя в Bitrix24.

        Returns:
            URL для перенаправления пользователя (GET-запрос).
        """
        params: dict[str, Any] = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        return f"{self.portal_domain}{OAUTH_ENDPOINT}?{urlencode(params)}"
