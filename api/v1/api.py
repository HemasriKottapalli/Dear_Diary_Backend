from fastapi import APIRouter
from .auth import router as auth_router
from .diary import router as diary_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(diary_router)