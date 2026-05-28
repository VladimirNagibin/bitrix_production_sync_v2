from typing import Any


FIELDS_BY_TYPE: dict[str, Any] = {
    "str": [
        # deal
        "TITLE",  # title
        "STAGE_ID",  # stage_id
        # lead
        "STATUS_ID",
    ],
    "str_none": [
        # deal
        "ADDITIONAL_INFO",  # "additional_info",
        "CURRENCY_ID",  # "currency_id",
        "TYPE_ID",  # "type_id",
        "SOURCE_ID",  # "source_id",
        "UTM_SOURCE",  # "utm_source",
        "UTM_MEDIUM",  # "utm_medium",
        "UTM_CAMPAIGN",  # "utm_campaign",
        "UTM_CONTENT",  # "utm_content",
        "UTM_TERM",  # "utm_term",
        "COMMENTS",  # "comments",
        "SOURCE_DESCRIPTION",  # "source_description",
        "ORIGINATOR_ID",  # "originator_id",
        "ORIGIN_ID",  # "origin_id",
        "LOCATION_ID",  # location_id
        "REPEAT_SALE_SEGMENT_ID",  # repeat_sale_segment_id:
        "UF_CRM_1759510370",  # introduction_offer
        "UF_CRM_6909F9E973085",  # wz_instagram
        "UF_CRM_6909F9E984D21",  # wz_vc
        "UF_CRM_6909F9E98F0B8",  # wz_avito
        "UF_CRM_6909F9E9994A9",  # wz_maxid
        "UF_CRM_6909F9E9A38DA",  # wz_telegram_username
        "UF_CRM_6909F9E9ADB80",  # wz_telegram_id
        "UF_CRM_1760952984",  # contract
        "UF_CRM_1763483026",  # offer_link
        "UF_CRM_1764696465",  # products_list_as_string
        # lead
        "NAME",  # "name:",
        "SECOND_NAME",  # "second_name:",
        "LAST_NAME",  # "last_name:",
        "POST",  # "post:",
        "COMPANY_TITLE",  # "company_title:",
        "STATUS_DESCRIPTION",  # "status_description:",
        "UF_CRM_1629271075",  # "type_id:",
        "UF_CRM_CALLTOUCHT413",  # "calltouch_site_id:",
        "UF_CRM_CALLTOUCH3ZFT",  # "calltouch_call_id:",
        "UF_CRM_CALLTOUCHWG9P",  # "calltouch_request_id:",
        "UF_CRM_1739432591418",  # "yaclientid:",
        "UF_CRM_INSTAGRAM_WZ",  # "wz_instagram:",
        "UF_CRM_VK_WZ",  # "wz_vc:",
        "UF_CRM_TELEGRAMUSERNAME_WZ",  # "wz_telegram_username:",
        "UF_CRM_TELEGRAMID_WZ",  # "wz_telegram_id:",
        "UF_CRM_AVITO_WZ",  # "wz_avito:",
        "ADDRESS",  # "address:",
        "ADDRESS_2",  # "address_2:",
        "ADDRESS_CITY",  # "address_city:",
        "ADDRESS_POSTAL_CODE",  # "address_postal_code:",
        "ADDRESS_REGION",  # "address_region:",
        "ADDRESS_PROVINCE",  # "address_province:",
        "ADDRESS_COUNTRY",  # "address_country:",
        "ADDRESS_COUNTRY_CODE",  # "address_country_code:",
        # contact
        "ORIGIN_VERSION",  # "origin_version",
        "TYPE_ID",  # "type_id",
        "UF_CRM_61236340EA7AC",  # "deal_type_id",
        "UF_CRM_63E1D6D4B8A68",  # "mgo_cc_entry_id",
        "UF_CRM_63E1D6D4C89EA",  # "mgo_cc_channel_type",
        "UF_CRM_63E1D6D4D40E8",  # "mgo_cc_result",
        "UF_CRM_63E1D6D4DFC93",  # "mgo_cc_entry_point",
        "UF_CRM_63E1D6D515198",  # "mgo_cc_tag_id",
        "UF_CRM_CALLTOUCHWWLX",  # "calltouch_site_id",
        "UF_CRM_CALLTOUCHZLRD",  # "calltouch_call_id",
        "UF_CRM_CALLTOUCHZGWC",  # "calltouch_request_id",
        # company
        "BANKING_DETAILS",  # "banking_details",
        "ADDRESS_LEGAL",  # "address_legal",
        "UF_CRM_1596031539",  # "address_company",
        "UF_CRM_1596031556",  # "province_company",
        "UF_CRM_607968CE029D8",  # "city",
        "UF_CRM_607968CE0F3A4",  # "source_external",
        "COMPANY_TYPE",  # "company_type_id",
        "UF_CRM_1637554945",  # "source_id",
        "UF_CRM_61974C16F0F71",  # "deal_type_id",
        "INDUSTRY",  # "industry_id",
        "EMPLOYEES",  # "employees_id",
        "UF_CRM_63F2F6E58EE14",  # "mgo_cc_entry_id",
        "UF_CRM_63F2F6E5A6DE8",  # "mgo_cc_channel_type",
        "UF_CRM_63F2F6E5BEAEE",  # "mgo_cc_result",
        "UF_CRM_63F2F6E5D8B28",  # "mgo_cc_entry_point",
        "UF_CRM_63F2F6E630D9C",  # "mgo_cc_tag_id",
        "UF_CRM_66618114BF72A",  # "calltouch_site_id",
        "UF_CRM_66618115024C3",  # "calltouch_call_id",
        "UF_CRM_66618115280F4",  # "calltouch_request_id",
        "UF_CRM_63F2F6E50BBDC",  # "wz_instagram",
        "UF_CRM_63F2F6E52BC88",  # "wz_vc",
        "UF_CRM_63F2F6E544CDC",  # "wz_telegram_username",
        "UF_CRM_63F2F6E5602C1",  # "wz_telegram_id",
        "UF_CRM_63F2F6E5766C6",  # "wz_avito",
        "UF_CRM_1630507939",  # "position_head",
        "UF_CRM_1630508048",  # "basis_operates",
        "UF_CRM_1632315102",  # "position_head_genitive",
        "UF_CRM_1632315157",  # "basis_operates_genitive",
        "UF_CRM_1632315337",  # "payment_delay_genitive",
        "UF_CRM_1633583719",  # "full_name_genitive",
        "UF_CRM_1623915176",  # "current_contract",
        "UF_CRM_1654683828",  # "current_number_contract",
    ],
    "int": [
        # deal
        "ID",  # "external_id",
        "CATEGORY_ID",  # "category_id" : 0, 1, 2 - funnels
        "ASSIGNED_BY_ID",  # "assigned_by_id",
        "CREATED_BY_ID",  # "created_by_id",
        "MODIFY_BY_ID",  # "modify_by_id",
    ],
    "int_none": [
        # deal
        "PROBABILITY",  # "probability",
        "LEAD_ID",  # "lead_id",
        "COMPANY_ID",  # "company_id",
        "CONTACT_ID",  # "contact_id",
        "LAST_ACTIVITY_BY",  # "last_activity_by",
        "MOVED_BY_ID",  # "moved_by_id",
        "QUOTE_ID",  # quote_id
        "UF_CRM_1759510532",  # delivery_days
        "UF_CRM_1759510662",  # warranty_months
        "UF_CRM_1759510807",  # begining_condition_payment_percentage
        "UF_CRM_1759510842",  # shipping_condition_payment_percentage
        # lead
        "UF_CRM_1598882174",  # "main_activity_id",
        "UF_CRM_1697036607",  # "deal_failure_reason_id",
        "ADDRESS_LOC_ADDR_ID",  # "address_loc_addr_id",
        # contact
        "UF_CRM_1598882745",  # "main_activity_id",
        "UF_CRM_6539DA9518373",  # "deal_failure_reason_id",
        # company
        "UF_CRM_1598882910",  # "main_activity_id",
        "UF_CRM_65A8D8C72059A",  # "deal_failure_reason_id",
        "UF_CRM_1631941968",  # "shipping_company_id",
        "UF_CRM_1631903199",  # "shipping_company ???",
        "UF_CRM_1623833602",  # "parent_company_id",
    ],
    "bool": [  # Y / N
        # deal
        "IS_MANUAL_OPPORTUNITY",  # "is_manual_opportunity",
        "CLOSED",  # "closed",
        "IS_NEW",  # "is_new",
        "IS_RECURRING",  # "is_recurring",
        "IS_RETURN_CUSTOMER",  # "is_return_customer",
        "IS_REPEATED_APPROACH",  # "is_repeated_approach",
        "OPENED",  # "opened",
        # lead
        "HAS_PHONE",  # "has_phone"
        "HAS_EMAIL",  # "has_email"
        "HAS_IMOL",  # "has_imol"
        # contact
        "EXPORT",  # "export",
        # company
        "IS_MY_COMPANY",  # "is_my_company",
    ],
    "bool_none": [  # 1 / 0
        # deal
        "UF_CRM_1763633586",  # without_offer
        "UF_CRM_1763633629",  # without_contract
        # lead
        "UF_CRM_1623830089",  # "is_shipment_approved"
        # contact
        "UF_CRM_60D97EF75E465",  # "is_shipment_approved"
        # company
        "UF_CRM_61974C16DBFBF",  # "is_shipment_approved"
    ],
    "datetime": [
        # deal
        "DATE_CREATE",  # "date_create",
        "DATE_MODIFY",  # "date_modify",
        "BEGINDATE",  # "begindate",
        "CLOSEDATE",  # "closedate",
    ],
    "datetime_none": [
        # deal
        "LAST_ACTIVITY_TIME",  # "last_activity_time",
        "LAST_COMMUNICATION_TIME",  # "last_communication_time",
        "MOVED_TIME",  # "moved_time",
        "UF_CRM_1763626692",  # date_answer_client
        # lead
        "BIRTHDATE",  # "birthdate"
        "DATE_CLOSED",  # "date_closed"
        # contact
        "UF_CRM_63E1D6D4EC444",  # "mgo_cc_create",
        "UF_CRM_63E1D6D5051DE",  # "mgo_cc_end",
        # company
        "UF_CRM_63F2F6E5F1691",  # "mgo_cc_create",
        "UF_CRM_63F2F6E6181EE",  # "mgo_cc_end",
        "UF_CRM_1623835088",  # "date_last_shipment",
    ],
    "float": [
        # deal
        "OPPORTUNITY",  # "opportunity",
        "TAX_VALUE",  # tax_value
        # company
        "REVENUE",  # "revenue",
    ],
    "enums": [
        # deal
        "STAGE_SEMANTIC_ID",  # "stage_semantic_id",
        "UF_CRM_1763479557",  # status_deal
        # lead
        "STATUS_SEMANTIC_ID",  # "status_semantic_id",
        "UF_CRM_1772448257",  # failure_reason
    ],
    "list": [
        # deal
        "CONTACT_IDS",  # contact_ids
        # lead
        "PHONE",  # "phone",
        "EMAIL",  # "email",
        "WEB",  # "web",
        "IM",  # "im",
        "LINK",  # "link",
        # contact
        "UF_CRM_1629106625",  # "additional_responsables",
        # company
        "UF_CRM_1629106458",  # "additional_responsables",
        "UF_CRM_1623833623",  # "contracts",
    ],
    "money": [
        # deal
        "UF_CRM_1760872964",  # half_amount
        # lead
    ],
}


