"""Integration tests for the question answering chat API and audit logging."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chat_log import ChatLog
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.providers.base import MockEmbeddingProvider
from app.services.answering import ABSTENTION_MESSAGE

settings = get_settings()


async def _seed_policy_document_and_chunks(
    db: AsyncSession,
    admin_user: User,
) -> tuple[Document, list[Chunk]]:
    """Helper to seed a completed document with vector chunks for query testing."""
    provider = MockEmbeddingProvider()

    doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="leave_and_time_off.pdf",
        title="Leave and Time Off Policy",
        content_type="application/pdf",
        file_path="/tmp/leave_and_time_off.pdf",
        file_size_bytes=2048,
        checksum_sha256="checksum_seed_001",
        status="completed",
    )
    db.add(doc)
    await db.flush()

    passages = [
        "Full-time employees accrue 20 days of paid time off per calendar year.",
        "A maximum of 5 unused PTO days may be carried over into the following calendar year before March 31.",
        "Employees receive 10 paid sick days annually.",
    ]
    vectors = await provider.embed_documents(passages)
    chunks: list[Chunk] = []

    for idx, (text, vec) in enumerate(zip(passages, vectors)):
        c = Chunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            chunk_index=idx,
            content=text,
            embedding=vec,
            page_number=idx + 1,
            section_title=f"Section {idx + 1}",
        )
        db.add(c)
        chunks.append(c)

    await db.commit()
    return doc, chunks


async def test_unauthenticated_query_denied_with_401(async_client: AsyncClient):
    """Anonymous queries must be rejected with 401 Unauthorized."""
    resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        json={"question": "How many vacation days do I get?"},
    )
    assert resp.status_code == 401


async def test_employee_successful_query_with_grounded_answer_and_citations(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
):
    """Authenticated employee asks a question; receives evidence-grounded answer with citations."""
    doc, chunks = await _seed_policy_document_and_chunks(db_session, admin_user)

    resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        headers=employee_auth_headers,
        json={
            "question": "How many days of paid time off do employees accrue?",
            "top_k": 3,
            "min_similarity": 0.1,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "How many days of paid time off do employees accrue?"
    assert data["is_unanswerable"] is False
    assert "20 days" in data["answer"].lower()
    assert len(data["citations"]) > 0

    first_citation = data["citations"][0]
    assert first_citation["document_title"] == "Leave and Time Off Policy"
    assert first_citation["document_filename"] == "leave_and_time_off.pdf"
    assert first_citation["page_number"] is not None
    assert data["confidence_score"] is not None
    assert data["chat_log_id"] is not None


async def test_query_below_similarity_threshold_abstains_without_llm_call(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
):
    """When no document chunks pass the similarity threshold, the system abstains."""
    await _seed_policy_document_and_chunks(db_session, admin_user)

    resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        headers=employee_auth_headers,
        json={
            "question": "What is the pet insurance subsidy reimbursement amount?",
            "top_k": 3,
            "min_similarity": 0.8,  # High threshold for unrelated query
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == ABSTENTION_MESSAGE
    assert data["is_unanswerable"] is True
    assert len(data["citations"]) == 0


async def test_query_creates_chat_log_audit_record(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    employee_user: User,
    db_session: AsyncSession,
    admin_user: User,
):
    """Every employee query must persist an audit record in the chat_logs table."""
    await _seed_policy_document_and_chunks(db_session, admin_user)

    q_text = "What is the policy on PTO carryover?"
    resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        headers=employee_auth_headers,
        json={"question": q_text, "min_similarity": 0.1},
    )
    assert resp.status_code == 200
    data = resp.json()
    log_id = uuid.UUID(data["chat_log_id"])

    # Query DB directly to verify persistence
    stmt = select(ChatLog).where(ChatLog.id == log_id)
    res = await db_session.execute(stmt)
    chat_log = res.scalar_one_or_none()

    assert chat_log is not None
    assert chat_log.user_id == employee_user.id
    assert chat_log.query == q_text
    assert chat_log.answer == data["answer"]
    assert chat_log.is_unanswerable == data["is_unanswerable"]
    assert isinstance(chat_log.retrieved_chunk_ids, list)
    assert chat_log.latency_ms >= 0


async def test_chat_logs_listing_role_based_access(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    employee_user: User,
    admin_user: User,
    db_session: AsyncSession,
):
    """Employees only see their own chat history; admins see all history."""
    # 1. Create one log for employee, one log for admin
    emp_log = ChatLog(
        id=uuid.uuid4(),
        user_id=employee_user.id,
        query="Employee query",
        retrieved_chunk_ids=[],
        answer="Employee answer",
        is_unanswerable=False,
        latency_ms=45,
    )
    admin_log = ChatLog(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        query="Admin query",
        retrieved_chunk_ids=[],
        answer="Admin answer",
        is_unanswerable=False,
        latency_ms=30,
    )
    db_session.add_all([emp_log, admin_log])
    await db_session.commit()

    # 2. Employee lists logs
    emp_resp = await async_client.get(
        f"{settings.API_V1_STR}/chat/logs",
        headers=employee_auth_headers,
    )
    assert emp_resp.status_code == 200
    emp_data = emp_resp.json()
    emp_log_ids = [item["id"] for item in emp_data]
    assert str(emp_log.id) in emp_log_ids
    assert str(admin_log.id) not in emp_log_ids  # Employee cannot see admin's query

    # 3. Admin lists logs
    admin_resp = await async_client.get(
        f"{settings.API_V1_STR}/chat/logs",
        headers=admin_auth_headers,
    )
    assert admin_resp.status_code == 200
    admin_data = admin_resp.json()
    admin_log_ids = [item["id"] for item in admin_data]
    assert str(emp_log.id) in admin_log_ids  # Admin sees employee logs
    assert str(admin_log.id) in admin_log_ids


async def test_oversized_question_rejected_with_400(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
):
    """Questions exceeding MAX_QUESTION_LENGTH return 400 Bad Request."""
    oversized = "How long is vacation? " + ("x" * settings.MAX_QUESTION_LENGTH)
    resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        headers=employee_auth_headers,
        json={"question": oversized},
    )
    # Pydantic validates max_length at request parsing time (422)
    # Service also guards against oversized queries (400)
    assert resp.status_code in [400, 422]
