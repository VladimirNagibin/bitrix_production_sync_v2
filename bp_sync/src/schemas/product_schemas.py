from __future__ import annotations

import math
import threading

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.exceptions.schemas import SchemaValidationError
from core.logger import logger

from .base_schemas import CommonFieldMixin
from .bitrix_validators import BitrixValidators
from .data_mapping import DataMappingMixin
from .field_models import FieldValue


if TYPE_CHECKING:
    from .data_mapping import FieldConfig
    from .enums import EntityTypeAbbr


# ===== Базовый класс для товаров в сущности (связка товар-сущность) =====
class BaseProductEntity(CommonFieldMixin):
    """
    Базовые поля для товаров, связанных с сущностью
    (сделка, лид, контакт и т.п.).
    """

    # ----- Основные поля -----
    product_name: str | None = Field(
        None,
        alias="productName",
        json_schema_extra={"bitrix_type": "str_none"},
        description="Название товара",
    )
    price: float | None = Field(
        None,
        alias="price",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Цена",
    )
    price_exclusive: float | None = Field(
        None,
        alias="priceExclusive",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Цена без налога со скидкой",
    )
    price_netto: float | None = Field(
        None,
        alias="priceNetto",
        json_schema_extra={"bitrix_type": "float_none"},
        description="PRICE_NETTO",
    )
    price_brutto: float | None = Field(
        None,
        alias="priceBrutto",
        json_schema_extra={"bitrix_type": "float_none"},
        description="PRICE_BRUTTO",
    )
    quantity: float | None = Field(
        None,
        alias="quantity",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Количество",
    )
    discount_type_id: int | None = Field(
        None,
        alias="discountTypeId",
        json_schema_extra={"bitrix_type": "int_none"},
        description="Тип скидки",
    )
    discount_rate: float | None = Field(
        None,
        alias="discountRate",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Величина скидки",
    )
    discount_sum: float | None = Field(
        None,
        alias="discountSum",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Сумма скидки",
    )
    tax_rate: float | None = Field(
        None,
        alias="taxRate",
        json_schema_extra={"bitrix_type": "float_none"},
        description="Налог",
    )
    tax_included: bool | None = Field(
        None,
        alias="taxIncluded",
        json_schema_extra={"bitrix_type": "bool_none_yn"},
        description="Налог включён в цену (Y/N)",
    )
    customized: bool | None = Field(
        None,
        alias="customized",
        json_schema_extra={"bitrix_type": "bool_none_yn"},
        description="Изменён",
    )
    measure_code: int | None = Field(
        None,
        alias="measureCode",
        json_schema_extra={"bitrix_type": "int_none"},
        description="Код единицы измерения",
    )
    measure_name: str | None = Field(
        None,
        alias="measureName",
        json_schema_extra={"bitrix_type": "str_none"},
        description="Единица измерения",
    )
    sort: int | None = Field(
        None,
        alias="sort",
        json_schema_extra={
            "bitrix_type": "int_none",
            "exclude_from_alternate_comparison": True,
        },
        description="Сортировка",
    )
    type: int | None = Field(
        None,
        alias="type",
        json_schema_extra={
            "bitrix_type": "int_none",
            "exclude_from_alternate_comparison": True,
        },
        description="TYPE",
    )
    store_id: int | None = Field(
        None,
        alias="storeId",
        json_schema_extra={
            "bitrix_type": "int_none",
            "exclude_from_alternate_comparison": True,
        },
        description="STORE_ID",
    )

    # ----- Валидаторы -----
    @field_validator("external_id", mode="before")  # pyright: ignore[misc]
    @classmethod
    def convert_str_to_int(cls, value: str | int) -> int:
        """Преобразует строковое представление ID в целое число."""
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value  # type: ignore[return-value]

    # ----- Конфигурация -----
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    # ----- Публичные методы -----
    def equals_ignore_owner(self, other: BaseProductEntity) -> bool:
        """Сравнивает два объекта, игнорируя исключённые поля"""

        for field_name, field_info in self.__class__.model_fields.items():
            if self._should_skip_comparison(field_info):
                continue

            value1 = getattr(self, field_name)
            value2 = getattr(other, field_name)

            if not self._is_values_equal(value1, value2):
                return False

        return True

    # ----- Вспомогательные методы -----
    def _should_skip_comparison(self, field_info: Any) -> bool:
        """
        Проверяет, нужно ли пропустить поле при сравнении.
        """
        # Исключаем поля из основного сравнения (get_changes)
        if self._is_excluded_from_comparison(field_info):
            return True
        # Исключаем поля из альтернативного сравнения (equals_ignore_owner)
        exclude_alt = self._get_json_extra_value(
            field_info, "exclude_from_alternate_comparison"
        )
        return exclude_alt is True

    @staticmethod
    def _is_values_equal(value1: Any, value2: Any, eps: float = 1e-6) -> bool:
        """
        Сравнивает два значения с учётом допустимой погрешности для float.
        """
        if isinstance(value1, float) and isinstance(value2, float):
            return math.isclose(value1, value2, rel_tol=eps)
        return bool(value1 == value2)