FIELDS_BY_TYPE_ALT: dict[str, Any] = {
    "str": [
        # deal
        "title",
        "stage_id",
        # lead
        "status_id",
    ],
    "str_none": [
        # deal
        "additional_info",
        "currency_id",
        "type_id",
        "source_id",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "wz_instagram",
        "wz_vc",
        "wz_telegram_username",
        "wz_telegram_id",
        "wz_avito",
        "wz_maxid",
        "comments",
        "source_description",
        "originator_id",
        "origin_id",
        "location_id",
        "repeat_sale_segment_id",
        "contract",
        "offer_link",
        "products_list_as_string",
        # lead
        "name:",
        "second_name:",
        "last_name:",
        "post:",
        "company_title:",
        "status_description:",
        "address:",
        "address_2:",
        "address_city:",
        "address_postal_code:",
        "address_region:",
        "address_province:",
        "address_country:",
        "address_country_code:",
        # contact
        "origin_version",
        "deal_type_id",
        # company
        "banking_details",
        "address_legal",
        "address_company",
        "province_company",
        "company_type_id",
        "industry_id",
        "employees_id",
        "position_head",
        "basis_operates",
        "position_head_genitive",
        "basis_operates_genitive",
        "payment_delay_genitive",
        "full_name_genitive",
        "current_contract",
        "current_number_contract",
    ],
    "int": [
        # deal
        "external_id",
        "category_id",  # : 0, 1, 2 - funnels
        "assigned_by_id",
        "created_by_id",
        "modify_by_id",
    ],
    "int_none": [
        # deal
        "probability",
        "lead_id",
        "company_id",
        "contact_id",
        "last_activity_by",
        "moved_by_id",
        "quote_id",
        "delivery_days",
        "warranty_months",
        "begining_condition_payment_percentage",
        "shipping_condition_payment_percentage",
        # lead
        "address_loc_addr_id",
        # "shipping_company ???",
        "parent_company_id",
    ],
    "bool": [  # Y / N
        # deal
        "is_manual_opportunity",
        "closed",
        "is_new",
        "is_recurring",
        "is_return_customer",
        "is_repeated_approach",
        "opened",
        # lead
        "has_phone"
        "has_email"
        "has_imol"
        # contact
        "export",
        # company
        "is_my_company",
    ],
    "bool_none": [  # 1 / 0
        # deal
        "without_offer",
        "without_contract",
    ],
    "datetime": [
        # deal
        "date_create",
        "date_modify",
        "begindate",
        "closedate",
    ],
    "datetime_none": [
        # deal
        "last_activity_time",
        "last_communication_time",
        "moved_time",
        "date_answer_client",
        # lead
        "birthdate",
        "date_closed",
        "date_last_shipment",
    ],
    "float": [
        # deal
        "opportunity",
        "tax_value",
        # company
        "revenue",
    ],
    "enums": [
        # deal
        "stage_semantic_id",
        "status_deal",
        # lead
        "status_semantic_id",
        "failure_reason",
    ],
    "list": [
        # deal
        "contact_ids",
        # lead
        "phone",
        "email",
        "web",
        "im",
        "link",
        # company
        "additional_responsables",
        "additional_responsible",
        "contracts",
    ],
    "money": [
        # deal
        "half_amount",
        # lead
    ],
}

