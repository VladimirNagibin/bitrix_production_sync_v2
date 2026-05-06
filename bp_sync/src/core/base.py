from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils import LogLevel


class AppSettings(BaseSettings):
    project_name: str = "bp_sync"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    log_level: LogLevel = LogLevel.DEBUG
    base_dir: Path = Path(__file__).resolve().parent.parent

    # Логирование
    log_to_file: bool = True
    logging_file_max_bytes: int = 50_000_000  # 50 МБ
    logging_backup_count: int = 5

    model_config = SettingsConfigDict(
        env_prefix="APP_", case_sensitive=True, extra="ignore"
    )

    @property
    def is_dev(self) -> bool:
        return self.reload or self.log_level == LogLevel.DEBUG


class SeqSettings(BaseSettings):
    enabled: bool = False
    url: str = "http://localhost:5341"
    api_key: str = ""
    level: str = LogLevel.DEBUG
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="SEQ_")
