from enum import Enum, StrEnum


class ErrorCode(StrEnum):
    """
    Перечисление внутренних кодов ошибок приложения.
    """

    # Base
    BASE_ERROR = "BASE_ERROR"

    # File & Storage
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    FILE_NOT_FOUND_ERROR = "FILE_NOT_FOUND_ERROR"
    ZIP_EXTRACTION_ERROR = "ZIP_EXTRACTION_ERROR"
    FILE_NOT_ZIP_ERROR = "FILE_NOT_ZIP_ERROR"
    FILE_SIZE_ERROR = "FILE_SIZE_ERROR"
    CSV_FILE_PARSING_ERROR = "CSV_FILE_PARSING_ERROR"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"

    # Database
    ERROR_WORKING_WITH_DB = "ERROR_WORKING_WITH_DB"
    ERROR_LOADING_DATA_TO_DB = "ERROR_LOADING_DATA_TO_DB"
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"

    # Data Processing
    DATA_PROCESSING_ERROR = "DATA_PROCESSING_ERROR"
    PRICE_PROCESSING_ERROR = "PRICE_PROCESSING_ERROR"
    EMAIL_FETCH_ERROR = "EMAIL_FETCH_ERROR"
    DRIVE_API_ERROR = "DRIVE_API_ERROR"
    EXCEL_PROCESSING_ERROR = "EXCEL_PROCESSING_ERROR"
    SUPPLIER_DATA_ERROR = "SUPPLIER_DATA_ERROR"

    # Network & API
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DOWNLOAD_ERROR = "DOWNLOAD_ERROR"
    API_ERROR = "API_ERROR"

    # Settings
    SETTINGS_ERROR = "SETTINGS_ERROR"
    INVALID_SETTINGS_VALUE_ERROR = "INVALID_SETTINGS_VALUE_ERROR"

    # redis
    REDIS_CLIENT_ERROR = "REDIS_CLIENT_ERROR"
    REDIS_CONNECTION_ERROR = "REDIS_CONNECTION_ERROR"
    REDIS_AUTH_ERROR = "REDIS_AUTH_ERROR"
    REDIS_NOT_INIT_ERROR = "REDIS_NOT_INIT_ERROR"
    REDIS_TIME_OUT_ERROR = "REDIS_TIME_OUT_ERROR"


class ErrorMessages(Enum):
    """Стандартизированные сообщения об ошибках с кодами."""

    NOT_ZIP = ("FILE_NOT_ZIP", "Файл должен быть в формате ZIP")
    INVALID_ZIP = ("INVALID_ZIP", "Файл не является валидным ZIP архивом")
    SIZE_LIMIT = ("FILE_TOO_LARGE", "Размер файла превышает лимит")
    SAVE_FAILED = ("SAVE_FAILED", "Ошибка при сохранении файла")
    VALIDATION_FAILED = (
        "VALIDATION_FAILED",
        "Ошибка при проверке ZIP архива",
    )
    CSV_NOT_FOUND = ("CSV_NOT_FOUND", "CSV файл не найден внутри архива")
    UNZIP_FAILED = ("ZIP_EXTRACTION_ERROR", "Не удалось распаковать архив")

    def __init__(self, code: str, message: str) -> None:
        self._code = code
        self._message = message

    @property
    def code(self) -> str:
        """Код ошибки."""
        return self._code

    @property
    def message(self) -> str:
        """Текстовое сообщение об ошибке."""
        return self._message
