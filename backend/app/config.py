"""Application settings and environment configuration."""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Application
    PROJECT_NAME: str = "Policy & Knowledge Assistant"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Security & Authentication
    SECRET_KEY: str = Field(
        default="insecure-dev-secret-key-change-in-production-min32chars",
        description="Cryptographic secret key for signing JWTs",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL & pgvector
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_dev_password"
    POSTGRES_DB: str = "policy_rag"

    # Async and Sync Database URLs
    DATABASE_URL: str | None = None
    SYNC_DATABASE_URL: str | None = None

    # Redis Queue & Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_INGESTION_QUEUE: str = "policy_rag_ingestion_queue"

    # Document Upload & Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB limit

    # Chunking & Retrieval Parameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_QUESTION_LENGTH: int = 1000
    TOP_K_RETRIEVAL: int = 5
    MIN_SIMILARITY_THRESHOLD: float = 0.5

    # AI / Provider Settings
    EMBEDDING_PROVIDER: Literal["mock", "openai", "gemini"] = "mock"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    LLM_PROVIDER: Literal["mock", "openai", "gemini"] = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Initial Admin Seeding
    INITIAL_ADMIN_EMAIL: str = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: str = "Admin@ChangeMe123!"
    INITIAL_ADMIN_FULL_NAME: str = "System Administrator"

    def get_database_url(self) -> str:
        """Returns the async database URL, building from components if not explicitly provided."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_sync_database_url(self) -> str:
        """Returns the synchronous database URL for Alembic migrations and CLI commands."""
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid repeated disk reads."""
    return Settings()
