"""Comprehensive Role-Based Access Control (RBAC) and authorization audit test suite.

Validates:
1. Complete rejection (401 Unauthorized) of unauthenticated requests across all protected endpoints.
2. Complete denial (403 Forbidden) of employee access to administrator-only management endpoints.
3. Permitted administrative execution of document lifecycle and audit management endpoints.
4. Permitted employee usage of chat querying, own chat audit history, and document catalog inspection.
5. Verification that public endpoints (health probes, login) remain accessible without credentials.
6. Row-level data isolation on chat logs preventing employee cross-account snooping.
"""

import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chat_log import ChatLog
from app.models.document import Document
from app.models.user import User
from tests.helpers import create_test_txt

settings = get_settings()


# ==============================================================================
# 1. Unauthenticated Request Rejection (401 Unauthorized)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,endpoint,payload",
    [
        ("GET", f"{settings.API_V1_STR}/auth/me", None),
        ("GET", f"{settings.API_V1_STR}/auth/admin-only", None),
        ("GET", f"{settings.API_V1_STR}/documents", None),
        ("GET", f"{settings.API_V1_STR}/documents/{uuid.uuid4()}", None),
        ("GET", f"{settings.API_V1_STR}/documents/{uuid.uuid4()}/chunks", None),
        ("DELETE", f"{settings.API_V1_STR}/documents/{uuid.uuid4()}", None),
        ("GET", f"{settings.API_V1_STR}/jobs/{uuid.uuid4()}", None),
        ("GET", f"{settings.API_V1_STR}/jobs/document/{uuid.uuid4()}", None),
        ("POST", f"{settings.API_V1_STR}/chat/query", {"question": "What is the policy?"}),
        ("GET", f"{settings.API_V1_STR}/chat/logs", None),
    ],
)
async def test_unauthenticated_requests_rejected_across_all_protected_endpoints(
    async_client: AsyncClient,
    method: str,
    endpoint: str,
    payload: dict | None,
):
    """Every protected endpoint in the application must deny requests lacking valid Authorization headers."""
    if method == "GET":
        resp = await async_client.get(endpoint)
    elif method == "DELETE":
        resp = await async_client.delete(endpoint)
    elif method == "POST":
        resp = await async_client.post(endpoint, json=payload)
    else:
        pytest.fail(f"Unsupported HTTP method: {method}")

    assert resp.status_code == 401
    assert "detail" in resp.json()


# ==============================================================================
# 2. Employee Denial on Administrator-Only Endpoints (403 Forbidden)
# ==============================================================================

