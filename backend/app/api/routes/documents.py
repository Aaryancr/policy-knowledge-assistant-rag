"""Document management endpoints: upload, listing, details, chunk inspection, and deletion."""

import hashlib
import os
import re
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.config import get_settings
from app.database import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.schemas.document import (
    ChunkResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.queue import QueueError, enqueue_ingestion_job

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def _validate_file_content(ext: str, content_header: bytes) -> None:
    """Validates magic bytes / signatures to detect spoofed file extensions."""
    if ext == ".pdf":
        if not content_header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file: Missing %PDF- magic signature",
            )
    elif ext == ".docx":
        # DOCX is a zip archive format, begins with PK\x03\x04
        if not content_header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DOCX file: Missing ZIP archive signature",
            )
    elif ext == ".txt":
        # Check that txt is not an executable or binary file containing null bytes
        if b"\x00" in content_header[:512]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TXT file: Binary content detected",
            )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Admin-only document upload endpoint.
    
    Validates file format, size, and magic bytes, performs SHA-256 deduplication,
    persists the document record, and enqueues an asynchronous ingestion job.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a valid filename",
        )

    # 1. Path traversal prevention & extension check
    raw_filename = os.path.basename(file.filename)
    name_part, ext_part = os.path.splitext(raw_filename)
    ext = ext_part.lower()

    if ext not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {list(ALLOWED_MIME_TYPES.keys())}",
        )

    # Sanitize filename: alphanumeric, underscores, hyphens, and periods only
    clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name_part)[:100] + ext
    doc_title = title.strip() if (title and title.strip()) else name_part

    # 2. Read and stream content, enforce size limits and compute checksum
    sha256_hash = hashlib.sha256()
    total_size = 0
    chunks_buffer: list[bytes] = []

    # Read first chunk to inspect header magic bytes
    first_chunk = await file.read(4096)
    if not first_chunk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty (0 bytes)",
        )

    _validate_file_content(ext, first_chunk)
    chunks_buffer.append(first_chunk)
    sha256_hash.update(first_chunk)
    total_size += len(first_chunk)

    if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        )

    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
            )
        sha256_hash.update(chunk)
        chunks_buffer.append(chunk)

    digest = sha256_hash.hexdigest()

    # 3. Check for existing identical document (Deduplication)
    dup_query = select(Document).where(Document.checksum_sha256 == digest)
    existing_doc_res = await db.execute(dup_query)
    existing_doc = existing_doc_res.scalar_one_or_none()

    if existing_doc and existing_doc.status == "completed":
        # Find latest completed job
        latest_job_query = (
            select(IngestionJob)
            .where(IngestionJob.document_id == existing_doc.id)
            .order_by(IngestionJob.created_at.desc())
        )
        job_res = await db.execute(latest_job_query)
        latest_job = job_res.scalar_one_or_none()

        return DocumentUploadResponse(
            document_id=existing_doc.id,
            job_id=latest_job.id if latest_job else None,
            status=existing_doc.status,
            title=existing_doc.title,
            filename=existing_doc.filename,
            file_size_bytes=existing_doc.file_size_bytes,
            checksum_sha256=existing_doc.checksum_sha256,
            is_duplicate=True,
            message="Document with identical content already processed. Reusing existing document record.",
            created_at=existing_doc.created_at,
        )

    # 4. Save file to persistent storage directory
    doc_id = uuid.uuid4()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_filename = f"{doc_id}_{clean_name}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    with open(file_path, "wb") as f:
        for chunk in chunks_buffer:
            f.write(chunk)

    # 5. Create database records for Document and IngestionJob
    content_type = file.content_type or ALLOWED_MIME_TYPES[ext]
    new_doc = Document(
        id=doc_id,
        title=doc_title,
        filename=clean_name,
        file_path=file_path,
        file_size_bytes=total_size,
        content_type=content_type,
        checksum_sha256=digest,
        status="pending",
        uploaded_by_id=admin_user.id,
        total_chunks=0,
    )
    db.add(new_doc)

    job_id = uuid.uuid4()
    ingestion_job = IngestionJob(
        id=job_id,
        document_id=doc_id,
        status="queued",
        retry_count=0,
        max_retries=3,
    )
    db.add(ingestion_job)
    await db.commit()
    await db.refresh(new_doc)
    await db.refresh(ingestion_job)

    # 6. Enqueue job into Redis
    try:
        await enqueue_ingestion_job(
            job_id=job_id,
            document_id=doc_id,
            file_path=file_path,
        )
    except QueueError as exc:
        # Prevent misleading "queued" status in database if Redis enqueue failed
        new_doc.status = "failed"
        new_doc.error_message = f"Failed to enqueue to queue: {exc}"
        ingestion_job.status = "failed"
        ingestion_job.error_message = f"Redis enqueue failed: {exc}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion queue is currently unavailable. Upload recorded as failed.",
        ) from exc

    return DocumentUploadResponse(
        document_id=new_doc.id,
        job_id=ingestion_job.id,
        status="queued",
        title=new_doc.title,
        filename=new_doc.filename,
        file_size_bytes=new_doc.file_size_bytes,
        checksum_sha256=new_doc.checksum_sha256,
        is_duplicate=False,
        message="Document uploaded and queued for processing",
        created_at=new_doc.created_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Lists uploaded documents with pagination."""
    count_query = select(func.count(Document.id))
    total_res = await db.execute(count_query)
    total = total_res.scalar_one() or 0

    docs_query = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    docs_res = await db.execute(docs_query)
    docs = docs_res.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieves metadata and processing status for a single document."""
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChunkResponse]:
    """Retrieves partitioned text chunks and metadata for a document (without exposing raw vector floats)."""
    # Verify document exists
    doc_res = await db.execute(select(Document).where(Document.id == document_id))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    chunks_query = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
    )
    chunks_res = await db.execute(chunks_query)
    chunks = chunks_res.scalars().all()

    return [
        ChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            page_number=c.page_number,
            section_title=c.section_title,
            metadata_json=c.metadata_json,
            has_embedding=c.embedding is not None,
        )
        for c in chunks
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Admin-only deletion: deletes document record, cascade-deleting chunks and jobs, and cleans up local storage."""
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    file_path = doc.file_path
    await db.delete(doc)
    await db.commit()

    # Remove file from local disk if it exists
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
