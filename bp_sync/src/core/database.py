from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils import DatabaseURL, validate_positive_int


PASS_MIN_LENGTH = 8
MAX_OVERFLOW = 10
POOL_SIZE_DEFAULT = 20
POOL_SIZE_MIN = 5
POOL_SIZE_MAX = 100


class DatabaseSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 5442
    user: str = "postgres"
    password: str = Field(default="postgres", min_length=PASS_MIN_LENGTH)
    db_name: str = "bp_sync"
    echo: bool = False
    pool_size: int = Field(
        default=POOL_SIZE_DEFAULT, ge=POOL_SIZE_MIN, le=POOL_SIZE_MAX
    )
    max_overflow: int = MAX_OVERFLOW

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        return validate_positive_int("port", v)

    @property
    def dsn(self) -> str:
        return DatabaseURL.build(
            driver="postgresql+asyncpg",
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.db_name,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
        )

    @property
    def is_configured(self) -> bool:
        return all([self.host, self.user, self.password, self.db_name])


class RedisSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    password: str = ""
    db: int = 0
    socket_timeout: float = 5.0

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class RabbitSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 5672
    user: str = "admin"
    password: str = ""
    vhost: str = "/"
    email_queue: str = "email_messages"
    exchange: str = "email_exchange"

    model_config = SettingsConfigDict(env_prefix="RABBIT_")

    # @property
    # def url(self) -> str:
    #     auth = f":{self.password}@" if self.password else ""
    #     return f"redis://{auth}{self.host}:{self.port}/{self.db}"
