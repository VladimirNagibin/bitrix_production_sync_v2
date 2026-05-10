# import uuid

# from collections.abc import AsyncGenerator, AsyncIterator
# from contextlib import asynccontextmanager
# from datetime import datetime

# import sqlalchemy as sa

# from core.settings import settings
# from sqlalchemy import false, func
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.ext.asyncio import (
#     AsyncAttrs,
#     AsyncEngine,
#     AsyncSession,
#     async_sessionmaker,
#     create_async_engine,
# )
# from sqlalchemy.orm import (
#     DeclarativeBase,
#     Mapped,
#     mapped_column,
# )

# from core.logger import logger


# POOL_SIZE = 20
# MAX_OVERFLOW = 10


# class DatabaseConfig:
#     """Configuration class for database settings."""

#     def __init__(self) -> None:
#         self.dsn = settings.dsn
#         self.echo = settings.POSTGRES_DB_ECHO
#         self.pool_size = POOL_SIZE
#         self.max_overflow = MAX_OVERFLOW
#         self.pool_pre_ping = True
#         self.future = True


# class Base(AsyncAttrs, DeclarativeBase):  # type: ignore[misc]
#     __abstract__ = True

#     id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True),
#         primary_key=True,
#         default=uuid.uuid4,
#         server_default=func.gen_random_uuid(),
#         comment="Уникальный идентификатор",
#     )
#     created_at: Mapped[datetime] = mapped_column(
#         server_default=func.now(),
#         comment="Дата и время создания",
#     )
#     updated_at: Mapped[datetime] = mapped_column(
#         server_default=func.now(),
#         onupdate=func.now(),
#         comment="Дата и время последнего обновления",
#     )
#     is_deleted_in_bitrix: Mapped[bool] = mapped_column(
#         server_default=false(),
#         default=False,
#         comment="Удалён в Битрикс",
#     )


# class DatabaseManager:
#     """Manager class for database operations."""

#     def __init__(self, config: DatabaseConfig) -> None:
#         self.config = config
#         self._engine = self._create_engine()
#         self._session_factory = self._create_session_factory()

#     def _create_engine(self) -> AsyncEngine:
#         """Create and configure async engine."""
#         return create_async_engine(
#             self.config.dsn,
#             echo=self.config.echo,
#             future=self.config.future,
#             pool_pre_ping=self.config.pool_pre_ping,
#             pool_size=self.config.pool_size,
#             max_overflow=self.config.max_overflow,
#             connect_args=(
#                 {
#                     "command_timeout": 60,
#                     "server_settings": {
#                         "jit": "off",
#                         "statement_timeout": "30000",
#                     },
#                 }
#                 if "postgresql" in self.config.dsn
#                 else {}
#             ),
#         )

#     def _create_session_factory(self) -> async_sessionmaker[AsyncSession]:
#         """Create session factory with configured options."""
#         return async_sessionmaker(
#             self._engine,
#             class_=AsyncSession,
#             expire_on_commit=False,
#             autoflush=False,
#         )

#     @property
#     def session_factory(self) -> async_sessionmaker[AsyncSession]:
#         """Get session factory."""
#         return self._session_factory

#     @property
#     def engine(self) -> AsyncEngine:
#         """Get database engine."""
#         return self._engine


# # Initialize database manager
# db_config = DatabaseConfig()
# db_manager = DatabaseManager(db_config)


# async def create_database() -> None:
#     """Create all database tables."""
#     try:
#         async with db_manager.engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)
#         logger.info("Database tables created successfully")
#     except Exception as e:
#         logger.error("Failed to create database tables: %s", e)
#         raise


# async def purge_database() -> None:
#     """Drop all database tables."""
#     try:
#         async with db_manager.engine.begin() as conn:
#             await conn.run_sync(Base.metadata.drop_all)
#         logger.info("Database tables dropped successfully")
#     except Exception as e:
#         logger.error("Failed to drop database tables: %s", e)
#         raise


# @asynccontextmanager
# async def get_session() -> AsyncIterator[AsyncSession]:
#     """
#     Get database session as async context manager.

#     Usage:
#         async with get_session() as session:
#             await session.execute(...)
#     """
#     session: AsyncSession = db_manager.session_factory()
#     try:
#         logger.debug("Database session started")
#         yield session
#         await session.commit()
#         logger.debug("Database session committed successfully")
#     except Exception as e:
#         await session.rollback()
#         logger.error("Database session rolled back due to error: %s", e)
#         raise
#     finally:
#         await session.close()
#         logger.debug("Database session closed")


# async def get_session_generator() -> AsyncGenerator[AsyncSession]:
#     """
#     Get database session as async generator.

#     This is maintained for backward compatibility with existing code
#     that uses dependency injection patterns.
#     """
#     async with get_session() as session:
#         yield session


# class DatabaseHealthCheck:
#     """Class for database health monitoring."""

#     @staticmethod
#     async def check_connection() -> bool:
#         """Check if database is reachable."""
#         try:
#             async with db_manager.engine.connect() as conn:
#                 await conn.execute(sa.text("SELECT 1"))
#             return True
#         except Exception as e:
#             logger.error("Database health check failed: %s", e)
#             return False

#     @staticmethod
#     async def get_connection_info() -> dict[str, str | int]:
#         """Get database connection information."""
#         return {
#             "dsn": db_config.dsn,
#             "pool_size": db_config.pool_size,
#             "max_overflow": db_config.max_overflow,
#             "echo": db_config.echo,
#         }


# # Backward compatibility exports
# engine: AsyncEngine = db_manager.engine
# async_session: async_sessionmaker[AsyncSession] = db_manager.session_factory
