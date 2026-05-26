import asyncio

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core import settings
from core.exceptions.app_token import (
    CipherConfigurationError,
    CipherDecryptionError,
    CipherEncryptionError,
    CipherInvalidTokenError,
)
from core.logger import logger


class TokenCipher:
    """
    Асинхронный шифратор/дешифратор на основе Fernet.

    Использует asyncio.to_thread для вызова синхронных криптографических
    операций в отдельном потоке, чтобы не блокировать цикл событий.
    """

    def __init__(self, encryption_key: str):
        """
        Инициализирует шифратор.

        Args:
            encryption_key: Строка с ключом шифрования
                            (ожидается валидный Fernet-ключ).
        Raises:
            CipherConfigurationError: Если ключ имеет неверный формат.
        """
        self._validate_key_not_empty(encryption_key)
        try:
            self._cipher = Fernet(encryption_key.encode())
        except (ValueError, TypeError) as e:
            logger.critical(f"Invalid encryption key format: {e}")
            raise CipherConfigurationError(
                message="Invalid encryption key configuration"
            ) from e

    async def encrypt(self, data: str) -> bytes:
        """
        Асинхронно шифрует строку.

        Args:
            data: Исходная строка (не пустая).

        Returns:
            Зашифрованные данные в виде байтов.

        Raises:
            EncryptionError: При любой ошибке в процессе шифрования.
        """
        self._validate_data_not_empty(data, "encryption")
        try:
            encrypted = await asyncio.to_thread(self._encrypt_sync, data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise CipherEncryptionError(
                message="Token encryption error"
            ) from e
        else:
            return encrypted

    async def decrypt(self, encrypted_data: bytes) -> str:
        """
        Асинхронно дешифрует байтовые данные.

        Args:
            encrypted_data: Зашифрованные данные в виде байтов.

        Returns:
            Расшифрованная строка.

        Raises:
            InvalidTokenError: Если токен повреждён или недействителен.
            DecryptionError: При любой другой ошибке дешифрования.
        """
        self._validate_bytes_not_empty(encrypted_data)
        try:
            decrypted = await asyncio.to_thread(
                self._decrypt_sync, encrypted_data
            )
        except InvalidToken as e:
            logger.warning(f"Invalid token decryption attempt: {e}")
            raise CipherInvalidTokenError(
                message="Invalid or corrupted token"
            ) from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise CipherDecryptionError(
                message="Token decryption error"
            ) from e
        else:
            return decrypted

    def _encrypt_sync(self, data: str) -> bytes:
        """
        Синхронное шифрование (выполняется в отдельном потоке).
        """
        return self._cipher.encrypt(  # type: ignore[no-any-return]
            data.encode()
        )

    def _decrypt_sync(self, encrypted_data: bytes) -> str:
        """
        Синхронное дешифрование (выполняется в отдельном потоке).
        """
        return self._cipher.decrypt(  # type: ignore[no-any-return]
            encrypted_data
        ).decode()

    # ----- Вспомогательные валидаторы -----

    @staticmethod
    def _validate_key_not_empty(key: str) -> None:
        """Проверяет, что ключ не пустой."""
        if not key or not key.strip():
            raise CipherConfigurationError(
                message="Encryption key cannot be empty"
            )

    @staticmethod
    def _validate_data_not_empty(data: str, operation: str) -> None:
        """Проверяет, что данные для шифрования не пустые."""
        if not data:
            raise CipherEncryptionError(
                message=f"Cannot perform {operation} on empty string"
            )

    @staticmethod
    def _validate_bytes_not_empty(data: bytes) -> None:
        """Проверяет, что байтовые данные для дешифрования не пустые."""
        if not data:
            raise CipherDecryptionError(message="Cannot decrypt empty data")


# ===== Фабрика (Dependency Injection) =====
@lru_cache(maxsize=1)
def get_token_cipher() -> TokenCipher:
    """
    Фабрика для получения экземпляра TokenCipher (синглтон).

    Использует ключ из настроек приложения. Результат кешируется через
    lru_cache, чтобы избежать повторной инициализации криптообъекта.

    Returns:
        Настроенный экземпляр TokenCipher.

    Raises:
        CipherConfigurationError: Если ключ шифрования отсутствует или
        неверен.
    """
    encryption_key = settings.encryption_key
    if not encryption_key:
        logger.critical("ENCRYPTION_KEY is not set in settings")
        raise CipherConfigurationError(
            message="ENCRYPTION_KEY is not configured"
        )
    return TokenCipher(encryption_key)
