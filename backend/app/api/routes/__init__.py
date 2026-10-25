"""API routes package."""

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router

__all__ = [
    "auth_router",
    "chat_router",
    "documents_router",
    "health_router",
    "jobs_router",
]
