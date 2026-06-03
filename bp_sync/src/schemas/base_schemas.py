from datetime import datetime
from typing import Any, Self, TypeVar
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.exceptions.schemas import (
    NegativeValueError,
    PaginationError,
)
from core.logger import logger

from .data_mapping import DataMappingMixin


# ===== Типы =====
T = TypeVar("T", bound="CommonFieldMixin")


class CommonFieldMixin(DataMappingMixin):
    """
    Базовый миксин для всех моделей с общими полями.
    """

    internal_id: UUID | None = Field(
        default=None,
        # exclude=True,
        init_var=False,
        description="Внутренний UUID идентификатор",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
        json_schema_extra={
            "exclude_from_bitrix": True,
            "exclude_from_comparison": True,
        },
    )
    created_at: datetime | None = Field(
        default=None,
        description="Дата и время создания записи",
        json_schema_extra={
            "exclude_from_bitrix": True,
            "exclude_from_comparison": True,
        },
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего обновления",
        json_schema_extra={
            "exclude_from_bitrix": True,
            "exclude_from_comparison": True,
        },
    )
    is_deleted: bool | None = Field(
        default=None,
        description="Флаг удаления",
        json_schema_extra={
            "exclude_from_bitrix": True,
            "exclude_from_comparison": True,
        },
    )
    external_id: int | str | None = Field(
        default=None,
        validation_alias=AliasChoices("ID", "id"),
        description="Внешний идентификатор (ID из Битрикс)",
        json_schema_extra={
            "exclude_from_bitrix": True,
            "exclude_from_alternate_comparison": True,
        },
    )
    extra_fields: dict[str, Any] = Field(
        default_factory=dict,
        # exclude=True,
        description="Дополнительные поля, не определённые в схеме",
    )

    # ----- Конфигурация -----
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        extra="allow",
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: str,
        },
    )

    @classmethod
    def get_default_entity(cls, external_id: int | str) -> Self:
        return cls(external_id=external_id)


