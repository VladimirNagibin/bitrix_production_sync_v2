from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ----------------------------------------------------------------------
# Исключения для обработки данных
# ----------------------------------------------------------------------


class DataProcessingError(BaseAppException):
    """Базовое исключение для ошибок обработки данных."""

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.DATA_PROCESSING_ERROR,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        msg = message or "Ошибка при обработки данных"
        super().__init__(error_code, msg, details)


class PriceProcessingError(DataProcessingError):
    """Ошибка при обработке прайс-листа."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        msg = message or "Ошибка при обработке прайс-листа"
        super().__init__(
            error_code=ErrorCode.PRICE_PROCESSING_ERROR,
            message=msg,
            details=details,
        )


class SupplierDataError(PriceProcessingError):
    """Ошибка при работе с данными поставщика."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        msg = message or "Ошибка при чтении или записи данных поставщика"
        super().__init__(message=msg, details=details)
        self.error_code = ErrorCode.SUPPLIER_DATA_ERROR


class ExcelProcessingError(PriceProcessingError):
    """Ошибка при чтении/записи Excel-файлов."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        msg = message or "Ошибка при чтении или записи Excel"
        super().__init__(message=msg, details=details)
        self.error_code = ErrorCode.EXCEL_PROCESSING_ERROR
