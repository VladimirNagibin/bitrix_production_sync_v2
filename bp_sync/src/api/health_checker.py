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


@health_router.get(
    "/test",
    summary="test",
    description="Test.",
)  # type: ignore[misc]
async def test() -> SuccessResponse:
    # from core.exceptions.base import BaseAppException
    # from core.exceptions.settings import SettingsError
    # from core.logger import logger
    # try:
    #     raise SettingsError(message="test error")
    # except BaseAppException as e:
    #     logger.error("Testing error: %s", e, exc_info=True)
    #     raise

    return SuccessResponse(message="test", data={"status": "test"})
