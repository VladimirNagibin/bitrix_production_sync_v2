import zoneinfo

from collections.abc import Callable
from datetime import datetime, tzinfo
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, TypeVar, cast

from core import settings
from core.exceptions.bitrix24 import (
    BitrixParseError,
    BitrixTypeError,
    BitrixValidationError,
)
from core.logger import logger


# ===== Вспомогательные типы и константы =====
EnumT = TypeVar("EnumT", bound=Enum)
T = TypeVar("T")
SYSTEM_USER_ID = settings.bitrix24.system_user_id


# ===== Основной класс =====
class BitrixValidators:
    """
    Класс с общими валидаторами и преобразователями данных из Bitrix24.

    Содержит статические методы для нормализации, парсинга и валидации
    значений, приходящих из REST API Bitrix24.
    """

    # ----- Настройки класса -----

    DEFAULT_TIMEZONE: tzinfo = zoneinfo.ZoneInfo(
        settings.bitrix24.server_zone_info
    )

    # Список полей, содержащих ID пользователей.
    # Требуют специальной обработки (проверка на валидность ID - не 0).
    _USER_FIELDS: frozenset[str] = frozenset(
        {
            "CREATED_BY_ID",
            "created_by_id",
            "MODIFY_BY_ID",
            "modify_by_id",
            "updatedBy",
        }
    )

    # Словарь трансформеров типов.
    # Используется MappingProxyType для защиты от случайных изменений.
    _TRANSFORMERS: ClassVar[MappingProxyType[str, Callable[[Any], Any]]] = (
        MappingProxyType(
            {
                "str_none": lambda v: v if v else None,
                "int_none": lambda v: None if not v or v == "0" else v,
                "bool": lambda v: bool(v in ("Y", "1", 1, True)),
                "bool_none": lambda v: bool(v in ("Y", "1", 1, True)),
                "datetime": lambda v: BitrixValidators.parse_datetime(v),
                "datetime_none": lambda v: BitrixValidators.parse_datetime(v),
                "float": lambda v: BitrixValidators.normalize_float(v),
                "list": lambda v: BitrixValidators.normalize_list(v),
                "list_in_int": lambda v: BitrixValidators.list_in_int(v),
                # "dict_none": (
                #    lambda v: (
                #       v.get("value") if v and isinstance(v, dict) else None)
                # ),
                "money": lambda v: BitrixValidators.normalize_money(v),
            }
        )
    )

    @staticmethod
    def normalize_empty_values(
        data: Any, fields: dict[str, list[str]]
    ) -> dict[str, Any]:
        """
        Нормализует входные данные: очищает пустые значения и приводит типы.

        Args:
            data: Входные данные (ожидается словарь)
            fields: Конфигурация полей в формате
                   {"тип_преобразования": ["поле1", "поле2"], ...}

        Returns:
            Нормализованный словарь с обработанными полями.

        Raises:
            BitrixTypeError: Если входные данные не являются словарем.
            BitrixValidationError: Если произошла ошибка при трансформации
            поля.
        """
        if not isinstance(data, dict):
            logger.error(f"Expected dict, got {type(data).__name__}")
            raise BitrixTypeError(
                field_name="root",
                value=data,
                reason=f"Expected dict, got {type(data).__name__}",
            )

        result: dict[str, Any] = {}
        excluded = BitrixValidators._get_excluded_fields()

        processed_data: dict[str, Any] = cast("dict[str, Any]", data)

        for field_name, value in list(processed_data.items()):
            try:
                # Применяем цепочку преобразований
                new_key, normalized_value = BitrixValidators._process_field(
                    field_name, value, fields
                )
                # Обновляем данные, если поле не исключено
                if new_key not in excluded:
                    result[new_key] = normalized_value
            except BitrixValidationError:
                # Пробрасываем ошибки валидации дальше
                raise
            except Exception as e:
                # Ловим неожиданные ошибки и заворачиваем в наше исключение
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
    def _process_field(
        field_name: str, value: Any, fields: dict[str, Any]
    ) -> tuple[str, Any]:
        """Обрабатывает одно поле через цепочку преобразований"""
        # 1. Переименование полей
        new_name = BitrixValidators._rename_field(field_name)

        # 2. Обработка пользовательских полей
        value = BitrixValidators._handle_user_field(new_name, value)

        # 3. Применение типизированных преобразований
        value = BitrixValidators._apply_transformers(new_name, value, fields)

        return new_name, value

    @staticmethod
    def _rename_field(field_name: str) -> str:
        """Переименовывает специальные поля"""
        if field_name == "id":
            return "ID"
        return field_name

    @staticmethod
    def _handle_user_field(field_name: str, value: Any) -> Any:
        """
        Обрабатывает поля, связанные с пользователями
        Если значение невалидно, подставляет SYSTEM_USER_ID.
        """
        if field_name not in BitrixValidators._USER_FIELDS:
            return value
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid user ID '{value}' in field '{field_name}'. "
                f"Replacing with SYSTEM_USER_ID ({SYSTEM_USER_ID})"
            )
            return SYSTEM_USER_ID
        else:
            return int_val if int_val else SYSTEM_USER_ID

    @staticmethod
    def _apply_transformers(
        field_name: str,
        value: Any,
        fields_config: dict[str, list[str]],
    ) -> Any:
        """Применяет преобразования в зависимости от типа поля"""
        # Ищем, какие типы применены к этому полю
        transformer_keys: list[str] = [
            key
            for key, field_list in fields_config.items()
            if field_name in field_list
        ]

        result_value = value
        for key in transformer_keys:
            transformer = BitrixValidators._TRANSFORMERS.get(key)
            if transformer:
                try:
                    result_value = transformer(result_value)
                except BitrixValidationError:
                    # Если трансформер выбросил наше исключение,
                    # пробрасываем его
                    raise
                except Exception as e:
                    # Оборачиваем неожиданные ошибки трансформера
                    logger.error(
                        f"Transformer '{key}' failed for field "
                        f"'{field_name}': {e!s}"
                    )
                    raise BitrixParseError(
                        field_name=field_name,
                        value=result_value,
                        reason=f"Transformer error ({key}): {e!s}",
                    ) from e
        return result_value

    @staticmethod
    def _get_excluded_fields() -> set[str]:
        """Возвращает набор исключенных полей"""
        # Замените на реальные исключенные поля из вашего класса
        return set()

    @staticmethod
    def normalize_float(v: Any) -> float:
        """
        Преобразует значение в число с плавающей точкой.

        Args:
            v: Любое значение для преобразования в float

        Returns:
            float: Нормализованное число (0 в случае ошибки)
        """
        if v is None or v == "":
            return 0.0
        try:
            return float(str(v).replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def parse_datetime(v: Any, tz: tzinfo | None = None) -> datetime | None:
        """
        Парсит строковые даты в объекты datetime.

        Поддерживает форматы:
        - ISO формат: '2023-12-31T23:59:59'
        - Bitrix формат: '31.12.2023 23:59:59'

        Args:
            v: Значение для парсинга
            tz: Часовой пояс (по умолчанию DEFAULT_TIMEZONE).

        Returns:
            datetime | None: Объект datetime или None при ошибке
        """
        if not v:
            return None

        target_tz = tz or BitrixValidators.DEFAULT_TIMEZONE

        if isinstance(v, datetime):
            return v if v.tzinfo is not None else v.replace(tzinfo=target_tz)

        # Bitrix формат
        if isinstance(v, str):
            try:
                dt = datetime.strptime(v, "%d.%m.%Y %H:%M:%S")  # noqa: DTZ007
                return dt.replace(tzinfo=target_tz)
            except ValueError:
                pass

            # ISO формат
            if "T" in v or "-" in v:
                try:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    return (
                        dt
                        if dt.tzinfo is not None
                        else dt.replace(tzinfo=target_tz)
                    )
                except ValueError:
                    pass
        logger.warning(f"Failed to parse datetime string: {v!r}")
        return None

    @staticmethod
    def convert_enum(v: Any, enum_type: type[EnumT], default: EnumT) -> EnumT:
        """
        Преобразует значения в член enum.

        Args:
            v: Значение для преобразования
            enum_type: Тип enum
            default: Значение по умолчанию

        Returns:
            EnumT: Значение enum
        """
        if v is None or v == "":
            return default

        try:
            if isinstance(v, str) and v.isdigit():
                v = int(v)
            return enum_type(v)
        except (ValueError, KeyError, TypeError):
            logger.debug(
                f"Failed to map value {v!r} to enum {enum_type.__name__}. "
                f"Using default {default!r}"
            )
            return default

    @staticmethod
    def normalize_list(v: Any) -> list[Any]:
        """
        Нормализует значение в список.

        Args:
            v: Значение для нормализации

        Returns:
            list: Нормализованный список (пустой список в случае ошибки)
        """
        if v is None:
            return []
        if isinstance(v, list):
            return cast("list[Any]", v)  # type: ignore[redundant-cast]

        logger.warning(
            f"Expected list, got {type(v).__name__}. Returning empty list."
        )
        return []

    @staticmethod
    def list_in_int(v: Any) -> int:
        """
        Извлекает первое значение из списка и преобразует в int.

        Args:
            v: Значение для обработки

        Returns:
            int: Первый элемент списка как int (0 в случае ошибки)
        """
        if not v:
            return 0

        if isinstance(v, list) and v:
            try:
                first_element = cast("Any", v[0])
                return int(first_element)
            except (ValueError, TypeError):
                return 0
        return 0

    @staticmethod
    def normalize_money(v: Any) -> float:
        """
        Преобразует денежные значения из формата Bitrix в float.

        Поддерживает форматы:
        - "1953500|KZT" → 1953500.0
        - Числовые значения
        - Строки с числами

        Args:
            v: Значение для преобразования

        Returns:
            float: Числовое значение (0.0 в случае ошибки)
        """
        if v is None:
            return 0.0

        try:
            if isinstance(v, str):
                # Обработка формата "1953500|KZT"
                if "|" in v:
                    number_part = v.split("|")[0].strip()
                    return float(number_part)
                else:
                    return float(v)
            else:
                return float(v)
        except (ValueError, TypeError, IndexError):
            return 0.0

    @staticmethod
    def parse_numeric_string(value: Any) -> float | None:
        """
        Универсальная функция для парсинга числовых строк с разными форматами
        """
        if value is None:
            return None

        if isinstance(value, int | float):
            return float(value)

        if isinstance(value, str):
            # Нормализуем пробелы и нестандартные символы
            normalized = value.strip()

            # Заменяем неразрывные пробелы и другие специальные пробелы
            normalized = normalized.replace("\xa0", " ")  # неразрывный пробел
            normalized = normalized.replace("\u2009", " ")  # тонкий пробел
            normalized = normalized.replace("\u202f", " ")  # неразрывный

            # Паттерны для разных форматов чисел
            # patterns = [
            # Формат с пробелами как разделителями тысяч: "27 300" -> 27300
            #    r"^(\d+)[\s]+(\d+)$",
            # Формат с пробелами и десятичной частью: "27 300,50" -> 27300.50
            #    r"^(\d+)[\s]+(\d+)[,.](\d+)$",
            # Просто число с запятой как десятичным разделителем
            #    r"^(\d+),(\d+)$",
            # Число с точкой как десятичным разделителем
            #    r"^(\d+)\.(\d+)$",
            # ]

            """
            # Пробуем разные паттерны
            for pattern in patterns:
                match = re.match(pattern, normalized)
                if match:
                    groups = match.groups()
                    if len(groups) == 2 and pattern == patterns[0]:
                        # "27 300" -> 27300
                        return float(groups[0] + groups[1])
                    elif len(groups) == 3 and pattern == patterns[1]:
                        # "27 300,50" -> 27300.50
                        return float(groups[0] + groups[1] + '.' + groups[2])
                    elif (
                        len(groups) == 2
                        and pattern in (patterns[2], patterns[3])
                    ):
                        # "27,50" -> 27.50 или "27.50" -> 27.50
                        return float(groups[0] + '.' + groups[1])
            """
            # Если паттерны не сработали, просто очищаем от всех нецифровых
            # символов кроме . и -
            # cleaned = re.sub(r'[^\d\.\-]', '', normalized)

            cleaned = normalized
            if cleaned:
                try:
                    return float(cleaned)
                except (ValueError, TypeError):
                    pass

        return None
