"""Question answering and RAG query endpoints."""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.chat_log import ChatLog
from app.models.user import User
from app.schemas.chat import (
    ChatLogResponse,
    CitationResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.answering import generate_grounded_answer
from app.services.retrieval import retrieve_chunks

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("app.chat")


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Answers employee policy questions grounded in document evidence with verified citations."""
    # 1. Retrieve evidence chunks from PostgreSQL with pgvector
    try:
        retrieved_chunks = await retrieve_chunks(
            question=request.question,
            db=db,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # 2. Synthesize answer with LLM and validate citation integrity
    answer_result = await generate_grounded_answer(
        question=request.question,
        retrieved_chunks=retrieved_chunks,
    )

    # 3. Persist audit log in database
    log_id = uuid.uuid4()
    chat_log = ChatLog(
        id=log_id,
        user_id=current_user.id,
        query=answer_result.question,
        retrieved_chunk_ids=[str(c.chunk_id) for c in answer_result.retrieved_chunks],
        answer=answer_result.answer,
        is_unanswerable=answer_result.is_unanswerable,
        confidence_score=answer_result.confidence_score,
        latency_ms=answer_result.latency_ms,
    )
    db.add(chat_log)
    await db.commit()

    citations_resp = [
        CitationResponse(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            document_filename=c.document_filename,
            page_number=c.page_number,
            section_title=c.section_title,
            snippet=c.snippet,
        )
        for c in answer_result.citations
    ]

    return QueryResponse(
        question=answer_result.question,
        answer=answer_result.answer,
        is_unanswerable=answer_result.is_unanswerable,
        citations=citations_resp,
        confidence_score=answer_result.confidence_score,
        latency_ms=answer_result.latency_ms,
        chat_log_id=log_id,
    )


@router.get("/logs", response_model=list[ChatLogResponse])
async def list_chat_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatLogResponse]:
    """Retrieves chat logs. Admins can view all history; employees can view their own."""
    stmt = select(ChatLog)
    if current_user.role != "admin":
        stmt = stmt.where(ChatLog.user_id == current_user.id)

    stmt = stmt.order_by(ChatLog.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [ChatLogResponse.model_validate(l) for l in logs]