FIELDS_PRODUCT: dict[str, Any] = {
    "int_none": [
        "SORT",  # sort
        "sort",
        "MODIFIED_BY",  # modified_by
        "modifiedBy",
        "CREATED_BY",  # created_by
        "createdBy",
        "CATALOG_ID",  # catalog_id
        "iblockId",
        "SECTION_ID",  # section_id
        "iblockSectionId",
        "VAT_ID",  # vat_id
        "vatId",
        "MEASURE",  # measure
        "measure",
    ],
    "str": [
        "NAME",  # name
        "name",
    ],
    "str_none": [
        "CODE",  # code
        "code",
        "XML_ID",  # xml_id
        "xmlId",
        "CURRENCY_ID",  # currency_id
        "DESCRIPTION",  # description
        "detailText",
        "DESCRIPTION_TYPE",  # description_type
        "detailTextType",
    ],
    "float_none": [
        "PRICE",  # price
    ],
    "bool_none": [  # Y / N
        "ACTIVE",  # active
        "active",
        "VAT_INCLUDED",  # vat_included
        "vatIncluded",
    ],
    "dict_none_str": [
        "PROPERTY_111",
        "property111",
        "PROPERTY_115",
        "property115",
        "PROPERTY_117",
        "property117",
        "PROPERTY_119",
        "property119",
        "PROPERTY_133",
        "property133",
        "PROPERTY_141",
        "property141",
    ],
    "dict_none_dict": [
        "PROPERTY_113",
        "property113",
        "PROPERTY_121",
        "property121",
        "PROPERTY_123",
        "property123",
        "PROPERTY_125",
        "property125",
        "PROPERTY_127",
        "property127",
        "PROPERTY_129",
        "property129",
        "PROPERTY_131",
        "property131",
    ],
    "datetime_none": [
        "DATE_CREATE",  # date_create
        "dateCreate",
        "TIMESTAMP_X",  # date_modify
        "TIMESTAMP_X",
    ],
}

