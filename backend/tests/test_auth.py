from datetime import datetime, timedelta, timezone
import uuid
import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core import security
from app.models.user import User

settings = get_settings()


def test_password_hashing_and_verification():
    raw_pass = "SecureSecret!456"
    hashed = security.hash_password(raw_pass)
    assert hashed != raw_pass
    assert security.verify_password(raw_pass, hashed) is True
    assert security.verify_password("WrongPassword!", hashed) is False


def test_jwt_creation_and_decoding():
    token = security.create_access_token(
        subject="user-123",
        role="employee",
        expires_delta=timedelta(minutes=15),
    )
    payload = security.decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "employee"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, employee_user: User):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "EmployeePass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "employee"
    assert data["email"] == "employee@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, employee_user: User):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_profile(
    async_client: AsyncClient,
    employee_token: str,
    employee_user: User,
):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(employee_user.id)
    assert data["email"] == employee_user.email
    assert data["role"] == "employee"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(async_client: AsyncClient):
    # No auth header
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401

    # Malformed token
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_role_authorization(
    async_client: AsyncClient,
    admin_token: str,
    employee_token: str,
):
    # Admin access granted
    admin_resp = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == 200
    assert "access granted" in admin_resp.json()["message"]

    # Employee access denied with 403 Forbidden
    emp_resp = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert emp_resp.status_code == 403
    assert "Forbidden" in emp_resp.json()["detail"]


@pytest.mark.asyncio
async def test_expired_jwt_rejected(async_client: AsyncClient, employee_user: User):
    """Expired JWTs must be rejected with 401 Unauthorized."""
    token = security.create_access_token(
        subject=str(employee_user.id),
        role=employee_user.role,
        expires_delta=timedelta(seconds=-10),
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_incorrectly_signed_jwt_rejected(async_client: AsyncClient, employee_user: User):
    """Tokens signed with a different/unauthorized secret key must be rejected with 401 Unauthorized."""
    now = datetime.now(timezone.utc)
    tampered_token = jwt.encode(
        {"sub": str(employee_user.id), "role": employee_user.role, "exp": now + timedelta(hours=1)},
        "wrong-secret-key-that-does-not-match-configured-secret",
        algorithm="HS256",
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_missing_subject_rejected(async_client: AsyncClient):
    """Tokens missing the subject ('sub') claim must be rejected with 401 Unauthorized."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"role": "employee", "exp": now + timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "missing subject claim" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_malformed_subject_uuid_rejected(async_client: AsyncClient):
    """Tokens with malformed non-UUID subject claims must be rejected with 401 Unauthorized."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "not-a-valid-uuid", "role": "employee", "exp": now + timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_integer_subject_rejected(async_client: AsyncClient):
    """Tokens with non-string integer subject claims must be rejected with 401 Unauthorized."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": 12345, "role": "employee", "exp": now + timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_nonexistent_user_rejected(async_client: AsyncClient):
    """Tokens with a valid UUID that does not exist in the database must be rejected with 401."""
    random_id = str(uuid.uuid4())
    token = security.create_access_token(
        subject=random_id,
        role="employee",
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "User associated with token not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_inactive_user_token_rejected(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Inactive accounts with valid JWTs must be denied with 403 Forbidden."""
    inactive_user = User(
        email="inactive@example.com",
        hashed_password=security.hash_password("InactivePass123!"),
        full_name="Inactive User",
        role="employee",
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.commit()
    await db_session.refresh(inactive_user)

    token = security.create_access_token(
        subject=str(inactive_user.id),
        role=inactive_user.role,
    )
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "User account is inactive" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_role_tampering_in_jwt_claims_blocked_by_database_role(
    async_client: AsyncClient,
    employee_user: User,
):
    """Forging role='admin' in a valid JWT payload for an employee user is blocked because
    authorization checks the database record's role, not client token claims.
    """
    forged_token = security.create_access_token(
        subject=str(employee_user.id),
        role="admin",  # Tampered claim
    )
    resp = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]
