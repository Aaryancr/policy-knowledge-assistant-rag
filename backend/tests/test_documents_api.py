"""Integration tests for document upload, listing, details, chunk queries, and deletion."""

import os
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.services.queue import QueueError
from tests.helpers import create_test_docx, create_test_pdf, create_test_txt


@pytest.mark.asyncio
async def test_admin_upload_pdf_success(
    async_client: AsyncClient,
    admin_token: str,
    tmp_path,
):
    pdf_path = create_test_pdf(str(tmp_path), text_pages=["Test policy page 1", "Test policy page 2"])
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock) as mock_enqueue:
        response = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_policy.pdf", file_bytes, "application/pdf")},
            data={"title": "Official Test Policy"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Official Test Policy"
    assert data["status"] == "queued"
    assert data["job_id"] is not None
    assert data["is_duplicate"] is False
    assert mock_enqueue.called


@pytest.mark.asyncio
async def test_admin_upload_docx_and_txt_success(
    async_client: AsyncClient,
    admin_token: str,
    tmp_path,
):
    # 1. DOCX upload
    docx_path = create_test_docx(str(tmp_path))
    with open(docx_path, "rb") as f:
        docx_bytes = f.read()

    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        resp_docx = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("handbook.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert resp_docx.status_code == 201

    # 2. TXT upload
    txt_path = create_test_txt(str(tmp_path), content="Line 1\n\nLine 2")
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()

    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        resp_txt = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("rules.txt", txt_bytes, "text/plain")},
        )
    assert resp_txt.status_code == 201


@pytest.mark.asyncio
async def test_employee_upload_denied_with_403(
    async_client: AsyncClient,
    employee_token: str,
    tmp_path,
):
    txt_path = create_test_txt(str(tmp_path))
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()

    response = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {employee_token}"},
        files={"file": ("rules.txt", txt_bytes, "text/plain")},
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unauthenticated_upload_denied_with_401(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.txt", b"sample content", "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_unsupported_file_format(
    async_client: AsyncClient,
    admin_token: str,
):
    response = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("malware.exe", b"\x4D\x5A\x90", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(
    async_client: AsyncClient,
    admin_token: str,
):
    response = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "File is empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_spoofed_pdf_magic_bytes_rejected(
    async_client: AsyncClient,
    admin_token: str,
):
    # File named .pdf but containing arbitrary plaintext without %PDF- magic bytes
    response = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("fake.pdf", b"This is not a real PDF file", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Missing %PDF- magic signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(
    async_client: AsyncClient,
    admin_token: str,
):
    with patch("app.api.routes.documents.settings.MAX_UPLOAD_SIZE_BYTES", 50):
        # 100 bytes is greater than 50 bytes limit
        oversized = b"A" * 100
        response = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("large.txt", oversized, "text/plain")},
        )
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_duplicate_checksum_handling(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    tmp_path,
):
    pdf_path = create_test_pdf(str(tmp_path), text_pages=["Unique duplicate test content"])
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    # 1. Initial upload
    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        first_resp = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("first.pdf", file_bytes, "application/pdf")},
        )
    assert first_resp.status_code == 201
    first_data = first_resp.json()
    assert first_data["is_duplicate"] is False

    # Mark document as completed in DB
    doc_uuid = uuid.UUID(first_data["document_id"])
    doc = (await db_session.execute(select(Document).where(Document.id == doc_uuid))).scalar_one()
    doc.status = "completed"
    await db_session.commit()

    # 2. Upload identical content again
    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock) as mock_enqueue:
        second_resp = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("second.pdf", file_bytes, "application/pdf")},
        )
    assert second_resp.status_code == 201
    second_data = second_resp.json()
    # Verified deduplication response
    assert second_data["is_duplicate"] is True
    assert second_data["document_id"] == first_data["document_id"]
    # Re-enqueuing avoided for already completed identical document
    assert not mock_enqueue.called


@pytest.mark.asyncio
async def test_upload_redis_enqueue_failure_recovery(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    tmp_path,
):
    txt_path = create_test_txt(str(tmp_path), content="Content for Redis error test")
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()

    # Simulate Redis connection failure during enqueue
    with patch(
        "app.api.routes.documents.enqueue_ingestion_job",
        side_effect=QueueError("Connection refused by Redis server"),
    ):
        response = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("error.txt", txt_bytes, "text/plain")},
        )

    assert response.status_code == 503
    assert "Ingestion queue is currently unavailable" in response.json()["detail"]

    # Verify that the DB records were safely marked as 'failed', NOT left as misleading 'queued'
    docs = (await db_session.execute(select(Document).where(Document.filename == "error.txt"))).scalars().all()
    assert len(docs) == 1
    assert docs[0].status == "failed"

    jobs = (await db_session.execute(select(IngestionJob).where(IngestionJob.document_id == docs[0].id))).scalars().all()
    assert len(jobs) == 1
    assert jobs[0].status == "failed"
    assert "Redis enqueue failed" in jobs[0].error_message


@pytest.mark.asyncio
async def test_document_listing_details_chunks_and_deletion(
    async_client: AsyncClient,
    admin_token: str,
    employee_token: str,
    tmp_path,
):
    txt_path = create_test_txt(str(tmp_path), content="Document lifecycle test")
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()

    with patch("app.api.routes.documents.enqueue_ingestion_job", new_callable=AsyncMock):
        upload_resp = await async_client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("lifecycle.txt", txt_bytes, "text/plain")},
        )
    doc_id = upload_resp.json()["document_id"]
    job_id = upload_resp.json()["job_id"]

    # 1. Both admin and employee can list documents
    list_resp = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 2. Retrieve document details
    get_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == doc_id
    # Ensure sensitive server paths are not leaked in the API response
    assert "file_path" not in get_resp.json()

    # 3. Retrieve chunks
    chunks_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert chunks_resp.status_code == 200
    assert isinstance(chunks_resp.json(), list)

    # 4. Job status API
    job_resp = await async_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == job_id
    assert job_resp.json()["status"] == "queued"

    # 5. Non-admin cannot delete document
    delete_denied = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert delete_denied.status_code == 403

    # 6. Admin can delete document
    delete_ok = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_ok.status_code == 204

    # Confirm 404 after deletion
    get_after = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_after.status_code == 404
