"""
Модуль исключений для работы с файловой системой.

Содержит иерархию исключений, возникающих при операциях с файлами и
директориями: чтение, запись, загрузка, распаковка архивов, парсинг CSV и т.д.
"""

from pathlib import Path
from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ===== Исключения, связанные с файловой системой =====
class FileSystemError(BaseAppException):
    """
    Базовое исключение для ошибок при работе с файловой системой.

    Содержит путь к файлу, вызвавшему ошибку.
    """

    DEFAULT_MESSAGE = "File system operation failed"

    def __init__(
        self,
        path: Path | str,
        error_code: str | ErrorCode = ErrorCode.FILE_PROCESSING_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует исключение FileSystemError.

        Args:
            path: Путь к файлу или директории
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        self._path = str(path)
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)

    @property
    def path(self) -> str:
        """Возвращает строковое представление пути к файлу."""
        return self._path


# ===== Исключения для файлов и директорий =====
class FileAppNotFoundError(FileSystemError, FileNotFoundError):
    """Исключение, возникающее когда файл или директория не найдены."""

    DEFAULT_MESSAGE = "File or directory not found"

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует FileNotFoundError.

        Args:
            path: Путь к отсутствующему файлу/директории
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            path=path,
            error_code=ErrorCode.FILE_NOT_FOUND_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class FileNotZipError(FileSystemError):
    """Исключение, возникающее когда файл не является ZIP-архивом."""

    DEFAULT_MESSAGE = "File is not a ZIP archive"

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует FileNotZipError.

        Args:
            path: Путь к файлу, который не является ZIP
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            path=path,
            error_code=ErrorCode.FILE_NOT_ZIP_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class ZipExtractionError(FileSystemError):
    """Исключение, возникающее при ошибке распаковки ZIP-архива."""

    DEFAULT_MESSAGE = "Failed to extract ZIP archive"

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует ZipExtractionError.

        Args:
            path: Путь к ZIP-архиву, который не удалось распаковать
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            path=path,
            error_code=ErrorCode.ZIP_EXTRACTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class FileTooLargeError(FileSystemError):
    """
    Исключение, возникающее когда размер файла превышает допустимый лимит.
    """

    DEFAULT_MESSAGE = "File size exceeds maximum allowed limit"

    def __init__(
        self,
        path: Path | str,
        file_size: int | None = None,
        max_file_size: int | None = None,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует FileTooLargeError.

        Args:
            path: Путь к файлу
            file_size: Фактический размер файла в байтах (опционально)
            max_file_size: Максимально допустимый размер в байтах опционально
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        # Формируем сообщение с деталями, если не передано явно
        if message is None:
            message = self._format_message_with_sizes(
                file_size, max_file_size, path
            )

        # Добавляем информацию о размерах в details, если они не были переданы
        extra_details: dict[str, Any] = {}
        if file_size is not None:
            extra_details["file_size_bytes"] = file_size
        if max_file_size is not None:
            extra_details["max_file_size_bytes"] = max_file_size

        # Объединяем переданные details с extra_details
        if details is None:
            final_details: dict[str, Any] = extra_details
        elif isinstance(details, dict):
            final_details = {**details, **extra_details}
        else:
            # Если details не словарь, оборачиваем его в поле original_details
            final_details = {"original_details": details, **extra_details}

        super().__init__(
            path=path,
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=message,
            details=final_details,
            status_code=status_code,
        )

    @staticmethod
    def _format_message_with_sizes(
        file_size: int | None,
        max_file_size: int | None,
        path: Path | str,
    ) -> str:
        """
        Форматирует сообщение с указанием размеров файла и лимита.

        Args:
            file_size: Размер файла в байтах (может отсутствовать)
            max_file_size: Максимальный размер в байтах (может отсутствовать)
            path: Путь к файлу

        Returns:
            Отформатированное сообщение.
        """
        parts = [f"File size exceeds limit: {path}"]
        if file_size is not None:
            parts.append(f"(size: {file_size} bytes)")
        if max_file_size is not None:
            parts.append(f"max: {max_file_size} bytes")
        return " ".join(parts)


class CsvParsingError(FileSystemError):
    """Исключение, возникающее при ошибке парсинга CSV-файла."""

    DEFAULT_MESSAGE = "Failed to parse CSV file"

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CsvParsingError.

        Args:
            path: Путь к CSV-файлу
            message: Сообщение об ошибке
            details: Дополнительные детали
                     (например, номер строки, ошибка парсера)
            status_code: HTTP статус-код
        """
        super().__init__(
            path=path,
            error_code=ErrorCode.CSV_FILE_PARSING_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class FileUploadError(FileSystemError):
    """
    Исключение, возникающее при ошибке загрузки файла на сервер или в облако.
    """

    DEFAULT_MESSAGE = "File upload failed"

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует FileUploadError.

        Args:
            path: Путь к файлу, который не удалось загрузить
            message: Сообщение об ошибке
            details: Дополнительные детали (например, причина отказа)
            status_code: HTTP статус-код
        """
        super().__init__(
            path=path,
            error_code=ErrorCode.FILE_UPLOAD_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
