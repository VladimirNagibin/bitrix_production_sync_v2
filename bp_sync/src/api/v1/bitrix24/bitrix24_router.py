from fastapi import APIRouter

from .auth import auth_router


bitrix24_router = APIRouter()

# Подключаем все модули
bitrix24_router.include_router(auth_router, prefix="", tags=["auth"])
