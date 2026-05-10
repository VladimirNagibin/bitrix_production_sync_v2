from pathlib import Path
from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


# ----------------------------------------------------------------------
# Исключения, связанные с файловой системой
# ----------------------------------------------------------------------


class FileSystemError(BaseAppException):
    """Базовое исключение для операций с файловой системой."""

    def __init__(
        self,
        path: Path | str,
        error_code: str | ErrorCode = ErrorCode.FILE_PROCESSING_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        self.path = str(path)
        msg = message or f"Ошибка при работе с файлом: {self.path}"
        super().__init__(error_code, msg, details, status_code)


class FileAppNotFoundError(FileSystemError, FileNotFoundError):
    """Файл или директория не найдены."""

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        msg = message or f"Файл не найден: {path_str}"
        super().__init__(
            path=path_str,
            error_code=ErrorCode.FILE_NOT_FOUND_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class FileNotZipError(FileSystemError):
    """Файл не является ZIP-архивом."""

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        msg = message or f"Расширение файла не zip: {path_str}"
        super().__init__(
            path=path_str,
            error_code=ErrorCode.FILE_NOT_ZIP_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class ZipExtractionError(FileSystemError):
    """Ошибка при распаковке ZIP-архива."""

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        msg = message or f"Ошибка распаковки файла: {path_str}"
        super().__init__(
            path=path_str,
            error_code=ErrorCode.ZIP_EXTRACTION_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class FileTooLargeError(FileSystemError):
    """Размер файла превышает допустимый лимит."""

    def __init__(
        self,
        path: Path | str,
        file_size: int | None = None,
        max_file_size: int | None = None,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        if not message:
            file_size_str = f"({file_size} bytes)" if file_size else ""
            max_size_str = (
                f"(max: {max_file_size} bytes)" if max_file_size else ""
            )
            message = (
                f"Размер файла{file_size_str} превышает максимальный"
                f"{max_size_str}: {path}"
            )
        super().__init__(
            path=path_str,
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=message,
            details=details,
            status_code=status_code,
        )


class CsvParsingError(FileSystemError):
    """Ошибка при парсинге CSV-файла."""

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        msg = message or f"Ошибка парсинга CSV файла: {path_str}"
        super().__init__(
            path=path_str,
            error_code=ErrorCode.CSV_FILE_PARSING_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )


class FileUploadError(FileSystemError):
    """Ошибка при загрузке файла (например, на сервер или в облако)."""

    def __init__(
        self,
        path: Path | str,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        path_str = str(path)
        msg = message or f"Ошибка загрузки файла: {path_str}"
        super().__init__(
            path=path_str,
            error_code=ErrorCode.FILE_UPLOAD_ERROR,
            message=msg,
            details=details,
            status_code=status_code,
        )
