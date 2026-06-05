import asyncio

from collections.abc import AsyncGenerator, Callable
from typing import Any, TypeVar, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from core import settings
from core.exceptions.app_token import (
    CipherConfigurationError,
    TokenStorageInitError,
)
from core.exceptions.base import BaseAppException
from core.exceptions.bitrix24 import BitrixApiError, BitrixAuthError
from core.exceptions.bitrix24_container import (
    BitrixContainerInitError,
    BitrixEntityClientInitError,
)
from core.exceptions.redis import RedisManagerConnectionError
from core.logger import logger
from db.redis import get_redis as get_redis_client
from integrations.bitrix_services.base_bitrix_client import (
    BaseBitrixEntityClient,
)
from integrations.bitrix_services.bitrix_api_client import BitrixAPIClient
from integrations.bitrix_services.bitrix_oauth_client import BitrixOAuthClient
from schemas.base_schemas import CommonFieldMixin
from services.token_services.token_cipher import TokenCipher
from services.token_services.token_storage import TokenStorage


# ===== Типы =====
SchemaTypeCreate = TypeVar("SchemaTypeCreate", bound=CommonFieldMixin)
SchemaTypeUpdate = TypeVar("SchemaTypeUpdate", bound=CommonFieldMixin)
# T = TypeVar("T", bound=BaseBitrixEntityClient[Any, Any])

# ===== Константы =====
_LOG_INITIALIZING = "Initializing dependency container"
_LOG_INIT_SUCCESS = "Dependency container initialized successfully"
_LOG_INIT_FAILED = "Failed to initialize dependency container: {}"
_LOG_REDIS_CREATE = "Creating Redis client"
_LOG_REDIS_CONNECTED = "Redis client initialized and connected"
_LOG_REDIS_FAILED = "Failed to initialize Redis client: {}"
_LOG_CIPHER_CREATE = "Creating token cipher"
_LOG_CIPHER_FAILED = "Failed to initialize token cipher: {}"
_LOG_STORAGE_CREATE = "Creating token storage"
_LOG_STORAGE_FAILED = "Failed to initialize token storage: {}"
_LOG_OAUTH_CREATE = "Creating OAuth client"
_LOG_OAUTH_FAILED = "Failed to creating OAuth client: {}"
_LOG_API_CREATE = "Creating API client"
_LOG_API_FAILED = "Failed to creating API client: {}"
_LOG_ENTITY_CREATE = "Creating entity client: {}"
_LOG_ENTITY_FAILED = "Failed to creating entity client: {}"
_LOG_SHUTDOWN = "Shutting down dependency container"


