"""Export all SQLAlchemy models for clean imports and Alembic autogenerate discovery."""

from app.database import Base
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.ingestion_job import IngestionJob
from app.models.chat_log import ChatLog

__all__ = [
    "Base",
    "User",
    "Document",
    "Chunk",
    "IngestionJob",
    "ChatLog",
]
