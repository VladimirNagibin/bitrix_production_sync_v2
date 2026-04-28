# from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# from .ai import AISettings
# from .auth import AuthSettings
# from .base import AppSettings
# from .bitrix24 import Bitrix24Settings
# from .business import BusinessSettings
# from .database import DatabaseSettings, RedisSettings
# from .messaging import EmailSettings, RabbitSettings


class Settings(BaseSettings):
    """Главный класс настроек приложения"""

    # === Приложение ===
    # app: AppSettings = Field(default_factory=AppSettings)

    # # === Инфраструктура ===
    # database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    # redis: RedisSettings = Field(default_factory=RedisSettings)

    # # === Безопасность ===
    # auth: AuthSettings = Field(default_factory=AuthSettings)

    # # === Интеграции ===
    # bitrix24: Bitrix24Settings = Field(default_factory=Bitrix24Settings)
    # rabbitmq: RabbitSettings = Field(default_factory=RabbitSettings)
    # email: EmailSettings = Field(default_factory=EmailSettings)

    # # === AI/ML ===
    # ai: AISettings = Field(default_factory=AISettings)

    # # === Бизнес-логика ===
    # business: BusinessSettings = Field(default_factory=BusinessSettings)

    # # === Глобальные ===
    # encryption_key: str = Field(..., min_length=44)  # Fernet key
    # max_file_size: int = 20 * 1024 * 1024  # 20 МБ

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # === Прокси-свойства для удобства ===
    # @property
    # def dsn(self) -> str:
    #     return self.database.dsn

    # @property
    # def is_dev(self) -> bool:
    #     return self.app.is_dev

    # @property
    # def bitrix_configured(self) -> bool:
    #     return self.bitrix24.is_configured

    # def validate_production(self) -> list[str]:
    #     """Проверка настроек для продакшена"""
    #     errors = []
    #     if not self.is_dev:
    #         if self.app.app_reload:
    #             errors.append("APP_RELOAD должен быть False в продакшене")
    #         if self.app.log_level == "DEBUG":
    #             errors.append("LOG_LEVEL не должен быть DEBUG в продакшене")
    #         if not self.auth.secret_key or len(self.auth.secret_key) < 32:
    #             errors.append(
    #                 "AUTH_SECRET_KEY не настроен или слишком короткий"
    #             )
    #         if not self.encryption_key or len(self.encryption_key) < 44:
    #             errors.append(
    #                 "ENCRYPTION_KEY не настроен (нужен Fernet key)"
    #             )
    #     return errors

# Глобальный экземпляр
settings = Settings()

# Экспорт для удобного импорта
__all__ = [
    # "AppSettings",
    # "AuthSettings",
    # "Bitrix24Settings",
    # "DatabaseSettings",
    # "RedisSettings",
    "Settings",
    "settings",
]
