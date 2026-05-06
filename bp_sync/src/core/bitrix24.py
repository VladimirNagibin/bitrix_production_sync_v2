from typing import Any

from pydantic import Field, HttpUrl, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions.settings import InvalidSettingsValueError


class Bitrix24Settings(BaseSettings):
    # OAuth
    client_id: str = ""
    client_secret: str = ""
    portal_url: HttpUrl | str = Field(default="https://portal.bitrix24.ru")
    redirect_uri: HttpUrl | str | None = Field(default=None)

    # Webhooks
    webhook_key: str = ""
    webhook_token: str = ""
    webhook_max_age_seconds: int = 300  # 5 минут

    # Токены для сущностей
    webhook_tokens: dict[str, str] = Field(default_factory=dict)

    # Бизнес-правила
    service_user_id: int = 1
    default_provider: str = "B24"
    max_processing_stage: int = 5

    # Тестирование
    test_mode: bool = False
    test_deal_id: int | None = None

    model_config = SettingsConfigDict(
        env_prefix="BITRIX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("portal_url", "redirect_uri", mode="before")
    @classmethod
    def ensure_https(cls, v: Any, info: ValidationInfo) -> Any:
        if v and not str(v).startswith("https://"):
            raise InvalidSettingsValueError(
                field_name=str(info.field_name),
                value=v,
                reason="URL должен использовать HTTPS",
            )
        return v

    @property
    def is_configured(self) -> bool:
        return all([self.client_id, self.client_secret, self.portal_url])

    @property
    def portal_domain(self) -> str:
        return str(self.portal_url).replace("https://", "").rstrip("/")

    def get_webhook_config(
        self, token: str, events: set[str]
    ) -> dict[str, Any]:
        return {
            "expected_tokens": {token: self.portal_domain},
            "allowed_events": list(events),
            "max_age": self.webhook_max_age_seconds,
        }

    # Удобные property для конкретных сущностей
    @property
    def webhook_deal_config(self) -> dict[str, Any]:
        return self.get_webhook_config(
            self.webhook_tokens.get("deal", self.webhook_token),
            {"ONCRMDEALUPDATE", "ONCRMDEALADD", "ONCRMDEALDELETE"},
        )

    @property
    def webhook_product_config(self) -> dict[str, Any]:
        return self.get_webhook_config(
            self.webhook_tokens.get("product", self.webhook_token),
            {"ONCRMPRODUCTUPDATE", "ONCRMPRODUCTADD", "ONCRMPRODUCTDELETE"},
        )
