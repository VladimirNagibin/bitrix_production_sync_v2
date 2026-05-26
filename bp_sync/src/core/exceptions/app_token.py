from typing import Any

from .base import BaseAppException
from .enums import ErrorCode


class CipherError(BaseAppException):
    """Базовое исключение для операций шифрования."""

    DEFAULT_MESSAGE = "Cipher error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.CIPHER_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CipherError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class CipherEncryptionError(CipherError):
    """Возникает при ошибке шифрования."""

    DEFAULT_MESSAGE = "Cipher encryption error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CipherEncryptionError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.CIPHER_ENCRYPTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class CipherDecryptionError(CipherError):
    """Возникает при ошибке дешифрования."""

    DEFAULT_MESSAGE = "Cipher decryption error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CipherDecryptionError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.CIPHER_DECRYPTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class CipherInvalidTokenError(CipherDecryptionError):
    """Возникает, когда токен недействителен или повреждён."""

    DEFAULT_MESSAGE = "Cipher invalid token"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CipherInvalidTokenError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
        self.error_code = ErrorCode.CIPHER_INVALID_TOKEN


class CipherConfigurationError(CipherError):
    """Возникает при некорректной конфигурации шифратора."""

    DEFAULT_MESSAGE = "Cipher configuration error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует CipherConfigurationError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.CIPHER_CONFIGURATION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class TokenStorageError(BaseAppException):
    """Базовое исключение для ошибок хранилища токенов."""

    DEFAULT_MESSAGE = "Token storage error"

    def __init__(
        self,
        error_code: str | ErrorCode = ErrorCode.TOKEN_STORAGE_ERROR,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует TokenStorageError.

        Args:
            error_code: Код ошибки
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код (если применимо)
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(error_code, final_message, details, status_code)


class StorageConnectionError(TokenStorageError):
    """
    Возникает при ошибке подключения к Redis или выполнении Redis-команды.
    """

    DEFAULT_MESSAGE = "Storage connection error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует StorageConnectionError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.STORAGE_CONNECTION_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class TokenSaveError(TokenStorageError):
    """Возникает при ошибке сохранения токена."""

    DEFAULT_MESSAGE = "Token save error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует TokenSaveError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.TOKEN_SAVE_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class TokenDeleteError(TokenStorageError):
    """Возникает при ошибке удаления токена."""

    DEFAULT_MESSAGE = "Token delete error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует TokenDeleteError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.TOKEN_DELETE_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class InvalidTokenTypeError(TokenStorageError):
    """Возникает при передаче некорректного типа токена."""

    DEFAULT_MESSAGE = "Invalid token type error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует InvalidTokenTypeError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.INVALID_TOKEN_TYPE_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )


class TokenStorageInitError(TokenStorageError):
    """Возникает при ошибке инициализации хранилища токенов."""

    DEFAULT_MESSAGE = "Token storage init error"

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Инициализирует TokenStorageInitError.

        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали
            status_code: HTTP статус-код
        """
        super().__init__(
            error_code=ErrorCode.TOKEN_STORAGE_INIT_ERROR,
            message=message or self.DEFAULT_MESSAGE,
            details=details,
            status_code=status_code,
        )
