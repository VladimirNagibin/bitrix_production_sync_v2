from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
)


if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


class CommunicationChannel(BaseModel):
    """Схема канала связи (телефон, email, веб, IM и т.п.)."""

    external_id: int | None = Field(None, alias="ID")
    type_id: str | None = Field(None, alias="TYPE_ID")
    value_type: str = Field(..., alias="VALUE_TYPE")
    value: str = Field(..., alias="VALUE")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
    )


class FieldText(BaseModel):
    """Текстовое поле с возможностью указания типа (HTML/TEXT)."""

    text_field: str | None = Field(
        None, validation_alias=AliasChoices("TEXT", "text")
    )  # TEXT
    type_field: str | None = Field(
        "HTML", validation_alias=AliasChoices("TYPE", "type")
    )  # TYPE (HTML/TEXT)

    model_config = ConfigDict(populate_by_name=True)

    def to_bitrix_dict(self, alias_choice: int) -> dict[str, Any]:
        """
        Преобразует модель в словарь для Bitrix API.
        """
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
        Возвращает алиас поля с учётом выбранной схемы.
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