class ListResponseSchema[T: CommonFieldMixin](BaseModel):
    """
    Схема для ответа со списком сущностей.

    Attributes:
        result: Список сущностей
        total: Общее количество сущностей
        next: Идентификатор для пагинации (следующая страница)
    """

    result: list[T] = Field(
        default_factory=list[T], description="Список сущностей"
    )
    total: int = Field(
        default=0, ge=0, description="Общее количество сущностей"
    )
    next: int | None = Field(
        default=None,
        ge=0,
        description="Идентификатор для пагинации (следующая страница)",
    )

    # ----- Конфигурация -----
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: str,
        },
    )

    # ----- Валидаторы -----
    @model_validator(mode="after")
    def _validate_result_not_none(self) -> "ListResponseSchema[T]":
        """
        Валидатор: убеждается, что result не None (Pydantic в любом случае
        не допустит, но явная проверка не помешает).
        Логирует предупреждение, если result None.
        """
        if self.result is None:  # pyright: ignore[reportUnnecessaryComparison]
            logger.warning("Result field is None, replacing with empty list")
            self.result = []
        return self

    @field_validator("total", mode="after")
    @classmethod
    def _validate_total_non_negative(cls, value: int) -> int:
        """Проверяет, что total не отрицательный."""
        if value < 0:
            raise NegativeValueError(
                message=f"Total cannot be negative: {value}"
            )
        return value

    @field_validator("next", mode="after")
    @classmethod
    def _validate_next_non_negative(cls, value: int | None) -> int | None:
        """Проверяет, что next (если не None) не отрицательный."""
        if value is not None and value < 0:
            raise NegativeValueError(
                message=f"Next cursor cannot be negative: {value}"
            )
        return value

    # ----- Публичные методы -----
    @classmethod
    def from_cursor_paginated(
        cls,
        items: list[T],
        total: int | None = None,
        next_cursor: int | None = None,
        *,
        fallback_total: int = 0,
    ) -> "ListResponseSchema[T]":
        """
        Создаёт экземпляр из данных пагинации по курсору.

        Args:
            items: Список элементов текущей страницы
            total: Общее количество элементов
                   (может быть None, если неизвестно)
            next_cursor: Идентификатор следующей страницы
                         (None, если страница последняя)
            fallback_total: Значение total по умолчанию, если передан None

        Returns:
            Заполненная схема ListResponseSchema

        Raises:
            PaginationError: Если total отрицательный или items не является
            списком

        Example:
            >>> response = ListResponseSchema.from_cursor_paginated(
            ...     items=[{"id": 1}, {"id": 2}], total=100, next_cursor=2
            ... )
        """
        if not isinstance(items, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise PaginationError(
                message=(
                    f"Expected items to be a list, got {type(items).__name__}"
                )
            )
        if total is not None and total < 0:
            raise PaginationError(
                message=f"Total cannot be negative: {total}"
            )

        effective_total = total if total is not None else fallback_total
        logger.debug(
            f"Creating ListResponseSchema with {len(items)} items, "
            f"total={effective_total}, next={next_cursor}"
        )
        return cls(
            result=items,
            total=effective_total,
            next=next_cursor,
        )

    def __len__(self) -> int:
        """Возвращает количество элементов в текущей странице."""
        return len(self.result)

    def is_last_page(self) -> bool:
        """
        Проверяет, является ли текущая страница последней.

        Returns:
            True, если следующей страницы нет (next is None), иначе False.
        """
        return self.next is None

    def __str__(self) -> str:
        """Краткое строковое представление схемы ответа."""
        return (
            f"{self.__class__.__name__}(items={len(self.result)}, "
            f"total={self.total}, next={self.next})"
        )


# ===== Миксины для полей =====


class BaseFieldMixin:
    """Базовые поля для большинства сущностей."""

    comments: str | None = Field(
        None, alias="COMMENTS", json_schema_extra={"bitrix_type": "str_none"}
    )
    source_description: str | None = Field(
        None,
        alias="SOURCE_DESCRIPTION",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    originator_id: str | None = Field(
        None,
        alias="ORIGINATOR_ID",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    origin_id: str | None = Field(
        None, alias="ORIGIN_ID", json_schema_extra={"bitrix_type": "str_none"}
    )


class TimestampsCreateMixin:
    """Миксин для временных меток при создании."""

    date_create: datetime = Field(
        ...,
        validation_alias=AliasChoices("DATE_CREATE", "createdTime"),
        json_schema_extra={"bitrix_type": "datetime"},
    )
    date_modify: datetime = Field(
        ...,
        validation_alias=AliasChoices("DATE_MODIFY", "updatedTime"),
        json_schema_extra={"bitrix_type": "datetime"},
    )
    last_activity_time: datetime | None = Field(
        None,
        validation_alias=AliasChoices(
            "LAST_ACTIVITY_TIME", "lastActivityTime"
        ),
        json_schema_extra={"bitrix_type": "datetime_none"},
    )
    last_communication_time: datetime | None = Field(
        None,
        validation_alias=AliasChoices(
            "LAST_COMMUNICATION_TIME", "lastCommunicationTime"
        ),
        json_schema_extra={"bitrix_type": "datetime_alt_none"},
    )


class TimestampsUpdateMixin:
    """Миксин для временных меток при обновлении (все поля опциональны)."""

    date_create: datetime | None = Field(
        None,
        validation_alias=AliasChoices("DATE_CREATE", "createdTime"),
        json_schema_extra={"bitrix_type": "datetime"},
    )
    date_modify: datetime | None = Field(
        None,
        validation_alias=AliasChoices("DATE_MODIFY", "updatedTime"),
        json_schema_extra={"bitrix_type": "datetime"},
    )
    last_activity_time: datetime | None = Field(
        None,
        validation_alias=AliasChoices(
            "LAST_ACTIVITY_TIME", "lastActivityTime"
        ),
        json_schema_extra={"bitrix_type": "datetime_none"},
    )
    last_communication_time: datetime | None = Field(
        None,
        validation_alias=AliasChoices(
            "LAST_COMMUNICATION_TIME", "lastCommunicationTime"
        ),
        json_schema_extra={"bitrix_type": "datetime_alt_none"},
    )


class UserRelationsCreateMixin:
    """Миксин для полей, связанных с пользователями, при создании."""

    assigned_by_id: int = Field(
        ...,
        validation_alias=AliasChoices("ASSIGNED_BY_ID", "assignedById"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    created_by_id: int = Field(
        ...,
        validation_alias=AliasChoices("CREATED_BY_ID", "createdBy"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    modify_by_id: int = Field(
        ...,
        validation_alias=AliasChoices("MODIFY_BY_ID", "updatedBy"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    last_activity_by: int | None = Field(
        None,
        validation_alias=AliasChoices("LAST_ACTIVITY_BY", "lastActivityBy"),
        json_schema_extra={"bitrix_type": "int_none"},
    )


class UserRelationsUpdateMixin:
    """
    Миксин для полей, связанных с пользователями, при обновлении
    (все опциональны).
    """

    assigned_by_id: int | None = Field(
        None,
        validation_alias=AliasChoices("ASSIGNED_BY_ID", "assignedById"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    created_by_id: int | None = Field(
        None,
        validation_alias=AliasChoices("CREATED_BY_ID", "createdBy"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    modify_by_id: int | None = Field(
        None,
        validation_alias=AliasChoices("MODIFY_BY_ID", "updatedBy"),
        json_schema_extra={"bitrix_type": "int_user"},
    )
    last_activity_by: int | None = Field(
        None,
        validation_alias=AliasChoices("LAST_ACTIVITY_BY", "lastActivityBy"),
        json_schema_extra={"bitrix_type": "int_none"},
    )


class MarketingMixinUTM:
    """Миксин для маркетинговых полей"""

    utm_source: str | None = Field(
        None,
        alias="UTM_SOURCE",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    utm_medium: str | None = Field(
        None,
        alias="UTM_MEDIUM",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    utm_campaign: str | None = Field(
        None,
        alias="UTM_CAMPAIGN",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    utm_content: str | None = Field(
        None,
        alias="UTM_CONTENT",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    utm_term: str | None = Field(
        None,
        alias="UTM_TERM",
        json_schema_extra={"bitrix_type": "str_none"},
    )


class AddressMixin:
    """Миксин для адресных полей"""

    address: str | None = Field(
        None,
        alias="ADDRESS",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_2: str | None = Field(
        None,
        alias="ADDRESS_2",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_city: str | None = Field(
        None,
        alias="ADDRESS_CITY",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_postal_code: str | None = Field(
        None,
        alias="ADDRESS_POSTAL_CODE",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_region: str | None = Field(
        None,
        alias="ADDRESS_REGION",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_province: str | None = Field(
        None,
        alias="ADDRESS_PROVINCE",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_country: str | None = Field(
        None,
        alias="ADDRESS_COUNTRY",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_country_code: str | None = Field(
        None,
        alias="ADDRESS_COUNTRY_CODE",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    address_loc_addr_id: int | None = Field(
        None,
        alias="ADDRESS_LOC_ADDR_ID",
        json_schema_extra={"bitrix_type": "int_none"},
    )


class CallTrackingMixin:
    """Миксин для полей коллтрекинга (MGO, Calltouch)."""

    mgo_cc_entry_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    mgo_cc_channel_type: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    mgo_cc_result: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    mgo_cc_entry_point: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    mgo_cc_create: datetime | None = Field(
        None,
        json_schema_extra={"bitrix_type": "datetime_none"},
    )
    mgo_cc_end: datetime | None = Field(
        None,
        json_schema_extra={"bitrix_type": "datetime_none"},
    )
    mgo_cc_tag_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    calltouch_site_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    calltouch_call_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    calltouch_request_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )


class SocialProfilesMixin:
    """Миксин для полей социальных профилей."""

    wz_instagram: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    wz_vc: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    wz_telegram_username: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    wz_telegram_id: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )
    wz_avito: str | None = Field(
        None,
        json_schema_extra={"bitrix_type": "str_none"},
    )


class HasCommunicationCreateMixin:
    """Присутствуют ли коммуникации при создании."""

    has_phone: bool = Field(
        ...,
        alias="HAS_PHONE",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
    has_email: bool = Field(
        ...,
        alias="HAS_EMAIL",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
    has_imol: bool = Field(
        ...,
        alias="HAS_IMOL",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )


class HasCommunicationUpdateMixin:
    """Присутствуют ли коммуникации при обновлении (опционально)."""

    has_phone: bool | None = Field(
        None,
        alias="HAS_PHONE",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
    has_email: bool | None = Field(
        None,
        alias="HAS_EMAIL",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
    has_imol: bool | None = Field(
        None,
        alias="HAS_IMOL",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )


# ===== Базовые схемы для создания/обновления =====


class CoreCreateSchema(
    CommonFieldMixin,
    TimestampsCreateMixin,
    UserRelationsCreateMixin,
):
    """Ядро схемы для создания сущностей."""


class BaseCreateSchema(
    CoreCreateSchema,
    BaseFieldMixin,
    MarketingMixinUTM,
):
    """Базовая схема для создания сущностей."""

    opened: bool = Field(
        default=True,
        alias="OPENED",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )


class CoreUpdateSchema(
    CommonFieldMixin,
    TimestampsUpdateMixin,
    UserRelationsUpdateMixin,
):
    """Ядро схемы для обновления сущностей"""


class BaseUpdateSchema(
    CoreUpdateSchema,
    BaseFieldMixin,
    MarketingMixinUTM,
):
    """Базовая схема для обновления сущностей"""

    opened: bool | None = Field(
        default=None,
        alias="OPENED",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
