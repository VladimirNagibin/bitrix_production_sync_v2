"""
Модели для работы с коммуникационными каналами сущностей.
"""

from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    ForeignKey,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.exceptions.database import (
    CommunicationChannelTypeError,
    CommunicationChannelValueError,
)
from core.logger import logger
from db.postgres import Base
from schemas.enums import CommunicationType, EntityType

from .bases import IntIdEntity


# ===== Константы / Constants =====
MAX_TYPE_ID_LEN = 20  # PHONE, EMAIL, WEB, IM, LINK
MAX_VALUE_TYPE_LEN = 50  # WORK, HOME, MAIN, MOBILE и т.д.
MAX_DESCRIPTION_LEN = 255
MAX_CHANNEL_VALUE_LEN = 255
MAX_ENTITY_TYPE_LEN = 20  # lead, contact, company


# ===== Модель: Тип коммуникационного канала/Communication Channel Type =====
class CommunicationChannelType(Base):
    """
    Справочник типов коммуникационных каналов.

    Описывает, что именно хранится (телефон, email) и как уточняется
    (рабочий, домашний).
    """

    __tablename__ = "communication_channel_types"
    __table_args__ = (
        UniqueConstraint(
            "type_id", "value_type", name="uq_channel_type_value_type"
        ),
    )

    type_id: Mapped[CommunicationType] = mapped_column(
        String(MAX_TYPE_ID_LEN),
        comment="Тип коммуникации (PHONE, EMAIL, WEB, IM, LINK)",
    )  # TYPE_ID
    value_type: Mapped[str] = mapped_column(
        String(MAX_VALUE_TYPE_LEN),
        comment=(
            "Уточнение типа коммуникации по каналу "
            "(WORK, HOME, MAIN, MOBILE и т.д.)"
        ),
    )  # VALUE_TYPE
    description: Mapped[str | None] = mapped_column(
        String(MAX_DESCRIPTION_LEN),
        default=None,
        nullable=True,
        comment="Описание типа канала",
    )

    # Связь с конкретными каналами
    channels: Mapped[list["CommunicationChannel"]] = relationship(
        "CommunicationChannel",
        back_populates="channel_type",
        cascade="all, delete-orphan",
        lazy="selectin",  # Оптимизированная загрузка для коллекций
    )

    def __init__(self, **kwargs: object) -> None:
        """
        Инициализация объекта типа канала с валидацией данных.
        """
        data = dict(kwargs)
        self._validate_payload(data)
        super().__init__(**kwargs)

    @staticmethod
    def _validate_payload(data: dict[str, object]) -> None:
        """
        Валидирует входящие данные перед созданием объекта.

        Raises:
            CommunicationChannelTypeError: Если данные некорректны.
        """
        errors: list[str] = []

        # Проверка type_id
        type_id = data.get("type_id")
        if not type_id:
            errors.append("Field 'type_id' is required")
        elif isinstance(type_id, str) and len(type_id) > MAX_TYPE_ID_LEN:
            errors.append(
                f"Field 'type_id' exceeds maximum length of {MAX_TYPE_ID_LEN}"
            )

        # Проверка value_type
        value_type = data.get("value_type")
        if not value_type:
            errors.append("Field 'value_type' is required")
        elif (
            isinstance(value_type, str)
            and len(value_type) > MAX_VALUE_TYPE_LEN
        ):
            errors.append(
                "Field 'value_type' exceeds maximum length of "
                f"{MAX_VALUE_TYPE_LEN}"
            )

        if errors:
            error_msg = "Validation failed: " + "; ".join(errors)
            logger.warning(
                "CommunicationChannelType validation error: %s", error_msg
            )
            raise CommunicationChannelTypeError(message=error_msg)

    def __str__(self) -> str:
        return f"{self.type_id} - {self.value_type}"

    def __repr__(self) -> str:
        return (
            f"<CommunicationChannelType(id={self.internal_id}, "
            f"type_id='{self.type_id}', value_type='{self.value_type}', "
            f"description='{self.description}')>"
        )


