from datetime import timedelta

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions.settings import InvalidSettingsValueError


SECRET_KEY_MIN_LENGTH = 32
ADMIN_PASS_MIN_LENGTH = 8


class AuthSettings(BaseSettings):
    secret_key: str = Field(
        default="your-32-char-min-secret-key-here!!!",
        min_length=SECRET_KEY_MIN_LENGTH,
    )
    algorithm: str = "HS256"

    # Access token
    access_token_expire_minutes: int = 60
    # Refresh token
    refresh_token_expire_days: int = 30

    # Админ по умолчанию (только для dev!)
    admin_username: str = "admin"
    admin_password: str = Field(
        default="password", min_length=ADMIN_PASS_MIN_LENGTH
    )

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        field_name = "secret_key"
        if len(v) < SECRET_KEY_MIN_LENGTH:
            raise InvalidSettingsValueError(
                field_name,
                v,
                (
                    f"{field_name} должен быть не менее "
                    f"{SECRET_KEY_MIN_LENGTH} символов"
                ),
            )
        return v

    @property
    def access_token_expires(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expires(self) -> timedelta:
        return timedelta(days=self.refresh_token_expire_days)
