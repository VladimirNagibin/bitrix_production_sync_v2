from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .auth import SECRET_KEY_MIN_LENGTH, AuthSettings
from .base import AppSettings, SeqSettings
from .bitrix24 import Bitrix24Settings
from .database import DatabaseSettings, RabbitSettings, RedisSettings
from .utils import LogLevel


ENCRIPTION_KEY_MIN_LENGTH = 44
# from .ai import AISettings
# from .business import BusinessSettings
# from .messaging import EmailSettings


class Settings(BaseSettings):
    """Главный класс настроек приложения"""

    # === Приложение ===
    app: AppSettings = Field(default_factory=AppSettings)
    seq: SeqSettings = Field(default_factory=SeqSettings)

    # === Инфраструктура ===
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    rabbitmq: RabbitSettings = Field(default_factory=RabbitSettings)

    # === Безопасность ===
    auth: AuthSettings = Field(default_factory=AuthSettings)

    # === Интеграции ===
    bitrix24: Bitrix24Settings = Field(default_factory=Bitrix24Settings)

    # email: EmailSettings = Field(default_factory=EmailSettings)

    # # === AI/ML ===
    # ai: AISettings = Field(default_factory=AISettings)

    # # === Бизнес-логика ===
    # business: BusinessSettings = Field(default_factory=BusinessSettings)

    # === Глобальные ===
    encryption_key: str = Field(default="", min_length=44)  # Fernet key
    max_file_size: int = 20 * 1024 * 1024  # 20 МБ

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === Прокси-свойства для удобства ===
    @property
    def dsn(self) -> str:
        return self.database.dsn

    @property
    def is_dev(self) -> bool:
        return self.app.is_dev

    @property
    def bitrix_configured(self) -> bool:
        return self.bitrix24.is_configured

    def validate_production(self) -> list[str]:
        """Проверка настроек для продакшена"""
        errors: list[str] = []
        if not self.is_dev:
            if self.app.reload:
                errors.append("APP_RELOAD должен быть False в продакшене")
            if self.app.log_level == "DEBUG":
                errors.append("LOG_LEVEL не должен быть DEBUG в продакшене")
            if (
                not self.auth.secret_key
                or len(self.auth.secret_key) < SECRET_KEY_MIN_LENGTH
            ):
                errors.append(
                    "AUTH_SECRET_KEY не настроен или слишком короткий"
                )
            if (
                not self.encryption_key
                or len(self.encryption_key) < ENCRIPTION_KEY_MIN_LENGTH
            ):
                errors.append("ENCRYPTION_KEY не настроен (нужен Fernet key)")
        return errors


# Глобальный экземпляр
settings = Settings()


# Экспорт для удобного импорта
__all__ = [
    "AppSettings",
    "AuthSettings",
    "Bitrix24Settings",
    "DatabaseSettings",
    "LogLevel",
    "RedisSettings",
    "Settings",
    "settings",
]
