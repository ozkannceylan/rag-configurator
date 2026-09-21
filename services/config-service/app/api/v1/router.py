"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import auth, configs, export, folders, templates, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(configs.router)
api_router.include_router(folders.router)
api_router.include_router(export.router)
api_router.include_router(templates.router)
