from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator

from core import settings
from core.exceptions.schemas import SchemaValidationError

from .base_schemas import (
    AddressMixin,
    BaseCreateSchema,
    BaseUpdateSchema,
    HasCommunicationCreateMixin,
    HasCommunicationUpdateMixin,
)
from .mixins import CommunicationChannel


# ===== Константы =====
SYSTEM_USER_ID = settings.bitrix24.system_user_id


class BaseContact:
    """
    Базовые поля контакта Bitrix24.

    Содержит все стандартные атрибуты контакта: имя, фамилию, контактные
    данные, связи с другими сущностями и т.д.
    """

    # Идентификаторы и основные данные
    name: str | None = Field(
        None,
        alias="NAME",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    second_name: str | None = Field(
        None,
        alias="SECOND_NAME",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    last_name: str | None = Field(
        None,
        alias="LAST_NAME",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    post: str | None = Field(
        None,
        alias="POST",
        json_schema_extra={"bitrix_type": "str_none"},
    )

    # Статусы и флаги
    export: bool | None = Field(
        None,
        alias="EXPORT",
        json_schema_extra={"bitrix_type": "bool_yn"},
    )
    origin_version: str | None = Field(
        None,
        alias="ORIGIN_VERSION",
        json_schema_extra={"bitrix_type": "str_none"},
    )

    # Временные метки
    birthdate: datetime | None = Field(
        None,
        alias="BIRTHDATE",
        json_schema_extra={"bitrix_type": "datetime_none"},
    )

    # Связи с другими сущностями
    type_id: str | None = Field(
        None,
        alias="TYPE_ID",
        json_schema_extra={"bitrix_type": "str_none"},
    )
    company_id: int | None = Field(
        None,
        alias="COMPANY_ID",
        json_schema_extra={"bitrix_type": "int_none"},
    )
    lead_id: int | None = Field(
        None,
        alias="LEAD_ID",
        json_schema_extra={"bitrix_type": "int_none"},
    )
    source_id: str | None = Field(
        None,
        alias="SOURCE_ID",
        json_schema_extra={"bitrix_type": "str_none"},
    )

    # Коммуникации
    phone: list[CommunicationChannel] | None = Field(None, alias="PHONE")
    email: list[CommunicationChannel] | None = Field(None, alias="EMAIL")
    web: list[CommunicationChannel] | None = Field(None, alias="WEB")
    im: list[CommunicationChannel] | None = Field(None, alias="IM")
    link: list[CommunicationChannel] | None = Field(None, alias="LINK")

    @field_validator("external_id", mode="before")  # pyright: ignore[misc]
    @classmethod
    def convert_external_id_to_int(cls, value: str | int) -> int:
        """
        Преобразует строковое представление ID в целое число.

        Это необходимо, так как Bitrix24 может возвращать ID как строку,
        а в базе данных и бизнес-логике удобнее работать с числами.
        """
        if isinstance(value, str) and value.isdigit():
            return int(value)
        # Если значение не строка или не цифры, оставляем как есть,
        # Pydantic сам выполнит валидацию в соответствии с типом поля.
        return value  # type: ignore[return-value]


class ContactCreate(
    BaseCreateSchema, BaseContact, AddressMixin, HasCommunicationCreateMixin
):
    """
    Схема для создания нового контакта в Bitrix24.

    Объединяет базовые поля контакта, миксины адреса, коммуникаций,
    а также добавляет служебные поля (даты создания, создателя и т.д.).
    """

    EXTRA_FIELDS: ClassVar[dict[str, dict[str, str]]] = {
        "honorific": {
            "alias": "HONORIFIC",
            "type": "str_none",
            "comment": "Обращение",
        },
        "photo": {
            "alias": "PHOTO",
            "type": "dict_none",
            "comment": "Фотография",
        },
        "id_article_knowledge_base": {
            "alias": "UF_CRM_CONTACT_ITS_ARTICLE_ID",
            "type": "str_none",
            "comment": "ID статьи в Базе Знаний",
        },
        "business": {
            "alias": "UF_CRM_1779861791",
            "type": "str_none",
            "comment": "Список дел",
        },
    }

    @classmethod
    def get_default_entity(cls, external_id: int | str) -> "ContactCreate":
        """
        Создаёт экземпляр ContactCreate с предустановленными значениями по
        умолчанию.

        Используется для создания контакта-заглушки.
        """

        # Конвертируем str в int, если нужно
        if isinstance(external_id, str) and external_id.isdigit():
            external_id = int(external_id)
        elif isinstance(external_id, str):
            raise SchemaValidationError(
                message=(
                    "external_id must be int or numeric string, got "
                    f"{external_id!r}"
                )
            )

        now = datetime.now(UTC)
        contact_data: dict[str, Any] = {
            # Обязательные поля из TimestampsCreateMixin
            "date_create": now,
            "date_modify": now,
            # Обязательные поля из UserRelationsCreateMixin
            "assigned_by_id": SYSTEM_USER_ID,
            "created_by_id": SYSTEM_USER_ID,
            "modify_by_id": SYSTEM_USER_ID,
            # Обязательные поля из HasCommunicationCreateMixin
            "has_phone": False,
            "has_email": False,
            "has_imol": False,
            # Обязательные поля из ContactCreate
            "name": f"Contact #{external_id}",
            # Задаем external_id и флаг удаления
            "external_id": external_id,  # Внешний ID
            "is_deleted": True,
        }
        return cls(**contact_data)


class ContactUpdate(
    BaseUpdateSchema, BaseContact, AddressMixin, HasCommunicationUpdateMixin
):
    """
    Схема для обновления существующего контакта.

    Наследует те же поля, что и ContactCreate, но с поддержкой частичного
    обновления (через BaseUpdateSchema).
    """