# ===== Классы для создания/обновления товаров в сущности =====
class ProductEntityCreate(BaseProductEntity, DataMappingMixin):
    """Схема для создания товара внутри сущности (связка)."""

    owner_id: int = Field(
        ...,
        alias="ownerId",
        json_schema_extra={
            "bitrix_type": "int",
            "exclude_from_alternate_comparison": True,
        },
        description="ID владельца",
    )
    owner_type: EntityTypeAbbr = Field(
        ...,
        alias="ownerType",
        json_schema_extra={
            "bitrix_type": "str",
            "exclude_from_alternate_comparison": True,
        },
        description="Тип владельца",
    )
    product_id: int = Field(
        ...,
        alias="productId",
        json_schema_extra={"bitrix_type": "int"},
        description="ID товара",
    )


class ProductEntityUpdate(BaseProductEntity):
    """Схема для частичного обновления товаров в сущности"""

    owner_id: int | None = Field(
        None,
        alias="ownerId",
        json_schema_extra={
            "bitrix_type": "int",
            "exclude_from_alternate_comparison": True,
        },
        description="ID владельца",
    )
    owner_type: EntityTypeAbbr | None = Field(
        None,
        alias="ownerType",
        json_schema_extra={
            "bitrix_type": "str",
            "exclude_from_alternate_comparison": True,
        },
        description="Тип владельца",
    )
    product_id: int | None = Field(
        None,
        alias="productId",
        json_schema_extra={"bitrix_type": "int"},
        description="ID товара",
    )


class ListProductEntity(BaseModel):
    """Схема для списка товаров, связанных с сущностью."""

    result: list[ProductEntityCreate]

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    def equals_ignore_owner(self, other: ListProductEntity) -> bool:
        """Сравнивает два списка продуктов, игнорируя owner-поля"""
        if len(self.result) != len(other.result):
            return False

        return all(
            item1.equals_ignore_owner(item2)
            for item1, item2 in zip(self.result, other.result, strict=True)
        )

    def to_bitrix_dict(self) -> list[dict[str, Any]]:
        """
        Преобразует список в формат для отправки в Bitrix API.
        """
        return [
            product_entity.to_bitrix_dict() for product_entity in self.result
        ]

    @property
    def count_products(self) -> int:
        """Возвращает количество товаров в списке."""
        return len(self.result)


