from typing import Any

from fastapi import status

from core.exceptions.bitrix24 import BitrixApiError
from core.logger import logger
from integrations.bitrix_services.base_bitrix_client import (
    BaseBitrixEntityClient,
)
from integrations.bitrix_services.decorators import handle_bitrix_errors
from schemas.enums import EntityTypeAbbr
from schemas.product_schemas import (  # ProductEntityCreate,
    ListProductEntity,
    ProductCreate,
    ProductUpdate,
)


# from ..bitrix_services.base_bitrix_services import BaseBitrixEntityClient
# from ..bitrix_services.bitrix_api_client import BitrixAPIClient
# from ..decorators import handle_bitrix_errors
# from ..exceptions import BitrixApiError, ProductTransformationError
# from ..file_download_service import FileDownloadService
# from ..product_images.product_image_bitrix_service import (
#     ProductImageService
# )
# from .product_data_raw import ProductRawDataService
# from .product_transformation_service import ProductTransformationService


class ProductBitrixClient(
    BaseBitrixEntityClient[ProductCreate, ProductUpdate]
):
    entity_name = "product"  # "catalog.product" crm = False
    create_schema = ProductCreate
    update_schema = ProductUpdate

    # def __init__(
    #     self,
    #     bitrix_client: BitrixAPIClient,
    # ):
    #     super().__init__(bitrix_client)
    #     self._raw_data_service: ProductRawDataService | None = None
    #     self._file_download_service: FileDownloadService | None = None
    #     self._transform_service: ProductTransformationService | None = None
    #     self._image_service: ProductImageService | None = None

    # @property
    # def raw_data_service(self) -> ProductRawDataService:
    #     if not self._raw_data_service:
    #         self._raw_data_service = ProductRawDataService(
    #             self.bitrix_client
    #         )
    #     return self._raw_data_service

    # @property
    # def file_download_service(self) -> FileDownloadService:
    #     if not self._file_download_service:
    #         self._file_download_service = FileDownloadService()
    #     return self._file_download_service

    # @property
    # def transformation_service(self) -> ProductTransformationService:
    #     if not self._transform_service:
    #         self._transform_service = ProductTransformationService(
    #             self.file_download_service
    #         )
    #     return self._transform_service

    # @property
    # def image_service(self) -> ProductImageService:
    #     if not self._image_service:
    #         self._image_service = ProductImageService(
    #             self.raw_data_service, self.file_download_service
    #         )
    #     return self._image_service

    @handle_bitrix_errors()
    async def get_entity_products(
        self,
        owner_id: int,
        owner_type: EntityTypeAbbr,
    ) -> ListProductEntity:
        """Получение товаров в сущности по ID"""
        logger.debug(
            f"Fetching products of owner type:{owner_type} ID={owner_id}"
        )
        params: dict[str, Any] = {
            "filter": {
                "=ownerType": owner_type.value,
                "=ownerId": owner_id,
            }
        }
        response = await self.bitrix_client.call_api(
            "crm.item.productrow.list",
            params=params,
        )
        if (
            not (entity_data := response.get("result"))
            or "productRows" not in entity_data
        ):
            logger.warning(
                f"Products not found for {owner_type} ID={owner_id}"
            )
            return ListProductEntity(result=[])
        return ListProductEntity(result=entity_data["productRows"])

    async def _get_product_catalog(self, product_id: int) -> ProductCreate:
        """Получение каталога товара"""
        return await self.get(entity_id=product_id)  # , crm=False)

    @handle_bitrix_errors()
    async def set_entity_products(
        self,
        owner_id: int,
        owner_type: EntityTypeAbbr,
        products: ListProductEntity,
    ) -> ListProductEntity:
        """
        Устанавливает товарные позиции в сущность CRM.
        Перезаписывает все существующие товарные позиции.

        Args:
            owner_id: Идентификатор объекта CRM
            owner_type: Краткий символьный код типа объекта CRM
            products: Список товарных позиций для установки

        Returns:
            Ответ от Bitrix24 API
        """
        logger.debug(f"Setting products of {owner_type} ID={owner_id}")
        # Формируем параметры запроса
        params: dict[str, Any] = {
            "ownerId": owner_id,
            "ownerType": owner_type.value,
            "productRows": products.to_bitrix_dict(),
        }
        response = await self.bitrix_client.call_api(
            "crm.item.productrow.set", params=params
        )

        # Проверяем ответ
        if (
            not (entity_data := response.get("result"))
            or "productRows" not in entity_data
        ):
            logger.error(
                f"Failed to set product rows for owner type:{owner_type} "
                f"ID={owner_id}"
            )
            raise BitrixApiError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_description=(
                    f"Failed to set product rows for owner type:{owner_type} "
                    f"ID={owner_id}"
                ),
            )
        return ListProductEntity(result=entity_data["productRows"])

    async def update_deal_product_from_invoice(
        self, deal_id: int, invoice_id: int
    ) -> bool:
        """
        Проверяет и обновляет товары в сделке из счёта.

        Args:
            deal_id: ID сделки
            invoice_id: ID счёта

        Returns:
            bool
        """
        try:
            deal_products = await self.get_entity_products(
                deal_id, EntityTypeAbbr.DEAL
            )
            invoice_products = await self.get_entity_products(
                invoice_id, EntityTypeAbbr.INVOICE
            )
            if not deal_products.equals_ignore_owner(invoice_products):
                logger.info(
                    f"Products not equals deal:{deal_id}, "
                    f"invoice:{invoice_id}"
                )
                await self.set_entity_products(
                    deal_id, EntityTypeAbbr.DEAL, invoice_products
                )
            logger.info(
                f"Successfully updated products for deal:{deal_id} "
                f"from invoice:{invoice_id}"
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"Error updating products deal:{deal_id}, "
                f"invoice:{invoice_id}. Error: {e!s}"
            )
            return False
        else:
            return True

    # async def transform_product_fields(self, product_id: int) -> bool:
    #     """
    #     Преобразование полей товара

    #     Args:
    #         product_id: ID товара в Битрикс24

    #     Returns:
    #         bool: Успешность преобразования
    #     """
    #     try:
    #         logger.info(
    #             f"Starting field transformation for product {product_id}"
    #         )

    #         # Получаем данные товара
    #         product_data = await self.get(product_id)
    #         # product_data_dict = await self.raw_data_service.get(
    #               product_id
    #          )
    #         if not product_data:  # or not product_data_dict:
    #             logger.error(
    #                 f"Product {product_id} not found or empty result"
    #             )
    #             return False
    #         trans_service = self.transformation_service
    #         text_fields = await trans_service.transform_product_fields(
    #             product_data=product_data,
    #             product_id=product_id,
    #             # product_data_dict=product_data_dict,
    #         )
    #         # Обновляем текстовые поля
    #         if text_fields:
    #             logger.info(
    #                 f"Updating {len(text_fields)} text fields for product "
    #                 f"{product_id}"
    #             )
    #             text_fields["external_id"] = product_id
    #             product_update = ProductUpdate(**text_fields)
    #             await self.update(product_update)

    #         # Обновляем изображение
    #         # if image_fields:
    #         #     logger.info(f"Updating image for product {product_id}")
    #         #     success = await self.raw_data_service.update(
    #         #         product_id, image_fields
    #         #     )
    #         #     if not success:
    #         #         logger.error(
    #         #             f"Failed to update image for product {product_id}"
    #         #         )
    #         #         return False

    #         if not text_fields:  # and not image_fields:
    #             logger.info(f"No fields to update for product {product_id}")

    #         logger.info(f"Successfully transformed product {product_id}")
    #         return True

    #     except ProductTransformationError as e:
    #         logger.error(
    #             f"Transformation error for product {product_id}: {e}"
    #         )
    #         return False
    #     except Exception as e:
    #         logger.error(
    #             f"Unexpected error transforming product {product_id}: {e}",
    #             exc_info=True,
    #         )
    #         return False