FIELDS_PRODUCT_ALT: dict[str, Any] = {
    "int_none": [
        "sort",
        "modified_by",
        "created_by",
        "catalog_id",
        "section_id",
        "vat_id",
        "measure",
    ],
    "str": [
        "name",
    ],
    "str_none": [
        "code",
        "xml_id",
        "currency_id",
        "description",
        "description_type",
    ],
    "float_none": [
        "price",
    ],
    "bool_none": [  # Y / N
        "active",
        "vat_included",
    ],
    "dict_none_str": [
        "link",
        "original_name",
        "standards",
        "article",
        "brend",
        "source",
    ],
    "dict_none_dict": [
        "additional_description",
        "characteristics",
        "characteristics_for_print",
        "complect_for_print",
        "complects",
        "description_for_print",
        "standards_for_print",
    ],
    "datetime_none": [
        "date_create",
        "date_modify",
    ],
    "json_none": [
        "specifications",
        "configuration",
    ],
    "exclude_b24": [
        "ownerId",
        "ownerType",
        "internal_id",
        "created_at",
        "updated_at",
        "is_deleted_in_bitrix",
        "external_id",
        "sort",
        "type",
        "store_id",
    ],
}

FIELDS_USER: dict[str, Any] = {
    "str_none": [
        "NAME",  # "name",
        "SECOND_NAME",  # "second_name",
        "LAST_NAME",  # "last_name",
        "XML_ID",  # "xml_id",
        "PERSONAL_GENDER",  # "personal_gender",
        "WORK_POSITION",  # "work_position",
        "USER_TYPE",  # "user_type",
        "TIME_ZONE",  # "time_zone",
        "PERSONAL_CITY",  # "personal_city",
        "EMAIL",  # "email",
        "PERSONAL_MOBILE",  # "personal_mobile",
        "WORK_PHONE",  # "work_phone",
        "PERSONAL_WWW",  # "personal_www",
    ],
    "datetime_none": [
        "LAST_LOGIN",  # "last_login",
        "DATE_REGISTER",  # "date_register",
        "PERSONAL_BIRTHDAY",  # "personal_birthday",
        "UF_EMPLOYMENT_DATE",  # "employment_date",
        "UF_USR_1699347879988",  # "date_new",
    ],
    "bool": [  # Y / N
        "ACTIVE",  # "active",
        "IS_ONLINE",  # "is_online",
    ],
    "list_in_int": [
        "UF_DEPARTMENT",  # "department_id",
    ],
}

