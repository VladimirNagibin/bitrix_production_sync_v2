from schemas.contact_schemas import ContactCreate, ContactUpdate
from services.bitrix_services.base_bitrix_client import BaseBitrixEntityClient


class ContactBitrixClient(
    BaseBitrixEntityClient[ContactCreate, ContactUpdate]
):
    entity_name = "contact"
    create_schema = ContactCreate
    update_schema = ContactUpdate
