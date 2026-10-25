"""Ingestion job status endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.schemas.document import IngestionJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse:
    """Retrieves current processing state, retry count, timestamps, and errors for an ingestion job."""
    query = select(IngestionJob).where(IngestionJob.id == job_id)
    res = await db.execute(query)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job with ID {job_id} not found",
        )

    return IngestionJobResponse.model_validate(job)


@router.get("/document/{document_id}", response_model=list[IngestionJobResponse])
async def get_jobs_for_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionJobResponse]:
    """Retrieves all historical ingestion jobs associated with a specific document."""
    query = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
    )
    res = await db.execute(query)
    jobs = res.scalars().all()

    return [IngestionJobResponse.model_validate(j) for j in jobs]