FIELDS_USER_ALT: dict[str, Any] = {
    "str_none": [
        "name",
        "second_name",
        "last_name",
        "xml_id",
        "personal_gender",
        "work_position",
        "user_type",
        "time_zone",
        "personal_city",
        "email",
        "personal_mobile",
        "work_phone",
        "personal_www",
    ],
    "datetime_none": [
        "last_login",
        "date_register",
        "personal_birthday",
        "employment_date",
        "date_new",
    ],
    "bool": [  # Y / N
        "active",
        "is_online",
    ],
    "list_in_int": [
        "department_id",
    ],
}

FIELDS_TIMELINE_COMMENT: dict[str, Any] = {}

FIELDS_SUPPLIER_PRODUCT: dict[str, tuple[tuple[str, str], ...]] = {
    "simple_fields": (
        ("name", "str"),
        ("active", "str"),
        ("sort", "int"),
        ("measure", "int"),
        ("price", "float"),
        ("currency_id", "str"),
    ),
    "complex_fields": (
        ("link", "str"),
        ("original_name", "str"),
        ("standarts", "str"),
        ("article", "str"),
    ),
    "individual_fields": (
        ("internal_section_id", "str"),
        ("brend", "str"),
        ("description", "str"),
        ("characteristics", "str"),
        ("complects", "str"),
        ("detail_picture", "str"),
        ("more_photos", "str"),
    ),
}

FIELD_LABELS_RU = {
    "name": "Название товара",
    "code": "Символьный код",
    "brend": "Бренд",
    "article": "Артикул",
    "measure": "Единица измерения(9-шт, 11-упак)",
    "price": "Цена",
    "currency_id": "Валюта",
    "active": "Активность",
    "sort": "Сортировка",
    "xml_id": "Внешний код",
    "link": "Ссылки",
    "original_name": "Оригинальное название",
    "standarts": "Стандарты",
    # Специальные поля поставщика
    "supplier_category": "Категория поставщика",
    "supplier_subcategory": "Подкатегория поставщика",
    "internal_section_id": "Раздел в Битрикс24",
    # Поля предложений/описания
    "preview_for_offer": "Анонс для предложения",
    "description_for_offer": "Описание для предложения",
    "detail_picture": "Детальная картинка",
    "preview_picture": "Картинка анонса",
    "more_photos": "Галерея картинок",
    "more_photo": "Дополнительные картинки",
    # Сложные поля
    "characteristics": "Характеристики",
    "complects": "Комплектация",
    # Добавьте остальные поля по необходимости
    "description": "Описание",
    "quantity": "Количество",
    "vat_id": "Ставка НДС",
    "weight": "Вес",
    # ...
}