# ===== Базовый класс для товаров (справочник товаров) =====
class BaseProduct(CommonFieldMixin):
    """
    Базовый класс для товаров (продуктов) из справочника.
    """

    # ----- Конфигурация загрузки свойств -----
    PROPERTIES_FILENAME: ClassVar[str] = "product_properties_fields.json"
    SIMPLE_PROPERTIES_FILENAME: ClassVar[str] = (
        "simple_product_properties_fields.json"
    )

    _properties_cache: ClassVar[dict[str, FieldConfig] | None] = None
    _simple_properties_cache: ClassVar[dict[str, FieldConfig] | None] = None
    _properties_loaded: ClassVar[bool] = False
    _properties_lock: ClassVar[threading.Lock] = threading.Lock()

    # ----- Поля -----
    code: str | None = Field(
        None,
        validation_alias=AliasChoices("CODE", "code"),
        json_schema_extra={"bitrix_type": "str_none"},
        description="Символьный код",
    )
    active: bool | None = Field(
        None,
        validation_alias=AliasChoices("ACTIVE", "active"),
        json_schema_extra={"bitrix_type": "bool_none_yn"},
        description="Активен",
    )
    sort: int | None = Field(
        None,
        validation_alias=AliasChoices("SORT", "sort"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="Сортировка",
    )
    xml_id: str | None = Field(
        None,
        validation_alias=AliasChoices("XML_ID", "xmlId"),
        json_schema_extra={"bitrix_type": "str_none"},
        description="Внешний код",
    )
    date_create: datetime | None = Field(
        None,
        validation_alias=AliasChoices("DATE_CREATE", "dateCreate"),
        json_schema_extra={"bitrix_type": "datetime_none"},
        description="Дата создания",
    )
    date_modify: datetime | None = Field(
        None,
        validation_alias=AliasChoices("TIMESTAMP_X", "timestampX"),
        json_schema_extra={"bitrix_type": "datetime_none"},
        description="Дата изменения",
    )
    modified_by: int | None = Field(
        None,
        validation_alias=AliasChoices("MODIFIED_BY", "modifiedBy"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="Кем изменён",
    )
    created_by: int | None = Field(
        None,
        validation_alias=AliasChoices("CREATED_BY", "createdBy"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="Кем создан",
    )
    catalog_id: int | None = Field(
        None,
        validation_alias=AliasChoices("CATALOG_ID", "iblockId"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="ID каталога",
    )
    section_id: int | None = Field(
        None,
        validation_alias=AliasChoices("SECTION_ID", "iblockSectionId"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="ID раздела",
    )
    price: float | None = Field(
        None,
        validation_alias=AliasChoices("PRICE", "price"),
        json_schema_extra={"bitrix_type": "float_none"},
        description="Цена (в каталоге отдельный справочник)",
    )
    currency_id: str | None = Field(
        None,
        validation_alias=AliasChoices("CURRENCY_ID", "currency_id"),
        json_schema_extra={"bitrix_type": "str_none"},
        description="Валюта (в каталоге отдельный справочник)",
    )
    vat_id: int | None = Field(
        None,
        validation_alias=AliasChoices("VAT_ID", "vatId"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="Ставка НДС",
    )
    vat_included: bool | None = Field(
        None,
        validation_alias=AliasChoices("VAT_INCLUDED", "vatIncluded"),
        json_schema_extra={"bitrix_type": "bool_none_yn"},
        description="НДС включён в цену",
    )
    measure: int | None = Field(
        None,
        validation_alias=AliasChoices("MEASURE", "measure"),
        json_schema_extra={"bitrix_type": "int_none"},
        description="Единица измерения",
    )
    description: str | None = Field(
        None,
        validation_alias=AliasChoices("DESCRIPTION", "detailText"),
        json_schema_extra={"bitrix_type": "str_none"},
        description="Описание",
    )
    description_type: str | None = Field(
        None,
        validation_alias=AliasChoices("DESCRIPTION_TYPE", "detailTextType"),
        json_schema_extra={"bitrix_type": "str_none"},
        description="Тип описания (TEXT/HTML)",
    )

    # ----- Свойства (Properties) -----
    properties: dict[str, FieldValue] = Field(
        default_factory=dict,
        json_schema_extra={"exclude_from_bitrix": True},
        description=(
            "Дополнительные свойства товаров с указанием типа(TEXT, HTML)"
        ),
    )

    simple_properties: dict[str, FieldValue] = Field(
        default_factory=dict,
        json_schema_extra={"exclude_from_bitrix": True},
        description="Дополнительные простые свойства товаров",
    )

    # ----- Валидаторы -----
    @field_validator("price", mode="before")  # pyright: ignore[misc]
    @classmethod
    def clean_numeric_fields(cls, v: Any) -> float | None:
        """
        Преобразует строки в числа для ценовых полей.
        """
        return BitrixValidators.parse_numeric_string(v)

    @field_validator("external_id", mode="before")
    @classmethod
    def convert_external_id_to_int(cls, value: str | int) -> int:
        """
        Преобразует строковое представление ID в целое число.
        """
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def collect_additional_fields(self) -> BaseProduct:
        """
        Обрабатывает дополнительные поля (__pydantic_extra__) и сохраняет их
        в extra_fields, properties.
        """
        # __pydantic_extra__ автоматически заполняется Pydantic при
        # extra="allow"
        if (
            not hasattr(self, "__pydantic_extra__")
            or not self.__pydantic_extra__
        ):
            return self

        extra_alias_map = self._build_alias_map(self.extra_fields_config)
        property_alias_map = self._build_alias_map(self.properties_config)
        simple_property_alias_map = self._build_alias_map(
            self.simple_properties_config
        )

        extra_processed: dict[str, Any] = {}
        property_processed: dict[str, Any] = {}
        simple_property_processed: dict[str, Any] = {}
        map_processed = (
            (extra_alias_map, extra_processed, 1),
            (property_alias_map, property_processed, 2),
            (simple_property_alias_map, simple_property_processed, 3),
        )
        extra_fields = dict(self.__pydantic_extra__)
        for alias, value in extra_fields.items():
            for alias_map, processed, mode in map_processed:
                if self._check_field(
                    alias, value, alias_map, processed, mode
                ):
                    continue

        # Устанавливаем результат и очищаем __pydantic_extra__
        object.__setattr__(self, "extra_fields", extra_processed)
        object.__setattr__(self, "properties", property_processed)
        object.__setattr__(
            self, "simple_properties", simple_property_processed
        )
        object.__setattr__(self, "__pydantic_extra__", {})
        return self

    def _check_field(
        self,
        alias: str,
        value: Any,
        alias_map: dict[str, dict[str, str]],
        processed: dict[str, Any],
        mode: int,
    ) -> bool:
        field_config = alias_map.get(alias)
        if field_config:
            field_name = field_config["name"]
            field_type = field_config["type"]
            try:
                val = None
                if mode == 1:
                    val = BitrixValidators.apply_field_transformer(
                        field_name, value, field_type
                    )
                elif mode == 2:
                    val = FieldValue(**value)
                    val.value = BitrixValidators.apply_field_transformer(
                        field_name, val.value, field_type
                    )
                elif mode == 3:
                    val = FieldValue(**value)
                if val:
                    processed[field_name] = val
            except Exception as e:  # noqa: BLE001
                logger.error(
                    f"Failed to transform extra field '{field_name}': {e}"
                )
                return False
            else:
                return True
        return False

    # ----- Публичный метод доступа к конфигурации -----
    @classmethod
    def get_properties_configs(
        cls,
    ) -> tuple[dict[str, FieldConfig], dict[str, FieldConfig]]:
        """
        Возвращает конфигурации свойств товаров (основные и простые),
        загружая её при первом вызове.
        """
        if not cls._properties_loaded:
            with cls._properties_lock:
                if not cls._properties_loaded:
                    cls._load_properties_configs()
        return cls._properties_cache or {}, cls._simple_properties_cache or {}

    @property
    def properties_config(self) -> dict[str, FieldConfig]:
        """Возвращает конфигурацию составных свойств товара."""
        return self.get_properties_configs()[0]

    @property
    def simple_properties_config(self) -> dict[str, FieldConfig]:
        """Возвращает конфигурацию простых свойств товара."""
        return self.get_properties_configs()[1]

    # ----- Преобразование в словарь для Bitrix -----
    def to_bitrix_dict(
        self,
        alias_choice: int = 1,
        exclude_none: bool = True,
        exclude_unset: bool = True,
    ) -> dict[str, Any]:
        result = super().to_bitrix_dict(
            alias_choice=alias_choice,
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
        )
        choice_index = 1 if alias_choice >= 2 else 0
        simple_properties = getattr(self, "simple_properties", None)
        if simple_properties:
            for field_name, value in simple_properties.items():
                field_config = self.simple_properties_config.get(field_name)
                if field_config:
                    aliases = field_config.get("alias")
                    bitrix_type = field_config.get("type")
                    if isinstance(aliases, list) and bitrix_type:
                        alias = aliases[choice_index]
                        result[alias] = self._transform_field_value(
                            bitrix_type, value, alias_choice
                        )
        properties = getattr(self, "properties", None)
        if properties:
            for field_name, value in properties.items():
                field_config = self.properties_config.get(field_name)
                if field_config:
                    aliases = field_config.get("alias")
                    bitrix_type = field_config.get("type")
                    if isinstance(aliases, list) and bitrix_type:
                        alias = aliases[choice_index]
                        result[alias] = self._transform_field_value(
                            bitrix_type, value, alias_choice
                        )
        return result

    # ----- Приватные методы загрузки -----
    @classmethod
    def _load_properties_configs(cls) -> None:
        """
        Загружает конфигурации свойств из JSON-файлов.
        """
        if cls._properties_loaded:
            return

        cls._properties_cache = cls._load_config_file(cls.PROPERTIES_FILENAME)
        cls._simple_properties_cache = cls._load_config_file(
            cls.SIMPLE_PROPERTIES_FILENAME
        )
        cls._properties_loaded = True

    @classmethod
    def _load_config_file(
        cls, filename: str | None
    ) -> dict[str, FieldConfig]:
        """
        Загружает конфигурацию из указанного JSON-файла.
        В случае ошибки возвращает пустой словарь.
        """
        if not filename:
            logger.debug(f"Filename {filename} is empty, skipping load.")
            return {}

        return cls._load_data_from_file(filename)


# ===== Классы для создания/обновления товаров (справочник) =====
class ProductCreate(BaseProduct, DataMappingMixin):
    """Модель для создания товаров"""

    name: str = Field(
        ...,
        validation_alias=AliasChoices("NAME", "name"),
        json_schema_extra={"bitrix_type": "str"},
        description="Название товара",
    )

    @classmethod
    def get_default_entity(cls, external_id: int | str) -> ProductCreate:
        """
        Создаёт экземпляр ProductCreate с предустановленными значениями
        для товара-заглушки.
        """
        if isinstance(external_id, str) and external_id.isdigit():
            external_id = int(external_id)
        elif isinstance(external_id, str):
            raise SchemaValidationError(
                message=(
                    "external_id must be int or numeric string, got "
                    f"{external_id!r}"
                )
            )

        product_data: dict[str, Any] = {
            "name": f"Product #{external_id}",
            "external_id": external_id,
        }
        return cls(**product_data)


class ProductUpdate(BaseProduct, DataMappingMixin):
    """Схема для частичного обновления товаров"""

    name: str | None = Field(
        None,
        validation_alias=AliasChoices("NAME", "name"),
        json_schema_extra={"bitrix_type": "str"},
        description="Название товара",
    )


class ListProduct(BaseModel):
    """Схема для списка товаров сущности"""

    result: list[ProductCreate]

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
    )
