from integrations.bitrix_services.base_bitrix_client import (
    BaseBitrixEntityClient,
)
from schemas.contact_schemas import ContactCreate, ContactUpdate


class ContactBitrixClient(
    BaseBitrixEntityClient[ContactCreate, ContactUpdate]
):
    entity_name = "contact"
    create_schema = ContactCreate
    update_schema = ContactUpdate
