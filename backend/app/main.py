"""FastAPI application initialization, middleware, routes, and lifespan lifecycle."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle events."""
    setup_logging(level=settings.LOG_LEVEL)
    logger.info(
        "Application starting up",
        extra={
            "project": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "llm_provider": settings.LLM_PROVIDER,
        },
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Enterprise RAG Policy & Knowledge Assistant backend service with pgvector retrieval.",
    lifespan=lifespan,
)

# CORS configuration for React + Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unexpected server errors, logs structured detail, and returns clean error response."""
    logger.error(
        f"Unhandled server error: {exc}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


# Root health checks (for Docker/Kubernetes probes)
app.include_router(health_router)

# Versioned API routes
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)


