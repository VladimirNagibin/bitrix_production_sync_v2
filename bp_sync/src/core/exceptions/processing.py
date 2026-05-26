"""
Модуль исключений для обработки данных.

Содержит иерархию исключений, возникающих при обработке данных:
прайс-листов, поставщиков, Excel-файлов и других операций.
"""

from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения для обработки данных =====
class DataProcessingError(BaseAppException):
    """Базовое исключение для ошибок обработки данных."""

    DEFAULT_MESSAGE = "Data processing error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.DATA_PROCESSING_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует DataProcessingError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


# ===== Исключения для прайс-листов =====
class PriceProcessingError(DataProcessingError):
    """Ошибка при обработке прайс-листа."""

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует PriceProcessingError.

        Args:
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.PRICE_PROCESSING_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class SupplierDataError(PriceProcessingError):
    """Ошибка при работе с данными поставщика."""

    DEFAULT_MESSAGE = "Supplier data operation failed"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует SupplierDataError.

        Args:
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.SUPPLIER_DATA_ERROR


class ExcelProcessingError(PriceProcessingError):
    """Ошибка при чтении/записи Excel-файлов."""

    DEFAULT_MESSAGE = "Excel file processing error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует ExcelProcessingError.

        Args:
            message: Сообщение об ошибке (на английском)
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.EXCEL_PROCESSING_ERROR
