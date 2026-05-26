"""Модуль Redis клиента."""

import asyncio

from collections.abc import AsyncGenerator
from typing import Any, Protocol, cast

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import AuthenticationError as RedisAuthenticationError
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    RedisError,
)

from core import settings
from core.exceptions.redis import (
    RedisManagerAuthError,
    RedisManagerConnectionError,
    RedisManagerNotInitializedError,
)
from core.logger import logger


# ===== Константы =====
REDIS_TIMEOUT = 2.0  # Таймаут для операций с Redis в секундах
REDIS_CONNECTION_POOL_SETTINGS: dict[str, Any] = {
    "max_connections": 20,
    "health_check_interval": 30,
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "retry_on_timeout": True,
}


# ===== Протокол для строгой типизации Redis клиента =====
class _StrictRedisClient(Protocol):
    async def ping(self) -> bool: ...
    async def info(self, section: str | None = None) -> dict[str, Any]: ...


# ===== Менеджер Redis =====
class RedisManager:
    """
    Менеджер подключения Redis с пулом соединений и проверкой здоровья.
    Управляет жизненным циклом (инициализация, закрытие, переиспользование).
    """

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._connection_pool: ConnectionPool | None = None
        self._is_initialized: bool = False
        self._is_shutting_down: bool = False

    # ----- Публичные методы -----
    async def initialize(self) -> None:
        """
        Инициализирует подключение к Redis и пул соединений.

        Raises:
            RedisManagerConnectionError: Если не удалось подключиться.
            RedisManagerAuthError: Если неверный пароль.
            RedisManagerError: При других ошибках инициализации.
        """
        if self._is_initialized:
            logger.warning("Redis is already initialized")
            return

        try:
            self._connection_pool = await self._create_connection_pool()
            self._redis = Redis(connection_pool=self._connection_pool)
            await self._verify_connection()
            self._is_initialized = True
            logger.info("Redis connection initialized successfully")

        except RedisAuthenticationError as e:
            logger.error(
                "Redis authentication failed. Invalid password: %s",
                e,
                exc_info=True,
            )
            await self._cleanup()
            raise RedisManagerAuthError from e
        except (RedisConnectionError, OSError) as e:
            logger.error("Failed to connect to Redis: %s", e, exc_info=True)
            await self._cleanup()
            raise RedisManagerConnectionError from e
        except RedisError as e:
            logger.error(
                "Redis error during initialization: %s", e, exc_info=True
            )
            await self._cleanup()
            raise RedisManagerNotInitializedError from e

    async def close(self) -> None:
        """Закрывает подключение к Redis и освобождает ресурсы."""
        if not self._is_initialized:
            return

        logger.info("Closing Redis connection...")
        await self._cleanup()
        logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        """
        Возвращает экземпляр клиента Redis.

        Returns:
            Redis: Активный клиент Redis.

        Raises:
            RedisManagerNotInitializedError: Если Redis не инициализирован
            или находится в процессе закрытия.
        """
        if (
            not self._is_initialized
            or not self._redis
            or self._is_shutting_down
        ):
            raise RedisManagerNotInitializedError(
                message="Redis is not initialized. Call initialize() first."
            )
        return self._redis

    async def health_check(self) -> bool:
        """Проверяет, отвечает ли Redis на ping."""
        try:
            return await self._ping_connection()
        except RedisError:
            return False

    async def get_info(self) -> dict[str, Any]:
        """
        Возвращает информацию о сервере Redis (версия, память, клиенты).

        Returns:
            dict[str, Any]: Словарь с метриками или ошибкой.
        """
        if (
            not self._is_initialized
            or not self._redis
            or self._is_shutting_down
        ):
            return {"error": "Redis not initialized"}

        try:
            redis_client = cast("_StrictRedisClient", self._redis)
            info: dict[str, Any] = await redis_client.info()

            return {
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
            }
        except RedisError as e:
            logger.error("Failed to get Redis info: %s", e, exc_info=True)
            return {"error": str(e)}

    # ----- Приватные методы -----
    async def _create_connection_pool(self) -> ConnectionPool:
        """
        Создает и настраивает пул соединений.

        Returns:
            ConnectionPool: Настроенный пул соединений.
        """
        # Подготовка аргументов подключения
        connection_kwargs: dict[str, Any] = {
            "host": settings.redis.host,
            "port": settings.redis.port,
            "db": 0,
            "password": settings.redis.password,
            "decode_responses": True,
            "encoding": "utf-8",
            "socket_connect_timeout": REDIS_CONNECTION_POOL_SETTINGS[
                "socket_connect_timeout"
            ],
            "socket_timeout": REDIS_CONNECTION_POOL_SETTINGS[
                "socket_timeout"
            ],
            "retry_on_timeout": REDIS_CONNECTION_POOL_SETTINGS[
                "retry_on_timeout"
            ],
        }

        # Добавление SSL параметров, если включено
        # ВНИМАНИЕ: ssl_cert_reqs=None отключает проверку сертификата,
        # что небезопасно для продакшена,
        # но требуется для самоподписанных сертификатов.
        if getattr(settings, "ssl", False):
            connection_kwargs.update(
                {
                    "ssl": True,
                    "ssl_cert_reqs": None,
                }
            )

        return ConnectionPool(
            max_connections=REDIS_CONNECTION_POOL_SETTINGS["max_connections"],
            health_check_interval=REDIS_CONNECTION_POOL_SETTINGS[
                "health_check_interval"
            ],
            **connection_kwargs,
        )

    async def _verify_connection(self) -> None:
        """
        Проверяет активность подключения с помощью команды PING.

        Raises:
            RedisManagerConnectionError: Если ping не прошел.
        """
        if not self._redis:
            raise RedisManagerConnectionError(
                message="Redis client not created"
            )

        try:
            redis_client = cast("_StrictRedisClient", self._redis)
            is_healthy = await redis_client.ping()
            if not is_healthy:
                raise RedisManagerConnectionError(
                    message="Redis ping returned False"
                )
        except RedisError as e:
            raise RedisManagerConnectionError(
                message=f"Ping failed: {e}"
            ) from e

    async def _ping_connection(self) -> bool:
        """Отправляет PING и возвращает True при успехе."""
        if not self._redis or self._is_shutting_down:
            return False

        try:
            redis_client = cast("_StrictRedisClient", self._redis)
            return await redis_client.ping()
        except (RedisError, OSError, TimeoutError) as e:
            logger.debug("Redis ping failed: %s", e, exc_info=True)
            return False

    async def _cleanup(self) -> None:
        """Освобождает ресурсы: закрывает клиент и пул соединений."""
        if self._is_shutting_down:
            return

        self._is_shutting_down = True

        # 1. Закрываем клиент
        if self._redis:
            try:
                await asyncio.wait_for(
                    self._redis.aclose(), timeout=REDIS_TIMEOUT
                )
            except TimeoutError:
                logger.warning("Redis client close timeout, forcing cleanup")
            except (RedisConnectionError, OSError):
                logger.debug("Redis client already disconnected")
            except Exception as e:  # noqa: BLE001
                # Ловим оставшиеся исключения, чтобы не прерывать очистку
                logger.warning(
                    "Unexpected error during Redis client close: %s", e
                )
            finally:
                self._redis = None

        # 2. Закрываем пул соединений
        if self._connection_pool:
            try:
                await asyncio.wait_for(
                    self._connection_pool.disconnect(), timeout=REDIS_TIMEOUT
                )
            except TimeoutError:
                logger.warning("Redis pool disconnect timeout")
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Unexpected error during pool disconnect: %s", e
                )
            finally:
                self._connection_pool = None

        self._is_initialized = False
        self._is_shutting_down = False


