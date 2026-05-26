from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .bases import NameIntIdEntity
from .user_models import User


# ===== Модель: Отдел / Department =====
class Department(NameIntIdEntity):
    """
    Отделы:
    (предзаполнить)
    """

    __tablename__ = "departments"

    def __str__(self) -> str:
        return str(self.name)

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.external_id"), nullable=True
    )
    child_departments: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="parent_department",
        foreign_keys="[Department.parent_id]",
    )
    parent_department: Mapped["Department | None"] = relationship(
        "Department",
        back_populates="child_departments",
        foreign_keys="[Department.parent_id]",
        remote_side="[Department.external_id]",
    )
    users: Mapped[list[User]] = relationship(
        "User", back_populates="department"
    )