# ===== Модель: Коммуникационный канал / Communication Channel =====
class CommunicationChannel(IntIdEntity):
    """
    Конкретный канал связи сущности (Lead/Contact/Company).

    Связывает сущность с типом канала и хранит значение (номер, email).
    """

    __tablename__ = "communication_channels"

    entity_type: Mapped[EntityType] = mapped_column(
        String(MAX_ENTITY_TYPE_LEN),
        index=True,
        comment="Тип сущности (lead, contact, company)",
    )
    entity_id: Mapped[int] = mapped_column(
        comment="Внешний ID соответствующей сущности"
    )
    channel_type_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "communication_channel_types.internal_id", ondelete="CASCADE"
        ),
        comment="Ссылка на тип канала",
    )
    channel_type: Mapped["CommunicationChannelType"] = relationship(
        "CommunicationChannelType",
        back_populates="channels",
        lazy="joined",  # Жадная загрузка для производительности
    )
    value: Mapped[str] = mapped_column(
        String(MAX_CHANNEL_VALUE_LEN),
        comment="Значение коннекта (номер телефона, email, URL и т.д.)",
    )  # VALUE

    def __init__(self, **kwargs: object) -> None:
        """
        Инициализация канала связи с валидацией данных.
        """
        data = dict(kwargs)
        self._validate_payload(data)
        super().__init__(**kwargs)

    @staticmethod
    def _validate_payload(data: dict[str, object]) -> None:
        """
        Валидирует обязательные поля канала связи.

        Raises:
            CommunicationChannelValueError: Если данные некорректны.
        """
        errors: list[str] = []

        # Проверка entity_type
        entity_type = data.get("entity_type")
        if not entity_type:
            errors.append("Field 'entity_type' is required")

        # Проверка entity_id
        entity_id = data.get("entity_id")
        if entity_id is None:
            errors.append("Field 'entity_id' is required")

        # Проверка channel_type_id
        channel_type_id = data.get("channel_type_id")
        if not channel_type_id:
            errors.append("Field 'channel_type_id' is required")

        # Проверка value
        value = data.get("value")
        if not value:
            errors.append("Field 'value' is required")
        elif isinstance(value, str) and len(value) > MAX_CHANNEL_VALUE_LEN:
            errors.append(
                "Field 'value' exceeds maximum length of "
                f"{MAX_CHANNEL_VALUE_LEN}"
            )

        if errors:
            error_msg = "Validation failed: " + "; ".join(errors)
            logger.warning(
                "CommunicationChannel validation error: %s", error_msg
            )
            raise CommunicationChannelValueError(message=error_msg)

    @hybrid_property
    def type_id(self) -> str | None:  # pyright: ignore[reportRedeclaration]
        """
        Возвращает тип канала (например, 'PHONE') через связь.

        Property позволяет обращаться как к полю объекта без явного
        указания связанного объекта.
        """
        return self.channel_type.type_id if self.channel_type else None

    @type_id.expression  # type: ignore[no-redef]  # pyright: ignore[reportRedeclaration]
    def type_id(cls) -> ColumnElement[str]:
        """
        SQL-выражение для получения type_id.

        Позволяет фильтровать по type_id без явного JOIN в запросах,
        используя подзапрос (scalar_subquery).
        """
        return (
            select(CommunicationChannelType.type_id)
            .where(
                CommunicationChannelType.internal_id == cls.channel_type_id
            )
            .scalar_subquery()
        )

    @hybrid_property
    def value_type(self) -> str | None:  # pyright: ignore[reportRedeclaration]
        """
        Возвращает уточнение типа (например, 'WORK') через связь.
        """
        return self.channel_type.value_type if self.channel_type else None

    @value_type.expression  # type: ignore[no-redef]  # pyright: ignore[reportRedeclaration]
    def value_type(cls) -> ColumnElement[str]:
        """
        Возвращает уточнение типа (например, 'WORK') через связь.
        """
        return (
            select(CommunicationChannelType.value_type)
            .where(
                CommunicationChannelType.internal_id == cls.channel_type_id
            )
            .scalar_subquery()
        )

    def __str__(self) -> str:
        """Человеко-читаемое представление канала."""
        name_parts: list[str] = []
        if self.type_id:
            name_parts.append(str(self.type_id))
        if self.value_type:
            name_parts.append(str(self.value_type))

        name = " ".join(name_parts)
        return f"{name}: {self.value}" if name else str(self.value)

    def __repr__(self) -> str:
        return (
            f"<CommunicationChannel(id={self.internal_id}, "
            f"entity_type='{self.entity_type}', entity_id={self.entity_id}, "
            f"channel_type_id={self.channel_type_id}, value='{self.value}')>"
        )