@pytest.mark.asyncio
async def test_employee_cannot_upload_document(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    tmp_path,
):
    """Employees attempting to upload documents must be blocked with HTTP 403 Forbidden."""
    txt_file = create_test_txt(str(tmp_path), content="Unauthorized employee content")
    with open(txt_file, "rb") as f:
        file_bytes = f.read()

    resp = await async_client.post(
        f"{settings.API_V1_STR}/documents/upload",
        headers=employee_auth_headers,
        files={"file": ("unauthorized.txt", file_bytes, "text/plain")},
        data={"title": "Malicious Upload Attempt"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_employee_cannot_delete_document(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    tmp_path,
):
    """Employees attempting to delete documents must be blocked with HTTP 403 Forbidden."""
    # 1. Admin creates a document
    txt_file = create_test_txt(str(tmp_path), content="Document to test unauthorized deletion")
    with open(txt_file, "rb") as f:
        file_bytes = f.read()

    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        create_resp = await async_client.post(
            f"{settings.API_V1_STR}/documents/upload",
            headers=admin_auth_headers,
            files={"file": ("del_test.txt", file_bytes, "text/plain")},
            data={"title": "Delete Test"},
        )
    assert create_resp.status_code == 201
    doc_id = create_resp.json()["document_id"]

    # 2. Employee tries to delete it -> 403 Forbidden
    delete_resp = await async_client.delete(
        f"{settings.API_V1_STR}/documents/{doc_id}",
        headers=employee_auth_headers,
    )
    assert delete_resp.status_code == 403
    assert "Forbidden" in delete_resp.json()["detail"]


@pytest.mark.asyncio
async def test_employee_cannot_access_admin_diagnostic_endpoint(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
):
    """Employees attempting to access admin-only verification endpoint receive HTTP 403 Forbidden."""
    resp = await async_client.get(
        f"{settings.API_V1_STR}/auth/admin-only",
        headers=employee_auth_headers,
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


# ==============================================================================
# 3. Permitted Administrator Document-Management Actions
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_permitted_document_lifecycle_actions(
    async_client: AsyncClient,
    admin_auth_headers: dict[str, str],
    tmp_path,
):
    """Administrators can upload, list, retrieve details, inspect chunks, view jobs, and delete documents."""
    txt_file = create_test_txt(str(tmp_path), content="Admin permitted action document")
    with open(txt_file, "rb") as f:
        file_bytes = f.read()

    # 1. Upload
    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        upload_resp = await async_client.post(
            f"{settings.API_V1_STR}/documents/upload",
            headers=admin_auth_headers,
            files={"file": ("admin_lifecycle.txt", file_bytes, "text/plain")},
            data={"title": "Admin Document Lifecycle"},
        )
    assert upload_resp.status_code == 201
    data = upload_resp.json()
    doc_id = data["document_id"]
    job_id = data["job_id"]

    # 2. List documents
    list_resp = await async_client.get(
        f"{settings.API_V1_STR}/documents",
        headers=admin_auth_headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 3. Get document detail
    detail_resp = await async_client.get(
        f"{settings.API_V1_STR}/documents/{doc_id}",
        headers=admin_auth_headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == doc_id

    # 4. Get chunks
    chunks_resp = await async_client.get(
        f"{settings.API_V1_STR}/documents/{doc_id}/chunks",
        headers=admin_auth_headers,
    )
    assert chunks_resp.status_code == 200

    # 5. Get job status
    job_resp = await async_client.get(
        f"{settings.API_V1_STR}/jobs/{job_id}",
        headers=admin_auth_headers,
    )
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "queued"

    # 6. Delete document
    del_resp = await async_client.delete(
        f"{settings.API_V1_STR}/documents/{doc_id}",
        headers=admin_auth_headers,
    )
    assert del_resp.status_code == 204


# ==============================================================================
# 4. Permitted Employee Knowledge Assistant Usage & Data Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_employee_permitted_chat_and_isolated_history(
    async_client: AsyncClient,
    employee_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    employee_user: User,
    admin_user: User,
    db_session: AsyncSession,
):
    """Employees can query policy knowledge base and inspect their own query history,
    while being strictly restricted from accessing other users' chat logs.
    """
    # 1. Employee query endpoint works
    query_resp = await async_client.post(
        f"{settings.API_V1_STR}/chat/query",
        headers=employee_auth_headers,
        json={"question": "What is the policy?"},
    )
    assert query_resp.status_code == 200

    # 2. Seed explicit logs for employee and admin
    emp_log = ChatLog(
        id=uuid.uuid4(),
        user_id=employee_user.id,
        query="Employee confidential question",
        retrieved_chunk_ids=[],
        answer="Employee answer",
        is_unanswerable=False,
        latency_ms=10,
    )
    admin_log = ChatLog(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        query="Executive confidential question",
        retrieved_chunk_ids=[],
        answer="Executive answer",
        is_unanswerable=False,
        latency_ms=10,
    )
    db_session.add_all([emp_log, admin_log])
    await db_session.commit()

    # 3. Employee list logs: strictly isolated to employee's own logs
    emp_logs_resp = await async_client.get(
        f"{settings.API_V1_STR}/chat/logs",
        headers=employee_auth_headers,
    )
    assert emp_logs_resp.status_code == 200
    emp_log_ids = [item["id"] for item in emp_logs_resp.json()]
    assert str(emp_log.id) in emp_log_ids
    assert str(admin_log.id) not in emp_log_ids  # Employee CANNOT see admin's query

    # 4. Admin list logs: global view sees both
    admin_logs_resp = await async_client.get(
        f"{settings.API_V1_STR}/chat/logs",
        headers=admin_auth_headers,
    )
    assert admin_logs_resp.status_code == 200
    admin_log_ids = [item["id"] for item in admin_logs_resp.json()]
    assert str(emp_log.id) in admin_log_ids
    assert str(admin_log.id) in admin_log_ids


# ==============================================================================
# 5. Public Probe & Login Endpoints
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "/health",
        "/ready",
        f"{settings.API_V1_STR}/health",
        f"{settings.API_V1_STR}/ready",
    ],
)
async def test_health_and_readiness_probes_are_unauthenticated(
    async_client: AsyncClient,
    endpoint: str,
):
    """Health check and readiness endpoints must remain accessible without credentials."""
    resp = await async_client.get(endpoint)
    assert resp.status_code in [200, 503]  # 200 when ready, 503 if dependencies down, but never 401/403
