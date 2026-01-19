from fastapi import APIRouter
from api.v1 import diary_ai, diary, auth

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(diary.router)
api_router.include_router(diary_ai.router)
