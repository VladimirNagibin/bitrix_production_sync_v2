from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core import settings
from core.exceptions.app_token import (
    InvalidTokenTypeError,
    StorageConnectionError,
    TokenDeleteError,
    TokenSaveError,
)
from core.logger import logger
from db.redis import get_redis

from .token_cipher import TokenCipher, get_token_cipher


# ===== Константы =====
TokenType = Literal["refresh_token", "access_token"]
DEFAULT_REFRESH_TTL = 15_552_000  # 180 дней в секундах
VALID_TOKEN_TYPES: tuple[str, ...] = ("refresh_token", "access_token")


class TokenStorage:
    """
    Хранилище токенов с шифрованием на базе Redis.

    Обеспечивает асинхронное сохранение, получение и удаление токенов
    с автоматическим шифрованием/дешифрованием.
    """

    def __init__(self, redis: Redis, token_cipher: TokenCipher) -> None:
        self._redis = redis
        self._token_cipher = token_cipher

    async def save_token(
        self,
        token: str,
        token_type: TokenType,
        user_id: str = str(settings.bitrix24.service_user_id),
        provider: str = settings.bitrix24.default_provider,
        expire_seconds: int = DEFAULT_REFRESH_TTL,
    ) -> None:
        """
        Сохраняет токен в Redis с шифрованием и TTL.

        Args:
            token: Исходный токен (строка).
            token_type: Тип токена ("refresh_token" или "access_token").
            user_id: Идентификатор пользователя.
            provider: Провайдер авторизации.
            expire_seconds: Время жизни в секундах.

        Raises:
            InvalidTokenTypeError: Если передан некорректный тип токена.
            TokenSaveError: При ошибке шифрования или сохранения.
            StorageConnectionError: При ошибке соединения с Redis.
        """
        self._validate_token_type(token_type)
        self._validate_token_not_empty(token)
        self._validate_user_id(user_id)

        key = self._build_key(token_type, user_id, provider)
        ttl = self._normalize_ttl(expire_seconds)

        try:
            encrypted_token = await self._token_cipher.encrypt(token)
            await self._redis.set(name=key, value=encrypted_token, ex=ttl)
            logger.debug(f"Token saved for {key}, TTL: {ttl}s")
        except (StorageConnectionError, TokenSaveError):
            # Пробрасываем уже известные исключения дальше
            raise
        except RedisError as e:
            logger.error(f"Redis save error for {key}: {e}")
            raise StorageConnectionError(
                message="Token storage unavailable"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected save error for {key}: {e}")
            raise TokenSaveError(message="Token save operation failed") from e

    async def get_token(
        self,
        token_type: TokenType,
        user_id: str = str(settings.bitrix24.service_user_id),
        provider: str = settings.bitrix24.default_provider,
    ) -> str | None:
        """
        Получает и расшифровывает токен из хранилища.

        Args:
            token_type: Тип токена ("refresh_token" или "access_token").
            user_id: Идентификатор пользователя.
            provider: Провайдер авторизации.

        Returns:
            Расшифрованный токен или None, если токен не найден.

        Raises:
            InvalidTokenTypeError: Если передан некорректный тип токена.
            StorageConnectionError: При ошибке соединения с Redis.
        """
        self._validate_token_type(token_type)

        key = self._build_key(token_type, user_id, provider)

        try:
            encrypted_token = await self._redis.get(key)
            if encrypted_token is None:
                logger.debug(f"Token not found for {key}")
                return None

            decrypted = await self._token_cipher.decrypt(encrypted_token)
        except RedisError as e:
            logger.error(f"Redis get error for {key}: {e}")
            raise StorageConnectionError(
                message="Token retrieval failed"
            ) from e
        except Exception as e:  # noqa: BLE001
            # При любых других ошибках (включая ошибки дешифрования) логируем
            # и возвращаем None
            logger.error(f"Unexpected get error for {key}: {e}")
            return None
        else:
            return decrypted

    async def delete_token(
        self,
        token_type: TokenType,
        user_id: str = str(settings.bitrix24.service_user_id),
        provider: str = settings.bitrix24.default_provider,
    ) -> bool:
        """
        Удаляет токен из хранилища.

        Args:
            token_type: Тип токена ("refresh_token" или "access_token").
            user_id: Идентификатор пользователя.
            provider: Провайдер авторизации.

        Returns:
            True, если токен был удалён, иначе False.

        Raises:
            InvalidTokenTypeError: Если передан некорректный тип токена.
            StorageConnectionError: При ошибке соединения с Redis.
            TokenDeleteError: При неожиданной ошибке удаления.
        """
        self._validate_token_type(token_type)

        key = self._build_key(token_type, user_id, provider)

        try:
            deleted_count = await self._redis.delete(key)
            success = deleted_count > 0
            if success:
                logger.debug(f"Token deleted for {key}")
            else:
                logger.debug(f"Token not found for deletion: {key}")
            return bool(success)
        except RedisError as e:
            logger.error(f"Redis delete error for {key}: {e}")
            raise StorageConnectionError(
                message="Token deletion failed"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected delete error for {key}: {e}")
            raise TokenDeleteError(
                message="Token delete operation failed"
            ) from e

    # ----- Вспомогательные методы -----
    def _build_key(self, token_type: str, user_id: str, provider: str) -> str:
        """
        Формирует ключ Redis из компонентов.

        Returns:
            Ключ в формате "{token_type}:{user_id}:{provider}".
        """
        return f"{token_type}:{user_id}:{provider}"

    @staticmethod
    def _validate_token_type(token_type: TokenType) -> None:
        """Проверяет, что тип токена допустим."""
        if token_type not in VALID_TOKEN_TYPES:
            raise InvalidTokenTypeError(
                message=(
                    f"Invalid token type: {token_type}. "
                    f"Expected one of {VALID_TOKEN_TYPES}"
                )
            )

    @staticmethod
    def _validate_token_not_empty(token: str) -> None:
        """Проверяет, что токен не пустой."""
        if not token or not token.strip():
            raise TokenSaveError(message="Cannot save empty token")

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        """Проверяет, что user_id не пустой."""
        if not user_id:
            raise TokenSaveError(message="User ID cannot be empty")

    @staticmethod
    def _normalize_ttl(expire_seconds: int) -> int:
        """
        Нормализует TTL, гарантируя положительное значение.

        Returns:
            TTL не менее 1 секунды (минимальное допустимое значение).
        """
        return max(1, expire_seconds)


# ===== Фабрика (Dependency Injection) =====
@lru_cache(maxsize=1)
def get_token_storage(
    redis: Annotated[Redis, Depends(get_redis)],
    token_cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> TokenStorage:
    """
    Фабрика для получения экземпляра TokenStorage (синглтон).

    Использует зависимости Redis и TokenCipher, внедряемые через
    FastAPI Depends.

    Returns:
        Настроенный экземпляр TokenStorage.

    Raises:
        StorageConnectionError: Если Redis клиент недоступен.
    """
    return TokenStorage(redis, token_cipher)
