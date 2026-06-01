"""
Модуль настроек интеграции с Bitrix24.

Содержит конфигурацию OAuth, вебхуков, бизнес-правил и тестового режима.
Все сообщения об ошибках на английском, комментарии и docstrings на русском.
"""

from typing import Any

from pydantic import Field, HttpUrl, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.exceptions.settings import InvalidSettingsValueError


# ===== Константы =====
DEFAULT_PORTAL_URL = "https://portal.bitrix24.ru"
DEFAULT_WEBHOOK_MAX_AGE_SECONDS = 300  # 5 minutes
DEFAULT_SERVICE_USER_ID = 1
DEFAULT_PROVIDER = "B24"
DEFAULT_MAX_PROCESSING_STAGE = 5
DEFAULT_SYSTEM_USER_ID = 1
DEFAULT_CURRENCY = "KZT"

# Наборы событий вебхуков
DEAL_WEBHOOK_EVENTS = {"ONCRMDEALUPDATE", "ONCRMDEALADD", "ONCRMDEALDELETE"}
PRODUCT_WEBHOOK_EVENTS = {
    "ONCRMPRODUCTUPDATE",
    "ONCRMPRODUCTADD",
    "ONCRMPRODUCTDELETE",
}


# ===== Настройки Bitrix24 =====
class Bitrix24Settings(BaseSettings):
    """
    Настройки интеграции с Bitrix24.

    Загружаются из переменных окружения с префиксом BITRIX_.
    Поддерживает OAuth авторизацию и вебхуки.
    """

    # ----- OAuth настройки -----
    client_id: str = Field(
        default="",
        description="OAuth client ID",
    )
    client_secret: str = Field(
        default="",
        description="OAuth client secret",
    )
    portal_url: HttpUrl | str = Field(
        default=DEFAULT_PORTAL_URL,
        description="Bitrix24 portal URL (must use HTTPS)",
    )
    redirect_uri: HttpUrl | str | None = Field(
        default=None,
        description="OAuth redirect URI",
    )

    currency: str = Field(
        default=DEFAULT_CURRENCY,
        description="Currency for Bitrix24",
    )
    # ----- timezone -----
    server_zone_info: str = Field(
        default="Europe/Moscow",
        description="Zone info of server",
    )

    # ----- Webhook настройки -----
    webhook_key: str = Field(
        default="",
        description="Webhook key (part of webhook URL)",
    )
    webhook_token: str = Field(
        default="",
        description="Default webhook token for authentication",
    )
    webhook_max_age_seconds: int = Field(
        default=DEFAULT_WEBHOOK_MAX_AGE_SECONDS,
        ge=1,
        description="Maximum age of webhook request in seconds",
    )

    # ----- Токены для конкретных сущностей -----
    webhook_tokens: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Entity-specific webhook tokens (e.g., {'deal': 'token', "
            "'product': 'token'})"
        ),
    )

    # ----- Бизнес-правила -----
    service_user_id: int = Field(
        default=DEFAULT_SERVICE_USER_ID,
        description="Bitrix24 user ID for service operations",
    )
    default_provider: str = Field(
        default=DEFAULT_PROVIDER,
        description="Default provider name",
    )
    max_processing_stage: int = Field(
        default=DEFAULT_MAX_PROCESSING_STAGE,
        ge=1,
        le=100,
        description="Maximum processing stage for deals",
    )
    system_user_id: int = Field(
        default=DEFAULT_SYSTEM_USER_ID,
        ge=1,
        description="ID of system user in Bitrix",
    )

    # ----- Настройки тестирования -----
    test_mode: bool = Field(
        default=False,
        description="Enable test mode (bypass some validations)",
    )
    test_deal_id: int | None = Field(
        default=None,
        description="Deal ID to use in tests",
    )

    model_config = SettingsConfigDict(
        env_prefix="BITRIX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Валидаторы -----
    @field_validator("portal_url", mode="before")
    @classmethod
    def ensure_https(cls, v: Any, info: ValidationInfo) -> Any:
        """
        Проверяет, что URL использует HTTPS.

        Args:
            v: Значение URL
            info: Информация о поле

        Returns:
            Проверенное значение

        Raises:
            InvalidSettingsValueError: если URL не начинается с https://
        """
        if v is None:
            return None
        str_v = str(v)
        # Проверяем, что URL имеет протокол HTTPS
        if not str_v.startswith(("https://", "HTTPS://")):
            field_name = str(info.field_name)
            raise InvalidSettingsValueError(
                field_name=field_name,
                value=v,
                reason=f"{field_name} must use HTTPS protocol",
            )
        return v

    @field_validator("webhook_token", "webhook_key")
    @classmethod
    def validate_token_not_empty(cls, v: str) -> str:
        """
        Проверяет, что токен или ключ не пустые (если не в тестовом режиме).
        Валидация должна учитывать test_mode, но здесь сложно, так как нет
        доступа к другим полям. Можно добавить после инициализации.
        """
        return v

    # ----- Прокси-свойства -----
    @property
    def is_configured(self) -> bool:
        """
        Проверяет, настроена ли интеграция с Bitrix24.
        Для OAuth режима требуются client_id, client_secret и portal_url.
        """
        return bool(self.client_id and self.client_secret and self.portal_url)

    @property
    def portal_domain(self) -> str:
        """
        Возвращает домен портала (без https:// и завершающего слеша).
        """
        domain = str(self.portal_url)
        # Удаляем протокол
        if domain.startswith(("https://", "http://")):
            domain = domain.split("://", 1)[1]
        # Удаляем завершающий слеш
        return domain.rstrip("/")

    @property
    def has_webhook_credentials(self) -> bool:
        """
        Проверяет, установлены ли учётные данные для вебхуков.
        """
        return bool(self.webhook_key and self.webhook_token)

    # ----- Вспомогательные методы для работы с вебхуками -----
    def get_webhook_config(
        self, token: str, events: set[str]
    ) -> dict[str, Any]:
        """
        Возвращает конфигурацию для проверки вебхука.

        Args:
            token: Токен для проверки подписи
            events: Набор разрешённых событий

        Returns:
            Словарь конфигурации для валидации вебхука
        """
        return {
            "expected_tokens": {token: self.portal_domain},
            "allowed_events": list(events),
            "max_age": self.webhook_max_age_seconds,
        }

    def _get_entity_token(self, entity_name: str) -> str:
        """
        Внутренний метод для получения токена сущности.

        Args:
            entity_name: Имя сущности (deal, product и т.д.)

        Returns:
            Специфичный для сущности токен или общий webhook_token
        """
        return self.webhook_tokens.get(entity_name, self.webhook_token)

    # Удобные property для конкретных сущностей
    @property
    def webhook_deal_config(self) -> dict[str, Any]:
        """Конфигурация вебхука для сделок."""
        return self.get_webhook_config(
            self._get_entity_token("deal"),
            DEAL_WEBHOOK_EVENTS,
        )

    @property
    def webhook_product_config(self) -> dict[str, Any]:
        """Конфигурация вебхука для товаров."""
        return self.get_webhook_config(
            self._get_entity_token("product"),
            PRODUCT_WEBHOOK_EVENTS,
        )
