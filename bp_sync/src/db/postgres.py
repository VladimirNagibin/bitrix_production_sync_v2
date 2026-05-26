"""
Модуль асинхронной работы с SQLAlchemy (PostgreSQL).
"""

import uuid

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import sqlalchemy as sa

from sqlalchemy import false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import DatabaseError as SQLAlchemyDatabaseError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from core import settings
from core.exceptions.database import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseLoadError,
)
from core.logger import logger


# ===== Константы / Constants =====
DEFAULT_POOL_SIZE = 20
DEFAULT_MAX_OVERFLOW = 10
ENGINE_COMMAND_TIMEOUT = 60  # seconds (for asyncpg)
ENGINE_STATEMENT_TIMEOUT = "30000"  # milliseconds (PostgreSQL)


# ===== Базовый класс моделей / Base Model =====
class Base(AsyncAttrs, DeclarativeBase):  # type: ignore[misc]
    """
    Абстрактный базовый класс для всех моделей SQLAlchemy.
    Содержит общие поля: internal_id, created_at, updated_at, is_deleted.
    """

    __abstract__ = True

    internal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Уникальный идентификатор",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        comment="Дата и время создания",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата и время последнего обновления",
    )
    is_deleted: Mapped[bool] = mapped_column(
        server_default=false(),
        default=False,
        comment="Флаг удаления",
    )


# ===== Конфигурация базы данных / Database Configuration =====
class DatabaseConfig:
    """Конфигурация подключения к БД (DSN, пул, таймауты)."""

    def __init__(self) -> None:
        self.dsn: str = settings.dsn
        self.echo: bool = settings.database.echo
        self.pool_size: int = DEFAULT_POOL_SIZE
        self.max_overflow: int = DEFAULT_MAX_OVERFLOW
        self.pool_pre_ping: bool = True
        self.future: bool = True

    def is_postgres(self) -> bool:
        """Проверяет, используется ли PostgreSQL."""
        return "postgresql" in self.dsn

    def build_connect_args(self) -> dict[str, Any]:
        """
        Формирует аргументы для подключения в зависимости от типа БД.
        """
        if self.is_postgres():
            return {
                "command_timeout": ENGINE_COMMAND_TIMEOUT,
                "server_settings": {
                    "jit": "off",  # Отключаем JIT для уменьшения задержек
                    "statement_timeout": ENGINE_STATEMENT_TIMEOUT,
                },
            }
        return {}


