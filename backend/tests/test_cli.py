"""Tests for CLI initial administrator provisioning."""

from unittest.mock import patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cli import create_initial_admin
from app.core import security
from app.database import Base
from app.models.user import User

# In-memory sync engine for CLI unit test
test_sync_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSyncSessionLocal = sessionmaker(
    bind=test_sync_engine,
    autocommit=False,
    autoflush=False,
)


def test_create_initial_admin_script():
    # Setup tables in memory
    Base.metadata.create_all(test_sync_engine)

    test_email = "cli_admin@example.com"
    test_password = "SecurePassword123!"
    test_name = "CLI Admin"

    # Patch SyncSessionLocal in app.cli
    with patch("app.cli.SyncSessionLocal", TestSyncSessionLocal):
        create_initial_admin(
            email=test_email,
            password=test_password,
            full_name=test_name,
        )

        with TestSyncSessionLocal() as session:
            user = session.execute(
                select(User).where(User.email == test_email)
            ).scalar_one_or_none()

            assert user is not None
            assert user.email == test_email
            assert user.role == "admin"
            assert user.full_name == test_name
            assert user.is_active is True
            assert security.verify_password(test_password, user.hashed_password) is True

    Base.metadata.drop_all(test_sync_engine)


def test_create_user_script():
    Base.metadata.create_all(test_sync_engine)

    test_email = "employee_cli@example.com"
    test_password = "EmployeePass123!"
    test_name = "CLI Employee"

    with patch("app.cli.SyncSessionLocal", TestSyncSessionLocal):
        from app.cli import create_user

        create_user(
            email=test_email,
            password=test_password,
            full_name=test_name,
            role="employee",
        )

        with TestSyncSessionLocal() as session:
            user = session.execute(
                select(User).where(User.email == test_email)
            ).scalar_one_or_none()

            assert user is not None
            assert user.email == test_email
            assert user.role == "employee"
            assert user.full_name == test_name
            assert user.is_active is True
            assert security.verify_password(test_password, user.hashed_password) is True

    Base.metadata.drop_all(test_sync_engine)
