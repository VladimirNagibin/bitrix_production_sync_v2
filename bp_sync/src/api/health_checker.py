from fastapi import APIRouter

from schemas.response_schema import SuccessResponse


health_router = APIRouter()


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
    "/test",
    summary="test",
    description="Test.",
)  # type: ignore[misc]
async def test() -> SuccessResponse:
    # try:
    #     raise SettingsError(message="test")
    # except BaseAppException as e:
    #     logger.error("Testing error: %s", e, exc_info=True)
    #     raise

    return SuccessResponse(message="test", data={"status": "test"})
