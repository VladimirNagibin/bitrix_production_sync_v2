from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core import settings
from schemas.response_schema import SuccessResponse


health_router = APIRouter()
templates = Jinja2Templates(directory=f"{settings.app.base_dir}/templates")


@health_router.get(
    "/health",
    summary="check health",
    description="Check health.",
)  # type: ignore[misc]
async def health_check() -> SuccessResponse:
    return SuccessResponse(
        message="check was successful", data={"status": "healthy"}
    )


@health_router.get(
    "/",
    summary="check page",
    description="Simple page.",
    name="index",
)  # type: ignore[misc]
async def simple_page(
    request: Request,
) -> HTMLResponse:
    return templates.TemplateResponse(request, "base.html")


# from typing import Annotated

# from fastapi import Depends

# from dependencies.dependencies_bitrix_entity import (
#     get_contact_bitrix_client
# )
# from services.contacts.contact_bitrix_client import ContactBitrixClient


# @health_router.get(
#     "/test",
#     summary="test",
#     description="Test.",
# )  # type: ignore[misc]
# async def test(
#     contact_bitrix_client: Annotated[
#         ContactBitrixClient, Depends(get_contact_bitrix_client)
#     ],
# ) -> SuccessResponse:

#     client = await contact_bitrix_client.get(2)
#     # await contact_bitrix_client.bitrix_client.oauth_client.
#     #     token_storage.delete_token("access_token")
#     # await contact_bitrix_client.bitrix_client.oauth_client.
#     #     token_storage.delete_token("refresh_token")

#     return SuccessResponse(message="test", data=client.dict())
