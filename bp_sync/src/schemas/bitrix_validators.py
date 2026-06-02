import zoneinfo

from collections.abc import Callable
from datetime import datetime, tzinfo
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, TypeVar, cast

from pydantic import AliasChoices, BaseModel

from core import settings
from core.exceptions.bitrix24 import (
    BitrixParseError,
    BitrixTypeError,
    BitrixValidationError,
)
from core.logger import logger


# ===== Типы и константы =====
EnumT = TypeVar("EnumT", bound=Enum)
SYSTEM_USER_ID = settings.bitrix24.system_user_id


# ===== Основной класс =====
class BitrixValidators:
    """
    Класс с общими валидаторами и преобразователями данных из Bitrix24.

    Содержит статические методы для нормализации, парсинга и валидации
    значений, приходящих из REST API Bitrix24.
    """

    # ----- Конфигурация -----
    _DEFAULT_TIMEZONE: ClassVar[tzinfo] = zoneinfo.ZoneInfo(
        settings.bitrix24.server_zone_info
    )

    # Реестр трансформеров типов: bitrix_type -> функция обработки
    _TRANSFORMERS: ClassVar[MappingProxyType[str, Callable[[Any], Any]]] = (
        MappingProxyType(
            {
                "str_none": lambda v: v if v else None,
                "int_none": lambda v: None if not v or v == "0" else int(v),
                "int_user": lambda v: BitrixValidators._sanitize_user_id(v),
                "bool_yn": lambda v: bool(v in ("Y", "1", 1, True)),
                "bool_none_yn": (
                    lambda v: BitrixValidators._to_optional_bool(v)
                ),
                "bool_10": lambda v: bool(v in ("Y", "1", 1, True)),
                "bool_none_10": (
                    lambda v: BitrixValidators._to_optional_bool(v)
                ),
                "datetime": (
                    lambda v: BitrixValidators._sanitize_datetime(
                        v, nullable=False
                    )
                ),
                "datetime_none": (
                    lambda v: BitrixValidators._sanitize_datetime(v)
                ),
                "datetime_alt_none": (
                    lambda v: BitrixValidators._sanitize_datetime(v)
                ),
                "float": lambda v: BitrixValidators._sanitize_float_value(v),
                "list": lambda v: BitrixValidators._sanitize_list_value(v),
                "list_in_int": (
                    lambda v: BitrixValidators._extract_first_int(v)
                ),
                "money": lambda v: BitrixValidators._sanitize_money_value(v),
                # "dict_none": (
                #    lambda v: (
                #       v.get("value") if v and isinstance(v, dict) else None)
                # ),
            }
        )
    )

    # ----- Публичные методы -----
    @classmethod
    def normalize_data(
        cls, data: Any, schema_class: type[BaseModel]
    ) -> dict[str, Any]:
        """
        Нормализует входные данные: очищает пустые значения, мапит алиасы
        и приводит типы согласно настройкам схемы.

        Args:
            data: Входные данные (ожидается словарь).
            schema_class: Класс Pydantic-модели, чьи метаданные используются.

        Returns:
            Словарь с нормализованными полями.

        Raises:
            BitrixTypeError: Если входные данные не являются словарем.
            BitrixValidationError: При ошибке обработки конкретного поля.
        """
        if not isinstance(data, dict):
            logger.error(f"Expected dict, got {type(data).__name__}")
            raise BitrixTypeError(
                field_name="root",
                value=data,
                reason=f"Expected dict, got {type(data).__name__}",
            )

        alias_map = cls._build_alias_to_field_map(schema_class)
        result: dict[str, Any] = {}

        processed_data: dict[str, Any] = cast("dict[str, Any]", data)
        for key, value in list(processed_data.items()):
            field_name = alias_map.get(key)
            if not field_name:
                # Неизвестное поле – сохраняем как есть
                # (попадёт в extra_fields)
                result[key] = value
                continue
            try:
                field_info = schema_class.model_fields[field_name]
                bitrix_type = cls._get_field_bitrix_type(field_info)

                # Если тип не указан, возвращаем исходное значение
                if bitrix_type is None:
                    result[field_name] = value
                    continue

                # Применяем трансформер
                result[field_name] = cls.apply_field_transformer(
                    field_name, value, bitrix_type
                )
            except BitrixValidationError:
                raise
            except Exception as e:
                logger.critical(
                    (
                        f"Unexpected error processing field '{field_name}': "
                        f"{e!s}"
                    ),
                    exc_info=True,
                )
                raise BitrixValidationError(
                    field_name=field_name,
                    value=value,
                    reason=f"Internal processing error: {e!s}",
                ) from e

        return result

    @staticmethod
    def parse_numeric_string(value: Any) -> float | None:
        """
        Парсит числовые строки с различными форматами (включая пробелы как
        разделители тысяч и запятые как разделители дробной части).

        Args:
            value: Входное значение

        Returns:
            Число с плавающей точкой или None
        """
        if value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        if not isinstance(value, str):
            return None

        cleaned = BitrixValidators._remove_whitespace(value)

        # Замена запятой как десятичного разделителя на точку
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            logger.warning("Failed to parse numeric string: %r", value)
            return None

    @staticmethod
    def apply_field_transformer(
        field_name: str,
        value: Any,
        bitrix_type: str,
    ) -> Any:
        """Находит и применяет трансформер согласно bitrix_type."""
        transformer = BitrixValidators._TRANSFORMERS.get(bitrix_type)
        if not transformer:
            return value

        try:
            return transformer(value)
        except BitrixValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Transformer '{bitrix_type}' failed for field "
                f"'{field_name}': {e!s}"
            )
            raise BitrixParseError(
                field_name=field_name,
                value=value,
                reason=f"Transformer error ({bitrix_type}): {e!s}",
            ) from e

    # ----- Приватные вспомогательные методы -----
    @staticmethod
    def _remove_whitespace(text: str) -> str:
        """Удаляет все виды пробелов из строки."""
        for ch in ("\xa0", "\u2009", "\u202f", " "):
            text = text.replace(ch, "")
        return text

    @classmethod
    def _build_alias_to_field_map(
        cls, schema_class: type[BaseModel]
    ) -> dict[str, str]:
        """
        Строит словарь маппинга: любой возможный ключ (имя поля или алиас)
        → имя атрибута поля в классе.
        """
        mapping: dict[str, str] = {}
        for field_name, field_info in schema_class.model_fields.items():
            mapping[field_name] = field_name
            val_alias = field_info.validation_alias

            if isinstance(val_alias, str):
                mapping[val_alias] = field_name
            elif isinstance(val_alias, AliasChoices):
                for choice in val_alias.choices:
                    if isinstance(choice, str):
                        mapping[choice] = field_name
        return mapping

    @staticmethod
    def _get_field_bitrix_type(field_info: Any) -> str | None:
        """
        Извлекает значение 'bitrix_type' из json_schema_extra поля.
        """
        extra = field_info.json_schema_extra
        if isinstance(extra, dict):
            return cast("dict[str, Any]", extra).get("bitrix_type")
        return None

    @staticmethod
    def _to_optional_bool(value: Any) -> bool | None:
        """Преобразует Y/N, 1/0, True/False в bool или None."""
        if (
            value is True
            or value == 1
            or value == "1"
            or (isinstance(value, str) and value.strip().upper() == "Y")
        ):
            return True
        if (
            value is False
            or value == 0
            or value == "0"
            or (isinstance(value, str) and value.strip().upper() == "N")
        ):
            return False
        return None

    @staticmethod
    def _sanitize_user_id(value: Any) -> int:
        """
        Нормализует ID пользователя: преобразует в int, подставляя
        SYSTEM_USER_ID при ошибке.
        """
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid user ID '{value}'. "
                f"Replacing with SYSTEM_USER_ID ({SYSTEM_USER_ID})"
            )
            return SYSTEM_USER_ID
        else:
            return int_val if int_val else SYSTEM_USER_ID

    @staticmethod
    def _sanitize_float_value(value: Any) -> float:
        """
        Преобразует значение в число с плавающей точкой.

        Args:
            v: Любое значение для преобразования в float

        Returns:
            float: Нормализованное число (0 в случае ошибки)
        """
        if value is None or value == "":
            return 0.0
        try:
            normalized = str(value).strip()
            normalized = BitrixValidators._remove_whitespace(normalized)
            if "," in normalized and "." not in normalized:
                normalized = normalized.replace(",", ".")
            return float(normalized)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _sanitize_datetime(
        value: Any, nullable: bool = True, tz: tzinfo | None = None
    ) -> datetime | None:
        """
        Парсит строковые даты в объекты datetime.

        Поддерживает форматы:
        - ISO формат: '2023-12-31T23:59:59'
        - Bitrix формат: '31.12.2023 23:59:59'

        Args:
            value: Значение для парсинга
            tz: Часовой пояс (по умолчанию DEFAULT_TIMEZONE).

        Returns:
            datetime | None: Объект datetime или
            None или Текущее время если nullable=False при ошибке
        """
        target_tz = tz or BitrixValidators._DEFAULT_TIMEZONE

        default_value = None if nullable else datetime.now(target_tz)

        if not value:
            return default_value

        if isinstance(value, datetime):
            return (
                value
                if value.tzinfo is not None
                else value.replace(tzinfo=target_tz)
            )

        if not isinstance(value, str):
            return default_value

        # Попытка парсинга формата Bitrix: "31.12.2023 23:59:59"
        try:
            dt = datetime.strptime(value, "%d.%m.%Y %H:%M:%S")  # noqa: DTZ007
            return dt.replace(tzinfo=target_tz)
        except ValueError:
            pass

        # Попытка парсинга ISO формата
        if "T" in value or "-" in value:
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return (
                    dt
                    if dt.tzinfo is not None
                    else dt.replace(tzinfo=target_tz)
                )
            except ValueError:
                pass

        logger.warning(f"Failed to parse datetime string: {value!r}")
        return default_value

    @staticmethod
    def _sanitize_enum(
        value: Any, enum_type: type[EnumT], default: EnumT
    ) -> EnumT:
        """
        Преобразует значения в член enum.

        Args:
            value: Значение для преобразования
            enum_type: Тип enum
            default: Значение по умолчанию

        Returns:
            EnumT: Значение enum
        """
        if value is None or value == "":
            return default

        try:
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            return enum_type(value)
        except (ValueError, KeyError, TypeError):
            logger.debug(
                f"Failed to map value {value!r} to enum "
                f"{enum_type.__name__}. Using default {default!r}"
            )
            return default

    @staticmethod
    def _sanitize_list_value(value: Any) -> list[Any]:
        """
        Нормализует значение в список.

        Args:
            v: Значение для нормализации

        Returns:
            list: Нормализованный список (пустой список в случае ошибки)
        """
        if value is None:
            return []
        if isinstance(value, list):
            return cast("list[Any]", value)  # type: ignore[redundant-cast]

        logger.warning(
            f"Expected list, got {type(value).__name__}. "
            "Returning empty list."
        )
        return []

    @staticmethod
    def _extract_first_int(value: Any) -> int:
        """
        Извлекает первое значение из списка и преобразует в int.

        Args:
            value: Значение для обработки

        Returns:
            int: Первый элемент списка как int (0 в случае ошибки)
        """
        if not value:
            return 0
        if isinstance(value, list) and value:
            try:
                first_element = cast("Any", value[0])
                return int(first_element)
            except (ValueError, TypeError):
                return 0
        return 0

    @staticmethod
    def _sanitize_money_value(value: Any) -> float:
        """
        Преобразует денежные значения из формата Bitrix в float.

        Поддерживает форматы:
        - "1953500|KZT" → 1953500.0
        - Числовые значения
        - Строки с числами

        Args:
            value: Значение для преобразования

        Returns:
            float: Числовое значение (0.0 в случае ошибки)
        """
        if value is None:
            return 0.0
        try:
            if isinstance(value, str) and "|" in value:
                # Обработка формата "1953500|KZT"
                number_part = value.split("|")[0].strip()
                return BitrixValidators._sanitize_float_value(number_part)
            return BitrixValidators._sanitize_float_value(value)
        except (ValueError, TypeError, IndexError):
            return 0.0