# ===== Менеджер базы данных / Database Manager =====
class DatabaseManager:
    """
    Менеджер жизненного цикла подключения к БД.
    Управляет движком (Engine) и фабрикой сессий (Session Factory).
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """
        Инициализирует движок и фабрику сессий.

        Raises:
            DatabaseConnectionError: Если не удалось подключиться к БД.
            DatabaseError: При ошибках конфигурации движка.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return

        try:
            self._create_engine()
            await self._test_connection()
            self._create_session_factory()
            self._initialized = True
            logger.info("Database connection initialized successfully")
        except OperationalError as e:
            logger.error("Database connection failed: %s", e, exc_info=True)
            raise DatabaseConnectionError(
                message="Cannot connect to database",
                details={"error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            logger.error("Database engine init error: %s", e, exc_info=True)
            raise DatabaseError(
                message="Database engine initialization failed",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error during DB init: %s", e, exc_info=True
            )
            raise DatabaseError(
                message="Unexpected database initialization error",
                details={"error": str(e)},
            ) from e

    def _create_engine(self) -> None:
        """Создаёт асинхронный движок (без проверки соединения)."""
        self._engine = create_async_engine(
            self._config.dsn,
            echo=self._config.echo,
            future=self._config.future,
            pool_pre_ping=self._config.pool_pre_ping,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow,
            connect_args=self._config.build_connect_args(),
        )

    async def _test_connection(self) -> None:
        """
        Проверяет соединение путём выполнения простого запроса.

        Raises:
            DatabaseConnectionError: Если тестовый запрос не удался.
        """
        if self._engine is None:
            raise DatabaseError(message="Engine not created")
        try:
            async with self._engine.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
        except OperationalError as e:
            raise DatabaseConnectionError(
                message="Connection test failed (SELECT 1)",
                details={"error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            raise DatabaseError(
                message=f"Connection test error: {e}",
                details={"error": str(e)},
            ) from e

    def _create_session_factory(self) -> None:
        """Создаёт фабрику асинхронных сессий."""
        if self._engine is None:
            raise DatabaseError(message="Engine not created")
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """
        Возвращает экземпляр движка БД.

        Raises:
            DatabaseError: Если движок не был инициализирован.
        """
        if not self._initialized or self._engine is None:
            raise DatabaseError(
                message="Database not initialized. Call initialize() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Возвращает фабрику сессий.

        Raises:
            DatabaseError: Если менеджер не был инициализирован.
        """
        if not self._initialized or self._session_factory is None:
            raise DatabaseError(
                message="Database not initialized. Call initialize() first."
            )
        return self._session_factory

    async def dispose(self) -> None:
        """Корректно закрывает все соединения и освобождает ресурсы."""
        if not self._initialized:
            return

        logger.info("Disposing database engine...")
        try:
            if self._engine is not None:
                await self._engine.dispose()
        except SQLAlchemyError as e:
            logger.error("Error during engine dispose: %s", e)
        finally:
            self._initialized = False
            self._engine = None
            self._session_factory = None
            logger.info("Database engine disposed")


# ===== Глобальный экземпляр менеджера =====
_db_config = DatabaseConfig()
db_manager = DatabaseManager(_db_config)

# Для обратной совместимости (если кто-то импортирует напрямую)
# async_session = db_manager.session_factory
# engine = db_manager.engine


# ===== Управление схемами (Создание/Удаление таблиц)/Schema Management =====
async def _run_schema_sync_action(action: str) -> None:
    """
    Вспомогательная функция для выполнения синхронных действий над схемой
    (create_all/drop_all) в асинхронном контексте.

    Args:
        action: Название метода для вызова ('create_all' или 'drop_all').

    Raises:
        DatabaseLoadError: При ошибке выполнения операции над схемой.
    """
    try:
        engine_instance = db_manager.engine
        async with engine_instance.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: getattr(Base.metadata, action)(sync_conn)
            )
        logger.info("Schema action '%s' completed successfully", action)
    except SQLAlchemyError as e:
        logger.error("Failed to execute schema action '%s': %s", action, e)
        raise DatabaseLoadError(
            message=f"Schema action '{action}' failed",
            details={"original_error": str(e)},
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error during schema action '%s': %s", action, e
        )
        raise DatabaseLoadError(
            message=f"Unexpected error during schema action '{action}'",
            details={"original_error": str(e)},
        ) from e


async def create_database_tables() -> None:
    """Создаёт все таблицы в БД, используя метаданные моделей."""
    await _run_schema_sync_action("create_all")


async def drop_database_tables() -> None:
    """Удаляет все таблицы из БД."""
    await _run_schema_sync_action("drop_all")


# ===== Контекстный менеджер сессии / Session Context Manager =====
@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Предоставляет асинхронную сессию SQLAlchemy.

    Управляет транзакцией: COMMIT при успехе, ROLLBACK при ошибке.
    Гарантирует закрытие сессии при выходе из контекста.

    Usage:
        async with get_session() as session:
            await session.execute(...)

    Raises:
        DatabaseConnectionError: При проблемах с сетью/подключением.
        DatabaseLoadError: При ошибках целостности данных.
        DatabaseError: При прочих ошибках БД.
    """
    session: AsyncSession = db_manager.session_factory()
    try:
        logger.debug("Starting new DB session")
        yield session
        await session.commit()
        logger.debug("DB session committed successfully")
    except OperationalError as e:
        await session.rollback()
        logger.error("Database connection error, rollback: %s", e)
        raise DatabaseConnectionError(
            message="Database connection lost during operation",
            details={"original_error": str(e)},
        ) from e
    except IntegrityError as e:
        await session.rollback()
        logger.error("Database integrity error, rollback: %s", e)
        raise DatabaseLoadError(
            message="Data integrity constraint violated",
            details={"original_error": str(e)},
        ) from e
    except SQLAlchemyDatabaseError as e:
        await session.rollback()
        logger.error("Database execution error, rollback: %s", e)
        raise DatabaseError(
            message="Database operation failed",
            details={"original_error": str(e)},
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Unexpected error in DB session, rollback: %s", e)
        raise DatabaseError(
            message="Unexpected database error",
            details={"original_error": str(e)},
        ) from e
    finally:
        await session.close()
        logger.debug("DB session closed")


async def get_session_generator() -> AsyncGenerator[AsyncSession]:
    """
    Генератор сессий для использования в зависимости FastAPI (Depends).

    Usage:
        @app.get("/")
        async def endpoint(
            session: AsyncSession = Depends(get_session_generator)
        ):
            ...
    """
    async with get_session() as session:
        yield session


# ===== Мониторинг здоровья / Health Check =====
class DatabaseHealthCheck:
    """Утилиты для мониторинга состояния базы данных."""

    @staticmethod
    async def is_healthy() -> bool:
        """Проверяет, отвечает ли БД на простой запрос."""
        try:
            engine = db_manager.engine
            async with engine.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
        except (OperationalError, SQLAlchemyError, DatabaseError) as e:
            logger.error("Health check failed: %s", e, exc_info=False)
            return False
        except Exception as e:  # noqa: BLE001
            logger.error("Unexpected health check error: %s", e)
            return False
        else:
            return True

    @staticmethod
    async def get_connection_info() -> dict[str, Any]:
        """Возвращает информацию о настройках подключения."""
        return {
            "dsn": _db_config.dsn,
            "pool_size": _db_config.pool_size,
            "max_overflow": _db_config.max_overflow,
            "echo": _db_config.echo,
            "is_postgres": _db_config.is_postgres(),
        }
