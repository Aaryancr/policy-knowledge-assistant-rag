"""Shared pytest fixtures: database engines, test client, and authenticated test users."""

import os
import sys
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.deps import get_db
from app.core import security
from app.database import Base
from app.main import app
from app.models.user import User

# In-memory SQLite async engine with StaticPool to keep schema in memory across sessions
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Recreates the database schema before each test run."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields an isolated async session for database interactions in tests."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yields an HTTP async test client with the database dependency overridden."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Creates a seeded admin user."""
    admin = User(
        email="admin@example.com",
        hashed_password=security.hash_password("AdminPass123!"),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def employee_user(db_session: AsyncSession) -> User:
    """Creates a seeded employee user."""
    employee = User(
        email="employee@example.com",
        hashed_password=security.hash_password("EmployeePass123!"),
        full_name="Employee User",
        role="employee",
        is_active=True,
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(employee)
    return employee


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generates a valid JWT access token for the admin user."""
    return security.create_access_token(
        subject=str(admin_user.id),
        role=admin_user.role,
        extra_claims={"email": admin_user.email},
    )


@pytest.fixture
def employee_token(employee_user: User) -> str:
    """Generates a valid JWT access token for the employee user."""
    return security.create_access_token(
        subject=str(employee_user.id),
        role=employee_user.role,
        extra_claims={"email": employee_user.email},
    )


@pytest.fixture
def admin_auth_headers(admin_token: str) -> dict[str, str]:
    """Authorization header dictionary for admin requests."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def employee_auth_headers(employee_token: str) -> dict[str, str]:
    """Authorization header dictionary for employee requests."""
    return {"Authorization": f"Bearer {employee_token}"}

