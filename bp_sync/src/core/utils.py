from enum import StrEnum
from typing import Any

from .exceptions.settings import InvalidSettingsValueError


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseURL:
    @staticmethod
    def build(
        driver: str,
        user: str,
        password: str,
        host: str,
        port: int,
        database: str,
        **kwargs: Any,
    ) -> str:
        params = "&".join(f"{k}={v}" for k, v in kwargs.items())
        query = f"?{params}" if params else ""
        return f"{driver}://{user}:{password}@{host}:{port}/{database}{query}"


def validate_positive_int(field_name: str, v: int) -> int:
    if v <= 0:
        raise InvalidSettingsValueError(
            field_name,
            v,
            "Значение должно быть положительным",
        )
    return v
