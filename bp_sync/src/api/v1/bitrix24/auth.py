from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core import settings
from core.exceptions.bitrix24 import BitrixAuthError
from core.logger import logger
from dependencies.dependencies_bitrix import get_oauth_client
from integrations.bitrix_services.bitrix_oauth_client import BitrixOAuthClient


auth_router = APIRouter()
templates = Jinja2Templates(directory=f"{settings.app.base_dir}/templates")


@auth_router.get("/auth/callback", summary="OAuth 2.0 Callback Handler")  # type: ignore
async def handle_auth_callback(
    request: Request,
    oauth_client: Annotated[BitrixOAuthClient, Depends(get_oauth_client)],
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    """
    Handle Bitrix24 OAuth 2.0 callback

    Processes authorization code or error returned from Bitrix24 OAuth server.
    """
    if error or error_description:
        error_msg = error_description or error or "Unknown OAuth error"
        logger.error(f"OAuth callback error: {error_msg}")
        raise BitrixAuthError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error=error or "OAUTH_ERROR",
            error_description=error_description or "Unknown error",
            message=f"OAuth error: {error_msg}",
        )

    if not code:
        logger.warning(
            "Authorization callback received without code parameter"
        )
        raise BitrixAuthError(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Authorization code is required",
        )

    # Обмен кода на токены
    await oauth_client.fetch_token(code)
    logger.info("Successfully obtained access token from Bitrix24")

    return templates.TemplateResponse(
        request, "auth.html", context={"oauth_url": None}
    )


@auth_router.get(
    "/auth/check",
    summary="test",
    description="Test.",
)  # type: ignore[misc]
async def test(
    request: Request,
    oauth_client: Annotated[BitrixOAuthClient, Depends(get_oauth_client)],
) -> HTMLResponse:
    auth_url: str | None = None
    try:
        await oauth_client.get_valid_token()
    except BitrixAuthError as e:
        details = e.details
        if isinstance(details, dict):
            auth_url = cast("dict[str, Any]", details).get("auth_url")
    # TODO: добавить кнопку сброса токена
    return templates.TemplateResponse(
        request, "auth.html", context={"auth_url": auth_url}
    )
