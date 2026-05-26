from enum import StrEnum, auto


class EntityType(StrEnum):
    """Типы сущностей в системе."""

    CONTACT = "Contact"
    COMPANY = "Company"
    LEAD = "Lead"
    DEAL = "Deal"
    USER = "User"
    INVOICE = "Invoice"
    TIMELINE_COMMENT = "TimelineComment"
    PRODUCT = "Product"
    # SUPPLIER_PRODUCT = "SupplierProduct"
    # PRODUCT_IMAGE = "ProductImage"


class EntityTypeAbbr(StrEnum):
    CONTACT = "C"
    COMPANY = "CO"
    LEAD = "L"
    DEAL = "D"
    INVOICE = "SI"
    QUOTE = "Q"
    REQUISITE = "RQ"
    ORDER = "O"


class CommunicationType(StrEnum):
    """Типы коммуникационных каналов."""

    PHONE = auto()
    EMAIL = auto()
    WEB = auto()
    IM = auto()
    LINK = auto()

    @staticmethod
    def has_value(value: str) -> bool:
        """Проверяет, существует ли значение в перечислении."""
        return value in CommunicationType.__members__


COMMUNICATION_TYPES = {
    "phone": CommunicationType.PHONE,
    "email": CommunicationType.EMAIL,
    "web": CommunicationType.WEB,
    "im": CommunicationType.IM,
    "link": CommunicationType.LINK,
}
