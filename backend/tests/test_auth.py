"""Tests for authentication, JWT lifecycle, password hashing and role-based access control."""

from datetime import timedelta
import pytest
from httpx import AsyncClient

from app.core import security
from app.models.user import User


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