class DependencyBitrixContainer:
    """
    Контейнер зависимостей для управления жизненным циклом сервисов.

    Реализует ленивую инициализацию синглтонов с потокобезопасностью.
    Все зависимости создаются один раз и переиспользуются.
    """

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._token_cipher: TokenCipher | None = None
        self._token_storage: TokenStorage | None = None
        self._oauth_client: BitrixOAuthClient | None = None
        self._api_client: BitrixAPIClient | None = None
        self._entity_clients: dict[
            type[BaseBitrixEntityClient[Any, Any]],
            BaseBitrixEntityClient[Any, Any],
        ] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Принудительная инициализация контейнера (вызывается при старте)."""
        await self._ensure_initialized()

    async def _ensure_initialized(self) -> None:
        """
        Гарантирует, что контейнер инициализирован.
        Использует блокировку для предотвращения гонок.
        """
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            await self._initialize()

    async def _initialize(self) -> None:
        """
        Выполняет фактическую инициализацию контейнера.
        Создаёт базовые зависимости, необходимые для работы.
        """
        if self._initialized:
            return

        logger.info(_LOG_INITIALIZING)

        try:
            # Предварительная загрузка основных зависимостей
            await self._get_redis_internal()
            await self._get_api_client_internal()
            self._initialized = True
            logger.info(_LOG_INIT_SUCCESS)
        except BaseAppException as e:
            logger.error(_LOG_INIT_FAILED.format(e))
            raise
        except Exception as e:
            logger.error(_LOG_INIT_FAILED.format(e))
            raise BitrixContainerInitError(
                message=f"Unexpected error: {e}"
            ) from e

    # ----- Публичные методы получения зависимостей -----

    async def get_redis(self) -> Redis:
        """
        Возвращает клиент Redis (синглтон).

        Returns:
            Экземпляр Redis.

        Raises:
            RedisManagerConnectionError: При ошибке подключения к Redis.
        """
        await self._ensure_initialized()
        return await self._get_redis_internal()

    async def get_token_cipher(self) -> TokenCipher:
        """
        Возвращает шифровальщик токенов (синглтон).

        Returns:
            Экземпляр TokenCipher.

        Raises:
            CipherConfigurationError: При ошибке конфигурации шифрования.
        """
        await self._ensure_initialized()
        return await self._get_token_cipher_internal()

    async def get_token_storage(self) -> TokenStorage:
        """
        Возвращает хранилище токенов (синглтон).

        Returns:
            Экземпляр TokenStorage.
        """
        await self._ensure_initialized()
        return await self._get_token_storage_internal()

    async def get_oauth_client(self) -> BitrixOAuthClient:
        """
        Возвращает OAuth клиент Bitrix24 (синглтон).

        Returns:
            Экземпляр BitrixOAuthClient.
        """
        await self._ensure_initialized()
        return await self._get_oauth_client_internal()

    async def get_api_client(self) -> BitrixAPIClient:
        """
        Возвращает API клиент Bitrix24 (синглтон).

        Returns:
            Экземпляр BitrixAPIClient.
        """
        await self._ensure_initialized()
        return await self._get_api_client_internal()

    async def get_entity_client[T: BaseBitrixEntityClient[Any, Any]](
        self, entity_class: type[T]
    ) -> T:
        """
        Возвращает клиент для работы с сущностью Bitrix24.

        Args:
            entity_class: Класс клиента сущности (наследник
                          BaseBitrixEntityClient).
        Returns:
            Экземпляр клиента сущности.

        Raises:
            TypeError: Если entity_class не является подклассом
                       BaseBitrixEntityClient.
        """
        await self._ensure_initialized()

        if not issubclass(entity_class, BaseBitrixEntityClient):  # pyright: ignore[unnecessary-issubclass]
            error_message = (
                "entity_class must be a subclass of BaseBitrixEntityClient, "
                f"got {entity_class}"
            )
            raise BitrixEntityClientInitError(message=error_message)

        if entity_class not in self._entity_clients:
            async with self._lock:
                if entity_class not in self._entity_clients:
                    try:
                        api_client = await self._get_api_client_internal()
                        logger.debug(
                            _LOG_ENTITY_CREATE.format(entity_class.__name__)
                        )
                        self._entity_clients[entity_class] = entity_class(
                            api_client
                        )
                    except BaseAppException as e:
                        logger.error(
                            _LOG_ENTITY_FAILED.format(
                                f"{entity_class.__name__} :{e}"
                            )
                        )
                        raise
                    except Exception as e:
                        logger.error(
                            _LOG_ENTITY_FAILED.format(
                                f"{entity_class.__name__} :{e}"
                            )
                        )
                        raise BitrixEntityClientInitError(
                            message=f"Unexpected error: {e}"
                        ) from e
        return cast("T", self._entity_clients[entity_class])

    # ----- Внутренние методы инициализации (без повторной проверки) -----

    async def _get_redis_internal(self) -> Redis:
        """
        Внутренний метод создания Redis-клиента (без проверки инициализации).
        Возвращает клиент Redis (синглтон).

        Returns:
            Экземпляр Redis.

        Raises:
            RedisManagerConnectionError: При ошибке подключения к Redis.
        """
        if self._redis is None:
            logger.debug(_LOG_REDIS_CREATE)
            try:
                self._redis = await get_redis_client()
                await cast("Any", self._redis).ping()
                logger.debug(_LOG_REDIS_CONNECTED)
            except BaseAppException as e:
                logger.error(_LOG_REDIS_FAILED.format(e))
                raise
            except RedisError as e:
                error_message = _LOG_REDIS_FAILED.format(e)
                logger.error(error_message)
                raise RedisManagerConnectionError(
                    message=error_message
                ) from e
            except Exception as e:
                logger.error(_LOG_REDIS_FAILED.format(e))
                raise RedisManagerConnectionError(
                    message=f"Unexpected error: {e}"
                ) from e
        return self._redis

    async def _get_token_cipher_internal(self) -> TokenCipher:
        """
        Внутренний метод создания шифровальщика (без проверки инициализации).
        Возвращает шифровальщик токенов (синглтон).

        Returns:
            Экземпляр TokenCipher.

        Raises:
            CipherConfigurationError: При ошибке конфигурации шифрования.
        """
        if self._token_cipher is None:
            logger.debug(_LOG_CIPHER_CREATE)
            try:
                self._token_cipher = TokenCipher(settings.encryption_key)
            except BaseAppException as e:
                logger.error(_LOG_CIPHER_FAILED.format(e))
                raise
            except Exception as e:
                logger.error(_LOG_CIPHER_FAILED.format(e))
                raise CipherConfigurationError(
                    message=f"Unexpected error: {e}"
                ) from e
        return self._token_cipher

    async def _get_token_storage_internal(self) -> TokenStorage:
        """
        Внутренний метод создания хранилища токенов.
        Возвращает хранилище токенов (синглтон).

        Returns:
            Экземпляр TokenStorage.
        """
        if self._token_storage is None:
            try:
                redis = await self._get_redis_internal()
                cipher = await self._get_token_cipher_internal()
                logger.debug(_LOG_STORAGE_CREATE)
                self._token_storage = TokenStorage(redis, cipher)
            except BaseAppException as e:
                logger.error(_LOG_STORAGE_FAILED.format(e))
                raise
            except Exception as e:
                logger.error(_LOG_STORAGE_FAILED.format(e))
                raise TokenStorageInitError(
                    message=f"Unexpected error: {e}"
                ) from e
        return self._token_storage

    async def _get_oauth_client_internal(self) -> BitrixOAuthClient:
        """
        Внутренний метод создания OAuth-клиента.
        Возвращает OAuth клиент Bitrix24 (синглтон).

        Returns:
            Экземпляр BitrixOAuthClient.
        """
        if self._oauth_client is None:
            try:
                token_storage = await self._get_token_storage_internal()
                logger.debug(_LOG_OAUTH_CREATE)
                self._oauth_client = BitrixOAuthClient(
                    token_storage=token_storage
                )
            except BaseAppException as e:
                logger.error(_LOG_OAUTH_FAILED.format(e))
                raise
            except Exception as e:
                logger.error(_LOG_OAUTH_FAILED.format(e))
                raise BitrixAuthError(message=f"Unexpected error: {e}") from e
        return self._oauth_client

    async def _get_api_client_internal(self) -> BitrixAPIClient:
        """
        Внутренний метод создания API-клиента.
        Возвращает API клиент Bitrix24 (синглтон).

        Returns:
            Экземпляр BitrixAPIClient.
        """
        if self._api_client is None:
            try:
                oauth_client = await self._get_oauth_client_internal()
                logger.debug(_LOG_API_CREATE)
                self._api_client = BitrixAPIClient(oauth_client=oauth_client)
            except BaseAppException as e:
                logger.error(_LOG_API_FAILED.format(e))
                raise
            except Exception as e:
                logger.error(_LOG_API_FAILED.format(e))
                raise BitrixApiError(message=f"Unexpected error: {e}") from e
        return self._api_client

    async def shutdown(self) -> None:
        """
        Корректно завершает работу контейнера, освобождая ресурсы.
        """
        logger.info(_LOG_SHUTDOWN)
        self._token_cipher = None
        self._token_storage = None
        self._oauth_client = None
        self._api_client = None
        self._entity_clients.clear()
        self._initialized = False
        # Redis клиент не закрываем здесь, так как он управляется внешним
        # контекстом, он будет закрыт отдельно при завершении приложения


# ===== Глобальный экземпляр контейнера =====
_dependency_container: DependencyBitrixContainer = DependencyBitrixContainer()


# ===== Функции для получения зависимостей (FastAPI) =====
async def get_dependency_container() -> AsyncGenerator[
    DependencyBitrixContainer
]:
    """
    Зависимость для получения глобального контейнера зависимостей.

    Используется в FastAPI для внедрения контейнера в обработчики.

    Yields:
        Экземпляр DependencyBitrixContainer.
    """
    try:
        yield _dependency_container
    finally:
        # Контейнер не закрывается здесь, так как он глобальный
        # Закрытие происходит при остановке приложения
        pass


async def get_redis() -> AsyncGenerator[Redis]:
    """
    Зависимость для получения клиента Redis.

    Yields:
        Экземпляр Redis.
    """
    redis = await _dependency_container.get_redis()
    try:
        yield redis
    finally:
        # Redis соединение управляется контейнером
        pass


async def get_token_cipher() -> AsyncGenerator[TokenCipher]:
    """
    Зависимость для получения шифровальщика токенов.

    Yields:
        Экземпляр TokenCipher.
    """
    cipher = await _dependency_container.get_token_cipher()
    yield cipher


async def get_token_storage() -> AsyncGenerator[TokenStorage]:
    """
    Зависимость для получения хранилища токенов.

    Yields:
        Экземпляр TokenStorage.
    """
    storage = await _dependency_container.get_token_storage()
    yield storage


async def get_oauth_client() -> AsyncGenerator[BitrixOAuthClient]:
    """
    Зависимость для получения OAuth клиента Bitrix24.

    Yields:
        Экземпляр BitrixOAuthClient.
    """
    oauth_client = await _dependency_container.get_oauth_client()
    yield oauth_client


async def get_api_client() -> AsyncGenerator[BitrixAPIClient]:
    """
    Зависимость для получения API клиента Bitrix24.

    Yields:
        Экземпляр BitrixAPIClient.
    """
    api_client = await _dependency_container.get_api_client()
    yield api_client


def provide_entity_client[T: BaseBitrixEntityClient[Any, Any]](
    entity_class: type[T],
) -> Callable[[], AsyncGenerator[T]]:
    """
    Фабрика для создания зависимости клиента сущности Bitrix24.

    Args:
        entity_class: Класс клиента сущности.

    Returns:
        Асинхронный генератор, возвращающий экземпляр клиента.
    """

    async def _get_entity_client() -> AsyncGenerator[T]:
        client = await _dependency_container.get_entity_client(entity_class)
        yield client

    return _get_entity_client


# ===== Утилиты для управления контейнером =====


async def initialize_bitrix_container() -> None:
    """
    Предварительная инициализация контейнера зависимостей.

    Должна вызываться при старте приложения.
    """
    await _dependency_container.initialize()


async def shutdown_bitrix_container() -> None:
    """
    Корректное завершение работы контейнера зависимостей.

    Должна вызываться при остановке приложения.
    """
    await _dependency_container.shutdown()
