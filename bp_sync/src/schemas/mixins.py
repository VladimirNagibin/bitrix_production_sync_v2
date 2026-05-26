from contextlib import suppress
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Self, cast
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from pydantic.fields import FieldInfo

from core.exceptions.schemas import (
    ComparisonError,
    FieldComparisonError,
)
from core.logger import logger
from models.communications import CommunicationChannel

from .bitrix_validators import BitrixValidators

# from .enums import CURRENCY
from .fields import (
    EXCLUDED_CHANGES_FIELDS,
    FIELDS_BY_TYPE,
    FIELDS_BY_TYPE_ALT,
)


CURRENCY = "KZT"


class DataMappingMixin(BaseModel):
    # Константа для полей, исключаемых из сравнения
    EXCLUDED_FIELDS: ClassVar[set[str]] = EXCLUDED_CHANGES_FIELDS
    EXTRA_FIELDS_BY_TYPE: ClassVar[dict[str, list[str]]] = {}
    FIELDS_BY_TYPE: ClassVar[dict[str, Any]] = FIELDS_BY_TYPE
    FIELDS_BY_TYPE_ALT: ClassVar[dict[str, Any]] = FIELDS_BY_TYPE_ALT

    # ----- Валидаторы -----
    @model_validator(mode="after")
    def collect_extra_fields(self) -> "DataMappingMixin":
        # __pydantic_extra__ автоматически заполняется Pydantic при
        # extra="allow"
        if hasattr(self, "__pydantic_extra__") and self.__pydantic_extra__:
            extra_fields = dict(self.__pydantic_extra__)
            object.__setattr__(self, "extra_fields", extra_fields)
            # Очищаем __pydantic_extra__ чтобы не дублировать данные
            object.__setattr__(self, "__pydantic_extra__", {})
        return self

    # ----- Публичные методы -----
    def get_changes(
        self,
        entity: Self | None,
        exclude_fields: set[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Сравнивает текущую сущность с другой и возвращает различия.

        Args:
            entity: Сущность для сравнения
            exclude_fields: Поля для исключения из сравнения

        Returns:
            Словарь с различиями в формате
            {поле: {internal: значение, external: значение}}

        Example:
            >>> changes = old_entity.get_changes(new_entity)
            >>> print(changes)
            {'name': {'internal': 'Old', 'external': 'New'}}
        """
        if entity is None:
            raise ComparisonError(message="Comparison entity cannot be None")

        if not isinstance(entity, self.__class__):
            raise ComparisonError(
                message=(
                    f"Expected entity of type {self.__class__.__name__}, "
                    f"got {type(entity).__name__}"
                )
            )
        internal_id = getattr(self, "internal_id", "-")
        logger.debug(
            f"Comparing entities: {self.__class__.__name__} "
            f"(ID: {internal_id})"
        )
        if exclude_fields is None:
            exclude_fields = self.EXCLUDED_FIELDS

        differences: dict[str, dict[str, Any]] = {}

        model_class = self.__class__
        fields = model_class.model_fields

        for field_name in fields:
            if field_name in exclude_fields:
                continue
            try:
                old_value = getattr(self, field_name)
                new_value = getattr(entity, field_name)

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
    def _are_values_equal(
        self,
        field_name: str,
        value1: Any,
        value2: Any,
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

        # Оба значения — Pydantic-модели → рекурсивное сравнение через дамп
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

    def _compare_company_id(self, value1: Any, value2: Any) -> bool:
        """Сравнивает значения company_id с учетом 0 и None."""
        return value1 in (0, None) and value2 in (0, None)

    @model_validator(mode="before")  # pyright: ignore[misc]
    @classmethod
    def preprocess_data(cls, data: Any) -> Any:
        return BitrixValidators.normalize_empty_values(
            data, fields=cls.FIELDS_BY_TYPE
        )

    def model_dump_db(self, exclude_unset: bool = False) -> dict[str, Any]:
        data = self.model_dump(exclude_unset=exclude_unset)
        for key in self.FIELDS_BY_TYPE_ALT.get("list", []):
            with suppress(KeyError):
                del data[key]
        for key in self.FIELDS_BY_TYPE_ALT.get("dict_none_str", []):
            with suppress(KeyError):
                del data[key]
        for key in self.FIELDS_BY_TYPE_ALT.get("dict_none_dict", []):
            with suppress(KeyError):
                del data[key]
        for key, value in data.items():
            if (
                key in self.FIELDS_BY_TYPE_ALT.get("str_none", [])
                and not value
            ) or (
                key in self.FIELDS_BY_TYPE_ALT.get("int_none", [])
                and (value is None or not int(value))
            ):
                data[key] = None

            elif key in self.FIELDS_BY_TYPE_ALT.get("dict_none_str", []):
                if value is None:
                    data[key] = None
                else:
                    data[key] = value["value"]
            elif key in self.FIELDS_BY_TYPE_ALT.get("dict_none_dict", []):
                if value is None:
                    data[key] = None
                else:
                    data[key] = value["value"]["text_field"]
        return data  # pyright: ignore[no-any-return]

    # Константы для преобразований
    _BOOLEAN_FIELDS_TO_STRING: ClassVar[set[str]] = {
        "UF_CRM_60D2AFAEB32CC",
        "UF_CRM_1632738559",
        "UF_CRM_1623830089",
        "UF_CRM_60D97EF75E465",
        "UF_CRM_61974C16DBFBF",
    }  # transform to: 1 - True, 0 - False

    _COMMUNICATION_TIME_FIELDS: ClassVar[set[str]] = {
        "LAST_COMMUNICATION_TIME",
        "lastCommunicationTime",
    }

    _SPECIAL_BOOLEAN_FIELDS: ClassVar[dict[str, Any]] = {
        "webformId": (1, 0)  # (true_value, false_value)
    }

    _EXCLUDED_FIELDS: ClassVar[set[str]] = {"ID", "id", "external_id"}

    _DUAL_ENUM: ClassVar[set[str]] = {
        "payment_type",
        "UF_CRM_1632738315",
        "shipment_type",
        "UF_CRM_1655141630",
        "ufCrm_SMART_INVOICE_1651114959541",
        "ufCrm_62B53CC5A2EDF",
    }

    _MONEY_FIELDS: ClassVar[set[str]] = {"UF_CRM_1760872964", "half_amount"}

    def to_bitrix_dict_(self, alias_choice: int = 1) -> dict[str, Any]:
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

        Returns:
            dict[str, Any]: Словарь с данными, готовыми к отправке в
            Bitrix API

        Raises:
            ValidationError: При ошибках преобразования данных

        Notes:
            - Поля со значением None исключаются из результата
            - Неизмененные (unset) поля игнорируются
            - Применяются преобразования через _apply_field_transformations
            - Исключает поля из _EXCLUDED_FIELDS

        Example:
            >>> contact = ContactModel(name="John", phone="+123456789")
            >>> bitrix_data = contact.to_bitrix_dict(alias_choice=2)
            {'NAME': 'John', 'PHONE_WORK': '+123456789'}
        """

        # Строим маппинг алиасов
        alias_mapping = self._build_alias_mapping(alias_choice)

        # Получаем данные модели
        data = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True,
        )

        # Применяем маппинг алиасов и преобразования
        result: dict[str, Any] = {}

        for field_name, value in data.items():
            # Получаем финальный алиас для поля
            field_alias = alias_mapping.get(field_name, field_name)

            # Пропускаем исключенные поля
            if field_alias in self._EXCLUDED_FIELDS:
                continue

            # Применяем преобразования
            transformed_value = self._apply_field_transformations(
                field_alias, value, alias_choice
            )
            result[field_alias] = transformed_value

        return result

    def _build_alias_mapping(self, alias_choice: int) -> dict[str, str]:
        """Строит маппинг имен полей на выбранные алиасы"""
        alias_mapping: dict[str, Any] = {}

        for field_name, field_info in self.__class__.model_fields.items():
            validation_alias = field_info.validation_alias

            if isinstance(validation_alias, AliasChoices):
                # Безопасный выбор алиаса с проверкой границ
                choice_index = max(
                    0,
                    min(alias_choice - 1, len(validation_alias.choices) - 1),
                )
                alias_mapping[field_name] = validation_alias.choices[
                    choice_index
                ]

        return alias_mapping

    def to_bitrix_dict(self, alias_choice: int = 1) -> dict[str, Any]:
        """
        Преобразует модель Pydantic в словарь, оптимизированный для
        Bitrix API.
        """
        result: dict[str, Any] = {}

        # Итерируемся по полям модели, чтобы получить доступ к исходным
        # значениям и информации о полях (FieldInfo).
        for field_name, field_info in self.__class__.model_fields.items():
            # Получаем значение поля напрямую из объекта.
            # Это будет исходный Python-объект
            # (например, экземпляр FieldValue), а не словарь.
            value = getattr(self, field_name, None)

            # Пропускаем, если значение не установлено (unset) или равно None.
            # Это имитирует поведение exclude_unset=True и exclude_none=True.
            if value is None:
                continue

            # Получаем финальный алиас для поля на основе alias_choice
            field_alias = self._get_field_alias(
                field_name, field_info, alias_choice
            )

            # Пропускаем исключенные поля (например, 'ID', 'id')
            if field_alias in self._EXCLUDED_FIELDS:
                continue
            # Применяем преобразования к исходному значению.
            # Теперь isinstance(value, FieldValue) будет работать корректно.
            transformed_value = self._apply_field_transformations(
                field_alias, value, alias_choice
            )

            # Если после преобразования значение стало None,
            # не добавляем его в результат.
            if transformed_value is None:
                continue

            result[field_alias] = transformed_value
        return result

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
        self, field_alias: str, value: Any, alias_choice: int
    ) -> Any:
        """Применяет все необходимые преобразования к значению поля"""

        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], FieldValue)
        ):
            typed_field_value_list = cast("list[FieldValue]", value)
            return [
                self._transform_field_value(v, alias_choice)
                for v in typed_field_value_list
            ]
        if isinstance(value, FieldValue):
            return self._transform_field_value(value, alias_choice)
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
        if isinstance(value, bool):
            return self._transform_boolean_value(field_alias, value)
        elif isinstance(value, datetime):
            return self._transform_datetime_value(field_alias, value)
        elif isinstance(value, float):
            return self._transform_float_value(field_alias, value)
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, tuple):
            return self._transform_tuple_value(
                field_alias, value, alias_choice
            )
        else:
            return self._transform_numeric_value(field_alias, value)

    def _transform_field_value(
        self, value: "FieldValue", alias_choice: int
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
        if hasattr(value, "value") and value.value is not None:  # pyright: ignore[comparison-overlap]
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
                result["value"] = nested_value

        return result

    def _transform_comm_channel(
        self, value: list["CommunicationChannel"], _alias_choice: int
    ) -> list[Any]:
        """
        Преобразует объект CommunicationChannel в формат, ожидаемый
        Bitrix API.
        """
        return [
            cast("BaseModel", val).model_dump(by_alias=True) for val in value
        ]

    def _transform_boolean_value(self, field_alias: str, value: bool) -> Any:
        """Преобразует булево значение в нужный формат"""
        if field_alias in self._SPECIAL_BOOLEAN_FIELDS:
            true_val, false_val = self._SPECIAL_BOOLEAN_FIELDS[field_alias]
            return true_val if value else false_val
        elif field_alias in self._BOOLEAN_FIELDS_TO_STRING:
            return "1" if value else "0"
        else:
            return "Y" if value else "N"

    def _transform_datetime_value(
        self, field_alias: str, value: datetime
    ) -> str:
        """Преобразует datetime в строковый формат"""
        if field_alias in self._COMMUNICATION_TIME_FIELDS:
            return value.strftime("%d.%m.%Y %H:%M:%S")
        else:
            # Стандартный ISO формат с часовым поясом
            # iso_format = value.isoformat()
            # Убедимся, что часовой пояс в правильном формате
            # if (
            #     iso_format and iso_format[-5] in ("+", "-") and
            #     ":" not in iso_format[-5:]
            # ):
            #    iso_format = f"{iso_format[:-2]}:{iso_format[-2:]}"
            iso_format = value.strftime("%Y-%m-%dT%H:%M:%S%z")
            if iso_format and iso_format[-5] in ("+", "-"):
                iso_format = f"{iso_format[:-2]}:{iso_format[-2:]}"
            return iso_format

    def _transform_numeric_value(self, field_alias: str, value: Any) -> Any:
        """Преобразует числовые значения для специальных полей"""
        if field_alias in (
            FIELDS_BY_TYPE["int_none"] + FIELDS_BY_TYPE["enums"]
        ):
            return "" if value == 0 else value
        return value

    def _transform_float_value(self, field_alias: str, value: Any) -> Any:
        """Преобразует числовые значения для специальных полей"""
        if field_alias in self._MONEY_FIELDS:
            return f"{value}|{CURRENCY}"
        return value

    def _transform_tuple_value(
        self, _field_alias: str, value: Any, alias_choice: int
    ) -> Any:
        """Преобразует перечисления с двойственными полями"""
        try:
            return value[alias_choice - 1]
        except Exception:  # noqa: BLE001
            return value[0]


class FieldText(BaseModel):
    text_field: str | None = Field(
        None, validation_alias=AliasChoices("TEXT", "text")
    )  # TEXT
    type_field: str | None = Field(
        "HTML", validation_alias=AliasChoices("TYPE", "type")
    )  # TYPE (HTML/TEXT)

    def to_bitrix_dict(self, alias_choice: int) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name, None)
            if value is None:
                continue

            # Получаем финальный алиас для поля на основе alias_choice
            field_alias = self._get_field_alias(field_info, alias_choice)

            result[field_alias] = value

        return result

    def _get_field_alias(
        self, field_info: FieldInfo, alias_choice: int
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
        return field_info.alias or field_info.name  # type: ignore

    model_config = ConfigDict(populate_by_name=True)


class FieldValue(BaseModel):
    value_id: int | None = Field(None, alias="valueId")  # id value
    value: str | FieldText = Field(..., alias="value")  # value

    model_config = ConfigDict(populate_by_name=True)

    @property
    def text(self) -> str | None:
        """
        Возвращает текстовое значение вне зависимости от типа поля value.
        """
        content = self.value
        if isinstance(content, str):
            return content
        return content.text_field