# ===== Глобальный экземпляр менеджера =====
redis_manager = RedisManager()


# ===== Вспомогательные функции для интеграции с приложением =====
async def init_redis() -> None:
    """Инициализирует Redis. Вызывается один раз при старте приложения."""
    await redis_manager.initialize()


async def close_redis() -> None:
    """Закрывает Redis. Вызывается при остановке приложения."""
    await redis_manager.close()


async def get_redis() -> Redis:
    """
    Возвращает клиент Redis.

    Returns:
        Redis: Экземпляр клиента.

    Raises:
        RedisManagerNotInitializedError: Если Redis не инициализирован.
    """
    return redis_manager.client


async def redis_health_check() -> bool:
    """Выполняет проверку здоровья Redis."""
    return await redis_manager.health_check()


async def get_redis_info() -> dict[str, Any]:
    """Получает информацию о сервере Redis."""
    return await redis_manager.get_info()


# ===== Контекстный менеджер сессии (для операций, требующих закрытия) =====
async def get_redis_session() -> AsyncGenerator[Redis]:
    """
    Контекстный менеджер для сессии Redis.

    Пример:
        async with get_redis_session() as redis:
            await redis.set("key", "value")
    """
    redis = await get_redis()
    try:
        yield redis
    except RedisError as e:
        logger.error("Redis operation failed: %s", e, exc_info=True)
        raise
