from fastapi import APIRouter

from .bitrix24.bitrix24_router import bitrix24_router


v1_router = APIRouter()

v1_router.include_router(
    bitrix24_router, prefix="/bitrix24", tags=["bitrix24"]
)
