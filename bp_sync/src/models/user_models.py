"""
Модуль моделей пользователей, менеджеров и аутентификации.

Содержит SQLAlchemy-модели:
- User: основная модель пользователя (наследуется от IntIdEntity)
- Manager: модель менеджера (связь 1:1 с User)
- UserAuth: модель для хранения хешированных паролей и ролей
  (связь 1:1 с User)
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy import UUID as uuid_sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.postgres import Base
from schemas.enums import EntityType
from schemas.user_schemas import ManagerCreate, UserCreate

from .bases import IntIdEntity


if TYPE_CHECKING:
    #     from .company_models import Company
    #     from .contact_models import Contact
    #     from .deal_models import Deal
    from .department_models import Department
#     from .lead_models import Lead
#     from .product_models import Product
#     from .timeline_comment_models import TimelineComment


# ===== Модель пользователя =====
class User(IntIdEntity):
    """
    Модель пользователя Bitrix24 / внутренняя.

    Содержит персональные данные, временные метки, связи с другими
    сущностями (сделки, контакты, компании, лиды, товары, комментарии).
    """

    __tablename__ = "users"
    _schema_class = UserCreate

    # ----- Свойства и методы -----
    @property
    def entity_type(self) -> EntityType:
        """Тип сущности для системы (пользователь)."""
        return EntityType.USER

    @property
    def full_name(self) -> str:
        """Полное имя пользователя (Имя + Фамилия)."""
        first = self.name or ""
        last = self.last_name or ""
        return f"{first} {last}".strip()

    def __str__(self) -> str:
        return self.full_name or f"User(external_id={self.external_id})"

    @property
    def has_auth(self) -> bool:
        """Проверяет, присутствует ли связанная запись аутентификации."""
        return self.auth is not None

    # ----- Поля таблицы -----
    xml_id: Mapped[str | None] = mapped_column(
        comment="Внешний код"
    )  # XML_ID : Внешний код
    name: Mapped[str | None] = mapped_column(comment="Имя")  # NAME : Имя
    second_name: Mapped[str | None] = mapped_column(
        comment="Отчество"
    )  # SECOND_NAME : Отчество
    last_name: Mapped[str | None] = mapped_column(
        comment="Фамилия"
    )  # LAST_NAME : Фамилия
    personal_gender: Mapped[str | None] = mapped_column(
        comment="Пол"
    )  # PERSONAL_GENDER : Пол M / F
    work_position: Mapped[str | None] = mapped_column(
        comment="Должность"
    )  # WORK_POSITION : Должность
    user_type: Mapped[str | None] = mapped_column(
        comment="Тип пользователя"
    )  # USER_TYPE : Тип пользователя

    # Статусы и флаги
    active: Mapped[bool] = mapped_column(
        default=False, comment="Активность"
    )  # ACTIVE : Активность True / False
    is_online: Mapped[bool] = mapped_column(
        default=False, comment="Онлайн"
    )  # IS_ONLINE : Онлайн (Y/N)

    # Временные метки
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Последняя авторизация"
    )  # LAST_LOGIN : Последняя авторизация (2025-06-18T03:00:00+03:00)
    date_register: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Дата регистрации"
    )  # DATE_REGISTER : Дата регистрации
    personal_birthday: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Дата рождения"
    )  # PERSONAL_BIRTHDAY : Дата рождения
    employment_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Дата принятия на работу"
    )  # UF_EMPLOYMENT_DATE : Дата принятия на работу
    date_new: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Новая дата"
    )  # UF_USR_1699347879988 : Новая дата

    # География и источники
    time_zone: Mapped[str | None] = mapped_column(
        comment="Часовой пояс"
    )  # TIME_ZONE : Часовой пояс
    personal_city: Mapped[str | None] = mapped_column(
        comment="Город проживания"
    )  # PERSONAL_CITY : Город проживания

    # Коммуникации
    email: Mapped[str | None] = mapped_column(
        comment="E-Mail"
    )  # EMAIL : E-Mail
    personal_mobile: Mapped[str | None] = mapped_column(
        comment="Личный мобильный"
    )  # PERSONAL_MOBILE : Личный мобильный
    work_phone: Mapped[str | None] = mapped_column(
        comment="Телефон компании"
    )  # WORK_PHONE : Телефон компании
    personal_www: Mapped[str | None] = mapped_column(
        comment="Домашняя страничка"
    )  # PERSONAL_WWW : Домашняя страничка

    # Связи с другими сущностями
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.external_id")
    )  # UF_DEPARTMENT : отдел

    # ----- Связи (relationships) -----
    department: Mapped["Department"] = relationship(
        "Department", back_populates="users"
    )
    # assigned_deals: Mapped[list["Deal"]] = relationship(
    #     "Deal",
    #     back_populates="assigned_user",
    #     foreign_keys="[Deal.assigned_by_id]",
    # )
    # created_deals: Mapped[list["Deal"]] = relationship(
    #     "Deal",
    #     back_populates="created_user",
    #     foreign_keys="[Deal.created_by_id]",
    # )
    # modify_deals: Mapped[list["Deal"]] = relationship(
    #     "Deal",
    #     back_populates="modify_user",
    #     foreign_keys="[Deal.modify_by_id]",
    # )
    # moved_deals: Mapped[list["Deal"]] = relationship(
    #     "Deal",
    #     back_populates="moved_user",
    #     foreign_keys="[Deal.moved_by_id]",
    # )
    # last_activity_deals: Mapped[list["Deal"]] = relationship(
    #     "Deal",
    #     back_populates="last_activity_user",
    #     foreign_keys="[Deal.last_activity_by]",
    # )

    # assigned_leads: Mapped[list["Lead"]] = relationship(
    #     "Lead",
    #     back_populates="assigned_user",
    #     foreign_keys="[Lead.assigned_by_id]",
    # )
    # created_leads: Mapped[list["Lead"]] = relationship(
    #     "Lead",
    #     back_populates="created_user",
    #     foreign_keys="[Lead.created_by_id]",
    # )
    # modify_leads: Mapped[list["Lead"]] = relationship(
    #     "Lead",
    #     back_populates="modify_user",
    #     foreign_keys="[Lead.modify_by_id]",
    # )
    # moved_leads: Mapped[list["Lead"]] = relationship(
    #     "Lead",
    #     back_populates="moved_user",
    #     foreign_keys="[Lead.moved_by_id]",
    # )
    # last_activity_leads: Mapped[list["Lead"]] = relationship(
    #     "Lead",
    #     back_populates="last_activity_user",
    #     foreign_keys="[Lead.last_activity_by]",
    # )

    # assigned_contacts: Mapped[list["Contact"]] = relationship(
    #     "Contact",
    #     back_populates="assigned_user",
    #     foreign_keys="[Contact.assigned_by_id]",
    # )
    # created_contacts: Mapped[list["Contact"]] = relationship(
    #     "Contact",
    #     back_populates="created_user",
    #     foreign_keys="[Contact.created_by_id]",
    # )
    # modify_contacts: Mapped[list["Contact"]] = relationship(
    #     "Contact",
    #     back_populates="modify_user",
    #     foreign_keys="[Contact.modify_by_id]",
    # )
    # last_activity_contacts: Mapped[list["Contact"]] = relationship(
    #     "Contact",
    #     back_populates="last_activity_user",
    #     foreign_keys="[Contact.last_activity_by]",
    # )

    # assigned_companies: Mapped[list["Company"]] = relationship(
    #     "Company",
    #     back_populates="assigned_user",
    #     foreign_keys="[Company.assigned_by_id]",
    # )
    # created_companies: Mapped[list["Company"]] = relationship(
    #     "Company",
    #     back_populates="created_user",
    #     foreign_keys="[Company.created_by_id]",
    # )
    # modify_companies: Mapped[list["Company"]] = relationship(
    #     "Company",
    #     back_populates="modify_user",
    #     foreign_keys="[Company.modify_by_id]",
    # )
    # last_activity_companies: Mapped[list["Company"]] = relationship(
    #     "Company",
    #     back_populates="last_activity_user",
    #     foreign_keys="[Company.last_activity_by]",
    # )
    # timeline_comments: Mapped[list["TimelineComment"]] = relationship(
    #     "TimelineComment",
    #     back_populates="author",
    #     foreign_keys="[TimelineComment.author_id]",
    # )

    # modified_products: Mapped[list["Product"]] = relationship(
    #     "Product",
    #     back_populates="modified_user",
    #     foreign_keys="[Product.modified_by]",
    # )

    # created_products: Mapped[list["Product"]] = relationship(
    #     "Product",
    #     back_populates="created_user",
    #     foreign_keys="[Product.created_by]",
    # )

    manager: Mapped["Manager"] = relationship(
        back_populates="user", uselist=False
    )

    auth: Mapped["UserAuth | None"] = relationship(
        "UserAuth",
        back_populates="user",
        uselist=False,  # Один-к-одному
        cascade="all, delete-orphan",
    )


# ===== Модель менеджера =====
class Manager(Base):
    """
    Расширенная информация о менеджере (связь 1:1 с пользователем).

    Используется для хранения служебных полей (диск, чат, активность).
    """

    __tablename__ = "managers"
    _schema_class = ManagerCreate

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.external_id"),
        unique=True,
        comment="ИД сотрудника",
    )
    user: Mapped["User"] = relationship("User", back_populates="manager")
    is_active: Mapped[bool] = mapped_column(
        default=False, comment="Менеджер активный"
    )
    disk_id: Mapped[int | None] = mapped_column(comment="ИД диска")
    chat_id: Mapped[int | None] = mapped_column(comment="ИД служебного чата")

    def __str__(self) -> str:
        return (
            str(self.user.full_name)
            if self.user
            else f"Manager(user_id={self.user_id})"
        )


# ===== Модель аутентификации пользователя =====
class UserAuth(Base):
    """
    Модель для хранения учётных данных (хеш пароля, роль, верификация).

    Связана с пользователем отношением один-к-одному.
    """

    __tablename__ = "user_auths"

    user_id: Mapped[UUID] = mapped_column(
        uuid_sql(as_uuid=True),
        ForeignKey("users.internal_id"),
        unique=True,
        nullable=False,
        comment="ID пользователя (UUID)",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Хеш пароля (bcrypt/argon2)",
    )

    role: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Роль: admin, manager, user, guest",
    )

    is_verified: Mapped[bool] = mapped_column(
        default=False,
        comment="Email подтверждён",
    )

    last_login_attempt: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Время последней неудачной попытки входа",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="auth",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<UserAuth for user_id={self.user_id}>"
