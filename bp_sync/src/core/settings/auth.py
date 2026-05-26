"""
Модуль настроек аутентификации.

Содержит конфигурацию для JWT токенов, администратора по умолчанию и
параметры безопасности.
"""

from datetime import timedelta

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.exceptions.settings import InvalidSettingsValueError


# ===== Константы =====
SECRET_KEY_MIN_LENGTH = 32
ADMIN_PASS_MIN_LENGTH = 8
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30


# ===== Класс настроек аутентификации =====
class AuthSettings(BaseSettings):
    """
    Настройки аутентификации и авторизации.

    Загружаются из переменных окружения с префиксом AUTH_,
    либо из секции .env файла.
    """

    # Секретный ключ для подписи JWT
    secret_key: SecretStr = Field(
        default=SecretStr("your-32-char-min-secret-key-here!!!"),
        min_length=SECRET_KEY_MIN_LENGTH,
        description="JWT secret key (min 32 chars for production)",
    )
    # Алгоритм подписи токенов
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )

    # Время жизни access токена (в минутах)
    access_token_expire_minutes: int = Field(
        default=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
        description="Access token lifetime in minutes",
    )

    # Время жизни refresh токена (в днях)
    refresh_token_expire_days: int = Field(
        default=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
        description="Refresh token lifetime in days",
    )

    # Учётные данные администратора (только для разработки!)
    admin_username: str = Field(
        default="admin",
        description="Default admin username (for development only)",
    )
    admin_password: SecretStr | None = Field(
        default=None,
        min_length=ADMIN_PASS_MIN_LENGTH,
        description=("Default admin password (for development only)"),
    )

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Валидаторы -----
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str | SecretStr) -> SecretStr:
        """
        Проверяет, что длина секретного ключа соответствует минимальному
        значению.

        Args:
            v: Значение secret_key

        Returns:
            Проверенное значение

        Raises:
            InvalidSettingsValueError: если ключ слишком короткий
        """
        value = v.get_secret_value() if isinstance(v, SecretStr) else v
        if len(value) < SECRET_KEY_MIN_LENGTH:
            raise InvalidSettingsValueError(
                field_name="secret_key",
                value="***",
                reason=(
                    f"Secret key must be at least "
                    f"{SECRET_KEY_MIN_LENGTH} characters long"
                ),
            )
        if isinstance(v, str):
            return SecretStr(v)
        return v

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(
        cls, v: str | SecretStr | None
    ) -> SecretStr | None:
        """
        Проверяет, что пароль администратора соответствует минимальной длине
        (особенно важно для production, где не рекомендуется использовать
        значение по умолчанию).

        Args:
            v: Значение пароля

        Returns:
            Проверенное значение

        Raises:
            InvalidSettingsValueError: если пароль слишком короткий
        """
        if v is None:
            return None
        value = v.get_secret_value() if isinstance(v, SecretStr) else v
        if len(value) < ADMIN_PASS_MIN_LENGTH:
            raise InvalidSettingsValueError(
                field_name="admin_password",
                value="***",
                reason=(
                    f"Admin password must be at least "
                    f"{ADMIN_PASS_MIN_LENGTH} characters long"
                ),
            )
        if isinstance(v, str):
            return SecretStr(v)
        return v

    # ----- Прокси-свойства для timedelta -----
    @property
    def access_token_expires(self) -> timedelta:
        """Возвращает timedelta для времени жизни access токена."""
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expires(self) -> timedelta:
        """Возвращает timedelta для времени жизни refresh токена."""
        return timedelta(days=self.refresh_token_expire_days)

    # ----- Вспомогательные методы безопасности -----
    def is_default_admin(self) -> bool:
        """
        Проверяет, используются ли учётные данные администратора по умолчанию.
        """
        return self.admin_username == "admin" and self.admin_password is None

    def get_admin_password_clear(self) -> str | None:
        """
        Возвращает пароль администратора в открытом виде
        (только для внутреннего использования).
        """
        if self.admin_password is None:
            return None
        return self.admin_password.get_secret_value()
