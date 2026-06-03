from __future__ import annotations

import json
import threading

from enum import Enum
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Self,
    TypedDict,
    cast,
)

from pydantic import (
    AliasChoices,
    BaseModel,
    model_validator,
)

from core import settings
from core.exceptions.schemas import (
    ComparisonError,
    FieldComparisonError,
)
from core.logger import logger

from .bitrix_validators import BitrixValidators
from .field_models import CommunicationChannel, FieldValue


if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from pydantic.fields import FieldInfo


# ===== Конфигурация типов для extra_fields =====
class FieldConfig(TypedDict):
    alias: str | list[str]
    type: str
    comment: str


# ===== Основной миксин =====
class DataMappingMixin(BaseModel):
    """
    Миксин для маппинга данных между Pydantic‑моделями, Bitrix24 и БД.
    Обеспечивает ленивую загрузку конфигурации дополнительных полей.
    """

    # ----- Конфигурация (переопределяется в наследниках) -----
    EXTRA_FIELDS_FILENAME: ClassVar[str] = ""

    # ----- Приватные кеши (раздельные для каждого класса) -----
    _extra_fields_cache: ClassVar[dict[str, FieldConfig] | None] = None
    _extra_fields_loaded: ClassVar[bool] = False
    _extra_fields_lock: ClassVar[threading.Lock] = threading.Lock()

    # ----- Публичный метод доступа к конфигурации -----
    @classmethod
    def get_extra_fields(cls) -> dict[str, FieldConfig]:
        """
        Возвращает конфигурацию дополнительных полей, загружая её при первом
        вызове.
        """
        if not cls._extra_fields_loaded:
            with cls._extra_fields_lock:
                if not cls._extra_fields_loaded:  # Double-check
                    cls._load_extra_fields()
        return cls._extra_fields_cache or {}

    @property
    def extra_fields_config(self) -> dict[str, FieldConfig]:
        """Удобный доступ к конфигурации extra_fields через экземпляр."""
        return self.get_extra_fields()

    # Реестр трансформеров типов: bitrix_type -> функция обработки
    _TRANSFORMERS: ClassVar[MappingProxyType[str, Callable[[Any], Any]]] = (
        MappingProxyType(
            {
                "str_none": lambda v: v if v else "",
                "int_none": lambda v: "" if not v or v == "0" else v,
                "int_user": lambda v: "" if not v or v == "0" else v,
                "bool_yn": lambda v: "Y" if v else "N",
                "bool_none_yn": (
                    lambda v: "Y"
                    if v is True
                    else ("N" if v is False else "")
                ),
                "bool_10": lambda v: "1" if v else "0",
                "bool_none_10": (
                    lambda v: "1"
                    if v is True
                    else ("0" if v is False else "")
                ),
                "datetime": (lambda v: DataMappingMixin._format_datetime(v)),
                "datetime_none": (
                    lambda v: DataMappingMixin._format_datetime(v)
                ),
                "datetime_alt_none": (
                    lambda v: v.strftime("%d.%m.%Y %H:%M:%S") if v else ""
                ),
                "money": lambda v: DataMappingMixin._format_money(v),
            }
        )
    )

    # ----- Автоматическая инициализация подклассов -----
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Вызывается автоматически при создании подкласса."""
        super().__init_subclass__(**kwargs)
        # Инициализируем пер-класс переменные,
        # чтобы не было "утечки" между наследниками
        cls._extra_fields_cache = None
        cls._extra_fields_loaded = False

    # ----- Загрузка конфигурации из JSON -----
    @classmethod
    def _load_extra_fields(cls) -> None:
        """
        Загружает конфигурацию из JSON-файла, указанного в
        EXTRA_FIELDS_FILENAME.
        """
        if cls._extra_fields_loaded:
            return

        filename = cls.EXTRA_FIELDS_FILENAME
        if not filename:
            logger.debug(f"{cls.__name__}: EXTRA_FIELDS_FILENAME not set")
            cls._extra_fields_cache = {}
            cls._extra_fields_loaded = True
            return

        cls._extra_fields_cache = cls._load_data_from_file(filename)
        cls._extra_fields_loaded = True
        return

    @classmethod
    def _load_data_from_file(cls, filename: str) -> dict[str, FieldConfig]:
        """
        Загружает конфигурацию из JSON-файла, указанного в filename.
        """
        file_path = settings.app.base_dir / "config" / filename
        if not file_path.is_file():
            logger.warning(
                f"{cls.__name__}: config not found: {file_path.resolve()}"
            )
            return {}

        try:
            with file_path.open("r", encoding="utf-8") as f:
                raw_config = cast("dict[str, Any]", json.load(f))

            # Валидация и приведение типов
            validated: dict[str, FieldConfig] = {}
            required_keys = {"alias", "type", "comment"}
            for key, value in raw_config.items():
                if isinstance(value, dict):
                    v_dict = cast("dict[str, Any]", value)
                    if required_keys.issubset(v_dict.keys()):
                        validated[key] = FieldConfig(
                            alias=v_dict["alias"],
                            type=str(v_dict["type"]),
                            comment=str(v_dict["comment"]),
                        )
                    else:
                        missing = required_keys - set(v_dict.keys())
                        logger.warning(
                            f"{cls.__name__}: field '{key}' is missing "
                            f"required keys {missing}, skipping"
                        )
                else:
                    logger.warning(
                        f"{cls.__name__}: field '{key}' is not a dictionary, "
                        "skipping"
                    )
            logger.info(
                f"{cls.__name__}: loaded {len(validated)} extra fields from "
                f"{file_path}"
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"{cls.__name__}: JSON decode error in {file_path}: {e}"
            )
            return {}
        except Exception as e:  # noqa: BLE001
            logger.exception(
                f"{cls.__name__}: unexpected error loading config: {e}"
            )
            return {}
        else:
            return validated

    # ----- Валидаторы -----
    @model_validator(mode="after")
    def collect_additional_fields(self) -> DataMappingMixin:
        """
        Обрабатывает дополнительные поля (__pydantic_extra__) и сохраняет их
        в extra_fields.
        """
        # __pydantic_extra__ автоматически заполняется Pydantic при
        # extra="allow"
        if (
            not hasattr(self, "__pydantic_extra__")
            or not self.__pydantic_extra__
        ):
            return self

        alias_map = self._build_alias_map(self.extra_fields_config)

        processed: dict[str, Any] = {}

        extra_fields = dict(self.__pydantic_extra__)
        for alias, value in extra_fields.items():
            field_config = alias_map.get(alias)
            if not field_config:
                continue
            field_name = field_config["name"]
            field_type = field_config["type"]
            try:
                processed[field_name] = (
                    BitrixValidators.apply_field_transformer(
                        field_name, value, field_type
                    )
                )

            except Exception as e:  # noqa: BLE001
                logger.error(
                    f"Failed to transform extra field '{field_name}': {e}"
                )
        # Устанавливаем результат и очищаем __pydantic_extra__
        object.__setattr__(self, "extra_fields", processed)
        object.__setattr__(self, "__pydantic_extra__", {})
        return self

    def _build_alias_map(
        self, data: dict[str, FieldConfig]
    ) -> dict[str, dict[str, str]]:
        # Маппинг: алиас → { "name": имя_поля, "type": тип_преобразования }
        alias_map: dict[str, dict[str, str]] = {}
        for internal_name, config in data.items():
            aliases = config["alias"]
            mapping_value = {
                "name": internal_name,
                "type": config["type"],
            }
            if isinstance(aliases, str):
                alias_map[aliases] = mapping_value
            elif isinstance(aliases, list):  # pyright: ignore[reportUnnecessaryIsInstance]
                for alias in aliases:
                    alias_map[alias] = mapping_value

        return alias_map

    # ----- Публичные методы -----
    def get_changes(
        self,
        other: Self,
    ) -> dict[str, dict[str, Any]]:
        """
        Сравнивает текущую сущность с другой и возвращает различия.

        Args:
            other: Сущность для сравнения

        Returns:
            Словарь с различиями в формате
            {поле: {internal: значение, external: значение}}

        Raises:
            ComparisonError: Если типы сущностей не совпадают.

        Example:
            >>> changes = old_entity.get_changes(new_entity)
            >>> print(changes)
            {'name': {'internal': 'Old', 'external': 'New'}}
        """

        if not isinstance(other, self.__class__):
            raise ComparisonError(
                message=(
                    f"Expected entity of type {self.__class__.__name__}, "
                    f"got {type(other).__name__}"
                )
            )
        internal_id = getattr(self, "internal_id", "-")
        logger.debug(
            f"Comparing entities: {self.__class__.__name__} "
            f"(ID: {internal_id})"
        )

        differences: dict[str, dict[str, Any]] = {}

        model_class = self.__class__

        for field_name, field_info in model_class.model_fields.items():
            # Пропускаем поля, помеченные как исключённые из сравнения
            if self._is_excluded_from_comparison(field_info):
                continue

            try:
                old_value = getattr(self, field_name)
                new_value = getattr(other, field_name)

                if field_name == "extra_fields":
                    diff_extra_fields = self._get_diff_extra_fields(
                        old_value, new_value
                    )
                    if diff_extra_fields:
                        differences.update(diff_extra_fields)
                    continue

                if not self._are_values_equal(
                    field_name, old_value, new_value
                ):
                    differences[field_name] = {
                        "internal": old_value,
                        "external": new_value,
                    }
                    logger.debug(
                        f"Field '{field_name}' changed: "
                        f"{old_value} -> {new_value}"
                    )
            except AttributeError as e:
                logger.warning(
                    f"Field '{field_name}' missing in one of the entities: "
                    f"{e!s}"
                )
            except (TypeError, ValueError) as e:
                logger.error(
                    f"Invalid comparison for field '{field_name}': {e!s}"
                )
            except ComparisonError as e:
                logger.error(
                    f"Comparison error for field '{field_name}': {e!s}"
                )
            except Exception as e:  # noqa: BLE001
                # Любая другая непредвиденная ошибка логируется,
                # но не прерывает процесс
                logger.critical(
                    f"Unexpected error comparing field '{field_name}': {e!s}",
                    exc_info=True,
                )

        logger.info(
            f"Found {len(differences)} changes in {self.__class__.__name__}"
        )
        return differences

    # ----- Вспомогательные методы сравнения -----
    def _is_excluded_from_comparison(self, field_info: Any) -> bool:
        """
        Проверяет, помечено ли поле как исключаемое из сравнения.
        """
        exclude_flag = self._get_json_extra_value(
            field_info, "exclude_from_comparison"
        )
        return exclude_flag is True

    def _get_json_extra_value(self, field_info: Any, field_name: str) -> Any:
        """
        Извлекает значение из json_schema_extra поля по ключу.
        """
        json_extra = field_info.json_schema_extra
        if isinstance(json_extra, dict):
            return cast("dict[str, Any]", json_extra).get(field_name)
        return None

    def _get_diff_extra_fields(
        self, old: Any, new: Any
    ) -> dict[str, dict[str, Any]] | None:
        """
        Сравнивает два словаря extra_fields и возвращает различия.
        """
        if not isinstance(old, dict) or not isinstance(new, dict):
            return None

        # Приводим типы для статического анализа
        old_dict: dict[str, Any] = cast("dict[str, Any]", old)
        new_dict: dict[str, Any] = cast("dict[str, Any]", new)

        differences: dict[str, dict[str, Any]] = {}

        # Ключи, которые есть в old, но отсутствуют или отличаются в new
        for key, old_val in old_dict.items():
            if key not in new:
                differences[key] = {"internal": old_val, "external": None}
                logger.debug(
                    f"Extra field '{key}' removed: {old_val} -> None"
                )
            elif not self._are_values_equal(key, old_val, new[key]):
                differences[key] = {"internal": old_val, "external": new[key]}
                logger.debug(
                    f"Extra field '{key}' changed: {old_val} -> {new[key]}"
                )

        # Ключи, которые появились в new
        for key, new_val in new_dict.items():
            if key not in old:
                differences[key] = {"internal": None, "external": new_val}
                logger.debug(f"Extra field '{key}' added: None -> {new_val}")

        return differences if differences else None

    def _are_values_equal(
        self, field_name: str, value1: Any, value2: Any
    ) -> bool:
        """
        Сравнивает два значения с учетом специальных типов данных.

        Args:
            field_name: Имя поля для специальной обработки
            value1: Первое значение
            value2: Второе значение

        Returns:
            True если значения равны, иначе False
        """
        # Оба значения None
        if value1 is None and value2 is None:
            return True
        # Проверка специальных полей (например, company_id)
        if self._handle_special_fields(field_name, value1, value2):
            return True
        # Одно из значений None
        if value1 is None or value2 is None:
            return False
        # Сравнение в зависимости от типов
        return self._compare_by_type(field_name, value1, value2)

    def _compare_by_type(
        self, field_name: str, value1: Any, value2: Any
    ) -> bool:
        """
        Сравнивает значения в зависимости от их типа.

        Использует последовательные проверки isinstance для чёткой типизации.
        """
        # Оба значения — перечисления (Enum)
        if isinstance(value1, Enum) and isinstance(value2, Enum):
            return bool(value1.value == value2.value)

        # Pydantic-модели
        if isinstance(value1, BaseModel) and isinstance(value2, BaseModel):
            return value1.model_dump() == value2.model_dump()

        # Оба значения — списки или словари → прямое сравнение
        if isinstance(value1, list | dict) and isinstance(
            value2, list | dict
        ):
            # Оператор == для коллекций корректен, типы элементов не важны
            return value1 == value2

        # Все остальные случаи (включая примитивы, даты, UUID и т.д.)
        try:
            return bool(value1 == value2)
        except (TypeError, ValueError) as e:
            type1 = type(value1).__name__  # pyright: ignore[reportUnknownArgumentType]
            raise FieldComparisonError(
                field_name,
                f"Cannot compare values of types "
                f"{type1} and {type(value2).__name__}: {e!s}",
            ) from e

    # ----- Обработка специальных полей -----
    def _handle_special_fields(
        self, field_name: str, value1: Any, value2: Any
    ) -> bool:
        """
        Обрабатывает специальные случаи для определенных полей.

        Returns:
            True если значения считаются равными для специального поля
        """
        special_handlers: dict[str, Any] = {
            "company_id": self._compare_company_id,
        }

        handler = special_handlers.get(field_name)
        if handler is None:
            return False
        try:
            return bool(handler(value1, value2))
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"Special handler for '{field_name}' failed: {e!s}",
                exc_info=True,
            )
            return False

    @staticmethod
    def _compare_company_id(value1: Any, value2: Any) -> bool:
        """Сравнивает значения company_id с учетом 0 и None."""
        return value1 in (0, None) and value2 in (0, None)

    @model_validator(mode="before")  # pyright: ignore[misc]
    @classmethod
    def preprocess_data(cls, data: Any) -> Any:
        return BitrixValidators.normalize_data(data, schema_class=cls)

    # ----- Преобразование в словарь для БД -----
    def model_dump_db(self, exclude_unset: bool = False) -> dict[str, Any]:
        """
        Возвращает словарь для сохранения в БД, исключая служебные поля.
        """
        result: dict[str, Any] = {}
        data = self.model_dump(exclude_unset=exclude_unset)
        model_class = self.__class__
        for field_name, value in data.items():
            field_info = model_class.model_fields[field_name]
            # Пропускаем поля, помеченные как исключённые из сравнения
            if self._is_excluded_from_db(field_info):
                continue  # list, dict_none_str, dict_none_dict
            bitrix_type = self._get_json_extra_value(
                field_info, "bitrix_type"
            )
            if bitrix_type in ("str_none", "int_none"):
                if not value:
                    result[field_name] = None
                else:
                    result[field_name] = value
                continue
            result[field_name] = value

            # elif key in self.FIELDS_BY_TYPE_ALT.get("dict_none_str", []):
            #     if value is None:
            #         data[key] = None
            #     else:
            #         data[key] = value["value"]
            # elif key in self.FIELDS_BY_TYPE_ALT.get("dict_none_dict", []):
            #     if value is None:
            #         data[key] = None
            #     else:
            #         data[key] = value["value"]["text_field"]
        return result

    # ----- Вспомогательные методы -----
    def _is_excluded_from_db(self, field_info: Any) -> bool:
        """
        Проверяет, помечено ли поле как исключаемое из выгрузки в db.
        """
        exclude_flag = self._get_json_extra_value(
            field_info, "exclude_from_db"
        )
        return exclude_flag is True

    # ----- Преобразование в словарь для Bitrix -----
    def to_bitrix_dict(
        self,
        alias_choice: int = 1,
        exclude_none: bool = True,
        exclude_unset: bool = True,
    ) -> dict[str, Any]:
        """
        Преобразует модель Pydantic в словарь, оптимизированный для
        Bitrix API.

        Метод выполняет комплексное преобразование данных модели с учетом:
        - выбора схемы алиасов через alias_choice
        - исключения служебных и неопределенных полей
        - применения кастомных преобразований для специфичных полей Bitrix

        Args:
            alias_choice (int, optional): Выбор схемы алиасов.
                Возможные значения:
                1 - алиасы для базовых сущностей (по умолчанию, первые)
                2 - алиасы для обобщённых сущностей (item, вторые)
                <1 - преобразуется в 1
                >2 - преобразуется в 2
                Default: 1.
            exclude_none: Исключать поля со значением None.
            exclude_unset: Исключать поля, которые не были явно установлены.

        Returns:
            dict[str, Any]: Словарь с данными, готовыми к отправке в
            Bitrix API

        Raises:
            ValidationError: При ошибках преобразования данных

        Example:
            >>> contact = ContactModel(name="John", phone="+123456789")
            >>> bitrix_data = contact.to_bitrix_dict(alias_choice=1)
            {'NAME': 'John', 'PHONE_WORK': '+123456789'}
        """
        result: dict[str, Any] = {}
        fields_set = self.model_fields_set  # множество установленных полей
        # Итерируемся по полям модели, чтобы получить доступ к исходным
        # значениям и информации о полях (FieldInfo).
        for field_name, field_info in self.__class__.model_fields.items():
            # Пропускаем, если поле не установлено и exclude_unset=True
            if exclude_unset and field_name not in fields_set:
                continue

            value = getattr(self, field_name, None)

            # Пропускаем, если значение None и exclude_none=True
            if exclude_none and value is None:
                continue

            if self._is_excluded_from_bitrix(field_info):
                continue

            if field_name == "extra_fields":
                if isinstance(value, dict):
                    for extra_name, extra_value in cast(
                        "dict[str, Any]", value
                    ).items():
                        try:
                            if config := self.extra_fields_config.get(
                                extra_name
                            ):
                                alias = config["alias"]
                                bitrix_type = config["type"]
                                if isinstance(alias, str) and (
                                    transformer := self._TRANSFORMERS.get(
                                        bitrix_type
                                    )
                                ):
                                    result[alias] = transformer(extra_value)
                        except Exception as e:  # noqa: BLE001
                            logger.warning(f"{e}")
                continue

            # Получаем финальный алиас для поля на основе alias_choice
            field_alias = self._get_field_alias(
                field_name, field_info, alias_choice
            )
            bitrix_type = self._get_json_extra_value(
                field_info, "bitrix_type"
            )
            # Применяем преобразования к исходному значению.
            # Теперь isinstance(value, FieldValue) будет работать корректно.
            transformed_value = self._apply_field_transformations(
                bitrix_type, value, alias_choice
            )

            # Если после преобразования значение стало None,
            # не добавляем его в результат.
            if exclude_none and transformed_value is None:
                continue

            result[field_alias] = transformed_value
        return result

    # ----- Вспомогательные методы -----
    def _is_excluded_from_bitrix(self, field_info: Any) -> bool:
        """
        Проверяет, помечено ли поле как исключаемое из Bitrix24.
        """
        exclude_flag = self._get_json_extra_value(
            field_info, "exclude_from_bitrix"
        )
        return exclude_flag is True

    def _get_field_alias(
        self, field_name: str, field_info: FieldInfo, alias_choice: int
    ) -> str:
        """
        Вспомогательный метод для получения алиаса поля из FieldInfo.
        """
        validation_alias = field_info.validation_alias
        if isinstance(validation_alias, AliasChoices):
            # Безопасный выбор алиаса с проверкой границ
            choice_index = max(
                0, min(alias_choice - 1, len(validation_alias.choices) - 1)
            )
            return validation_alias.choices[choice_index]  # type: ignore

        # Если AliasChoices не используется, пробуем получить обычный алиас
        return field_info.alias or field_name

    def _apply_field_transformations(
        self, bitrix_type: str, value: Any, alias_choice: int
    ) -> Any:
        """Применяет все необходимые преобразования к значению поля"""

        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], FieldValue)
        ):
            typed_field_value_list = cast("list[FieldValue]", value)
            return [
                self._transform_field_value(bitrix_type, v, alias_choice)
                for v in typed_field_value_list
            ]
        if isinstance(value, FieldValue):
            return self._transform_field_value(
                bitrix_type, value, alias_choice
            )
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], CommunicationChannel)
        ):
            typed_comm_channel_list = cast(
                "list[CommunicationChannel]", value
            )
            return self._transform_comm_channel(
                typed_comm_channel_list, alias_choice
            )

        if transformer := self._TRANSFORMERS.get(bitrix_type):
            return transformer(value)
        return cast("Any", value)
        # if isinstance(value, bool):
        #     return self._transform_boolean_value(field_alias, value)
        # elif isinstance(value, datetime):
        #     return self._transform_datetime_value(field_alias, value)
        # elif isinstance(value, float):
        #     return self._transform_float_value(field_alias, value)
        # elif isinstance(value, UUID):
        #     return str(value)
        # elif isinstance(value, tuple):
        #     return self._transform_tuple_value(
        #         field_alias, value, alias_choice
        #     )
        # else:
        #     return self._transform_numeric_value(field_alias, value)

    def _transform_field_value(
        self, bitrix_type: str, value: FieldValue, alias_choice: int
    ) -> dict[str, Any]:
        """
        Преобразует объект FieldValue в формат, ожидаемый Bitrix API.
        Рекурсивно применяет алиасы для вложенных моделей.
        """
        result: dict[str, Any] = {}
        # Обрабатываем поле value_id, если оно есть
        if hasattr(value, "value_id") and value.value_id is not None:
            # Предполагаем, что алиас для value_id - это 'valueId'
            result["valueId"] = value.value_id

        # Рекурсивно обрабатываем вложенное поле 'value'
        if hasattr(value, "value") and value.value is not None:  # pyright: ignore[reportUnnecessaryComparison]
            nested_value = value.value
            if isinstance(nested_value, BaseModel):
                # Если вложенное значение - это другая Pydantic-модель
                # (например, FieldText),
                # используем model_dump(by_alias=True), чтобы применить ее
                # алиасы.
                result["value"] = nested_value.to_bitrix_dict(alias_choice)
            else:
                # Если это простое значение (например, строка),
                # просто присваиваем его.
                if transformer := self._TRANSFORMERS.get(bitrix_type):
                    result["value"] = transformer(nested_value)
                else:
                    result["value"] = nested_value

        return result

    def _transform_comm_channel(
        self, value: list[CommunicationChannel], _alias_choice: int
    ) -> list[Any]:
        """
        Преобразует объект CommunicationChannel в формат, ожидаемый
        Bitrix API.
        """
        return [
            cast("BaseModel", val).model_dump(by_alias=True) for val in value
        ]

    @classmethod
    def _format_datetime(cls, value: datetime | None) -> str:
        """Преобразует datetime в строковый формат"""

        if value is None:
            return ""
        iso_format = value.strftime("%Y-%m-%dT%H:%M:%S%z")
        if iso_format and iso_format[-5] in ("+", "-"):
            iso_format = f"{iso_format[:-2]}:{iso_format[-2:]}"
        return iso_format

    @classmethod
    def _format_money(cls, value: Any) -> Any:
        """Преобразует числовые значения для специальных полей"""
        return f"{value}|{settings.bitrix24.currency}"

    def _transform_tuple_value(
        self, _field_alias: str, value: Any, alias_choice: int
    ) -> Any:
        """Преобразует перечисления с двойственными полями"""
        try:
            return value[alias_choice - 1]
        except Exception:  # noqa: BLE001
            return value[0]
