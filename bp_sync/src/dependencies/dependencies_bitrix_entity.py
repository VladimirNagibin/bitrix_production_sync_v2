from collections.abc import AsyncGenerator  # , Callable
from typing import Annotated

from fastapi import Depends

# from ..bitrix_services.bitrix_api_client import BitrixAPIClient
# from ..companies.company_bitrix_services import CompanyBitrixClient
from integrations.bitrix_services.contact_bitrix_client import (
    ContactBitrixClient,
)
from integrations.bitrix_services.product_bitrix_client import (
    ProductBitrixClient,
)

# from ..deals.deal_bitrix_services import DealBitrixClient
# from ..entities.entities_bitrix_services import EntitiesBitrixClient
# from ..leads.lead_bitrix_services import LeadBitrixClient
# from ..products.product_bitrix_services import ProductBitrixClient
# from ..suppliers.repositories.supplier_product_repo import (
#     SupplierProductRepository
# )
# from ..timeline_comments.timeline_comment_bitrix_services import (
#     TimeLineCommentBitrixClient,
# )
# from ..users.user_bitrix_services import UserBitrixClient
from .dependencies_bitrix import (
    DependencyBitrixContainer,
    get_dependency_container,
)


# from .dependencies_suppliers import get_supplier_product_repo


# async def get_deal_bitrix_client(
# ) -> AsyncGenerator[DealBitrixClient, None]:
#     """Зависимость для клиента сделок"""
#     client = await dependency_container.get_entity_client(DealBitrixClient)
#     yield client


async def get_contact_bitrix_client(
    dependency_container: Annotated[
        DependencyBitrixContainer, Depends(get_dependency_container)
    ],
) -> AsyncGenerator[ContactBitrixClient]:
    """Зависимость для клиента сделок"""
    client = await dependency_container.get_entity_client(ContactBitrixClient)
    yield client


async def get_product_bitrix_client(
    dependency_container: Annotated[
        DependencyBitrixContainer, Depends(get_dependency_container)
    ],
) -> AsyncGenerator[ProductBitrixClient]:
    """Зависимость для клиента товаров"""
    client = await dependency_container.get_entity_client(ProductBitrixClient)
    yield client


# async def get_company_bitrix_client() -> (
#     AsyncGenerator[CompanyBitrixClient, None]
# ):
#     """Зависимость для клиента сделок"""
#     client = await dependency_container.get_entity_client(
#         CompanyBitrixClient
#     )
#     yield client


# async def get_lead_bitrix_client(
# ) -> AsyncGenerator[LeadBitrixClient, None]:
#     """Зависимость для клиента сделок"""
#     client = await dependency_container.get_entity_client(LeadBitrixClient)
#     yield client


# async def get_user_bitrix_client(
#     api_client: BitrixAPIClient = Depends(get_api_client),
# ) -> AsyncGenerator[UserBitrixClient, None]:
#     """Зависимость для клиента пользователей"""
#     yield UserBitrixClient(api_client)


# async def get_timeline_comment_bitrix_client(
#     api_client: BitrixAPIClient = Depends(get_api_client),
# ) -> AsyncGenerator[TimeLineCommentBitrixClient, None]:
#     """Зависимость для клиента комментариев в таймлайне"""
#     yield TimeLineCommentBitrixClient(api_client)


# async def get_product_bitrix_client(
#     api_client: BitrixAPIClient = Depends(get_api_client),
# ) -> AsyncGenerator[ProductBitrixClient, None]:
#     """Зависимость для клиента товаров"""
#     yield ProductBitrixClient(api_client)


# async def get_entity_bitrix_client(
#     deal_client: DealBitrixClient = Depends(get_deal_bitrix_client),
#     contact_client: ContactBitrixClient = Depends(
#         get_contact_bitrix_client
#     ),
#     company_client: CompanyBitrixClient = Depends(
#         get_company_bitrix_client
#     ),
#     user_client: UserBitrixClient = Depends(get_user_bitrix_client),
#     product_client: ProductBitrixClient = Depends(
#     get_product_bitrix_client
#     ),
#     # supplier_repo: SupplierProductRepository = Depends(
#     #     get_supplier_product_repo
#     # ),
# ) -> AsyncGenerator[EntitiesBitrixClient, None]:
#     """Зависимость для агрегированного клиента сущностей"""
#     entity_client = EntitiesBitrixClient(
#         contact_bitrix_client=contact_client,
#         company_bitrix_client=company_client,
#         deal_bitrix_client=deal_client,
#         user_bitrix_client=user_client,
#         product_bitrix_client=product_client,
#         # supplier_repo=supplier_repo,
#     )
#     yield entity_client


# def get_deal_client_() -> AsyncGenerator[DealBitrixClient, None]:
#    """Зависимость для клиента сделок"""
#    # Явно указываем тип
#    entity_client_func: Callable[
#        [], AsyncGenerator[DealBitrixClient, None]
#    ] = get_entity_client(DealBitrixClient)
#    return entity_client_func()
