"""
Модуль настроек для подключения к базам данных и брокерам сообщений.

Содержит конфигурации для:
- PostgreSQL (с использованием asyncpg)
- Redis
- RabbitMQ
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.exceptions.settings import InvalidSettingsValueError

from .utils import DatabaseURL, validate_positive_int


# ===== Константы =====
PASS_MIN_LENGTH = 8
MAX_OVERFLOW = 10
POOL_SIZE_DEFAULT = 20
POOL_SIZE_MIN = 5
POOL_SIZE_MAX = 100

DEFAULT_POSTGRES_HOST = "127.0.0.1"
DEFAULT_POSTGRES_PORT = 5442
DEFAULT_POSTGRES_USER = "postgres"
DEFAULT_POSTGRES_PASSWORD = "postgres"  # noqa: S105
DEFAULT_POSTGRES_DB = "bp_sync"

DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
DEFAULT_REDIS_SOCKET_TIMEOUT = 5.0

DEFAULT_RABBIT_HOST = "127.0.0.1"
DEFAULT_RABBIT_PORT = 5672
DEFAULT_RABBIT_USER = "admin"
DEFAULT_RABBIT_VHOST = "/"
DEFAULT_RABBIT_EMAIL_QUEUE = "email_messages"
DEFAULT_RABBIT_EXCHANGE = "email_exchange"


# ===== Настройки PostgreSQL =====
class DatabaseSettings(BaseSettings):
    """Настройки подключения к PostgreSQL с использованием asyncpg."""

    # ----- Поля модели -----
    host: str = Field(
        default=DEFAULT_POSTGRES_HOST,
        description="Database host",
    )
    port: int = Field(
        default=DEFAULT_POSTGRES_PORT,
        description="Database port",
    )
    user: str = Field(
        default=DEFAULT_POSTGRES_USER,
        description="Database user",
    )
    password: str = Field(
        default=DEFAULT_POSTGRES_PASSWORD,
        min_length=PASS_MIN_LENGTH,
        description="Database password (min 8 characters)",
    )
    db: str = Field(
        default=DEFAULT_POSTGRES_DB,
        description="Database name",
    )
    echo: bool = Field(
        default=True,
        description="Echo SQL queries (for development)",
    )
    pool_size: int = Field(
        default=POOL_SIZE_DEFAULT,
        ge=POOL_SIZE_MIN,
        le=POOL_SIZE_MAX,
        description="Connection pool size",
    )
    max_overflow: int = Field(
        default=MAX_OVERFLOW,
        description="Maximum overflow connections",
    )

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Валидаторы -----
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Проверяет, что порт положительный."""
        return validate_positive_int("port", v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Проверяет минимальную длину пароля (дополнительно к Field)."""
        if len(v) < PASS_MIN_LENGTH:
            raise InvalidSettingsValueError(
                field_name="password",
                value="***",
                reason=(
                    f"Password must be at least {PASS_MIN_LENGTH} characters "
                    "long"
                ),
            )
        return v

    # ----- Прокси-свойства -----
    @property
    def dsn(self) -> str:
        """Возвращает DSN строку для SQLAlchemy (asyncpg)."""
        return DatabaseURL.build(
            driver="postgresql+asyncpg",
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.db,
            # pool_size=self.pool_size,
            # max_overflow=self.max_overflow,
        )

    @property
    def is_configured(self) -> bool:
        """Проверяет, что все основные параметры подключения заданы."""
        return bool(self.host and self.user and self.password and self.db)


# ===== Настройки Redis =====
class RedisSettings(BaseSettings):
    """Настройки подключения к Redis."""

    # ----- Поля модели -----
    host: str = Field(
        default=DEFAULT_REDIS_HOST,
        description="Redis host",
    )
    port: int = Field(
        default=DEFAULT_REDIS_PORT,
        description="Redis port",
    )
    password: str = Field(
        default="",
        description="Redis password (optional)",
    )
    db: int = Field(
        default=DEFAULT_REDIS_DB,
        description="Redis database number",
    )
    socket_timeout: float = Field(
        default=DEFAULT_REDIS_SOCKET_TIMEOUT,
        gt=0,
        description="Socket timeout in seconds",
    )

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Валидаторы -----
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        return validate_positive_int("port", v)

    @field_validator("db")
    @classmethod
    def validate_db(cls, v: int) -> int:
        if v < 0:
            from core.exceptions.settings import InvalidSettingsValueError

            raise InvalidSettingsValueError(
                field_name="db",
                value=v,
                reason="Database number must be non-negative",
            )
        return v

    # ----- Прокси-свойства -----
    @property
    def url(self) -> str:
        """Возвращает Redis URL в формате redis://[:password@]host:port/db."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    @property
    def is_configured(self) -> bool:
        """Проверяет, что хост задан."""
        return bool(self.host)


# ===== Настройки RabbitMQ =====
class RabbitSettings(BaseSettings):
    """Настройки подключения к RabbitMQ (AMQP)."""

    # ----- Поля модели -----
    host: str = Field(
        default=DEFAULT_RABBIT_HOST,
        description="RabbitMQ host",
    )
    port: int = Field(
        default=DEFAULT_RABBIT_PORT,
        description="RabbitMQ AMQP port",
    )
    user: str = Field(
        default=DEFAULT_RABBIT_USER,
        description="RabbitMQ username",
    )
    password: str = Field(
        default="",
        description="RabbitMQ password",
    )
    vhost: str = Field(
        default=DEFAULT_RABBIT_VHOST,
        description="Virtual host",
    )
    email_queue: str = Field(
        default=DEFAULT_RABBIT_EMAIL_QUEUE,
        description="Queue name for email messages",
    )
    exchange: str = Field(
        default=DEFAULT_RABBIT_EXCHANGE,
        description="Exchange name for email messages",
    )

    model_config = SettingsConfigDict(
        env_prefix="RABBIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Валидаторы -----
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        return validate_positive_int("port", v)

    @field_validator("vhost")
    @classmethod
    def validate_vhost(cls, v: str) -> str:
        """Валидация virtual host (не может быть пустым)."""
        if not v:
            raise InvalidSettingsValueError(
                field_name="vhost",
                value=v,
                reason="Virtual host cannot be empty",
            )
        return v

    # ----- Прокси-свойства -----
    @property
    def url(self) -> str:
        """
        Возвращает AMQP URL для подключения к RabbitMQ.
        Формат: amqp://[user[:password]@]host:port/vhost
        """
        auth = ""
        if self.user:
            auth = self.user
            if self.password:
                auth += f":{self.password}"
            auth += "@"
        # Убедимся, что vhost начинается с '/'
        vhost = self.vhost if self.vhost.startswith("/") else f"/{self.vhost}"
        return f"amqp://{auth}{self.host}:{self.port}{vhost}"

    @property
    def is_configured(self) -> bool:
        """Проверяет, что основные параметры подключения заданы."""
        return bool(self.host and self.user)
