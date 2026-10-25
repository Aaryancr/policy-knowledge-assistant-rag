"""Command-line interface commands for database management and user provisioning."""

import argparse
import getpass
import sys
from sqlalchemy import select

from app.config import get_settings
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.database import SyncSessionLocal
from app.models.user import User

settings = get_settings()


def create_initial_admin(
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> None:
    """Creates or updates the initial administrator user safely without exposing production secrets in shell logs."""
    admin_email = email or settings.INITIAL_ADMIN_EMAIL
    admin_full_name = full_name or settings.INITIAL_ADMIN_FULL_NAME
    admin_password = password or settings.INITIAL_ADMIN_PASSWORD

    if not admin_email:
        admin_email = input("Enter admin email address: ").strip()

    if not admin_password:
        admin_password = getpass.getpass("Enter admin password: ").strip()
        confirm_password = getpass.getpass("Confirm admin password: ").strip()
        if admin_password != confirm_password:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(admin_password) < 8:
        print("Error: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    with SyncSessionLocal() as session:
        existing_user = session.execute(
            select(User).where(User.email == admin_email)
        ).scalar_one_or_none()

        if existing_user:
            print(f"User with email '{admin_email}' already exists. Updating role to 'admin' and refreshing password...")
            existing_user.hashed_password = hash_password(admin_password)
            existing_user.role = "admin"
            existing_user.is_active = True
            existing_user.full_name = admin_full_name
            session.commit()
            print(f"Admin '{admin_email}' successfully updated.")
            return

        new_admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            full_name=admin_full_name,
            role="admin",
            is_active=True,
        )
        session.add(new_admin)
        session.commit()
        print(f"Admin user '{admin_email}' created successfully.")


def create_user(
    email: str,
    password: str,
    full_name: str | None = None,
    role: str = "employee",
) -> None:
    """Creates or updates a user with a specific role ('admin' or 'employee')."""
    if role not in ("admin", "employee"):
        print(f"Error: Invalid role '{role}'. Must be 'admin' or 'employee'.", file=sys.stderr)
        sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    with SyncSessionLocal() as session:
        existing_user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_user:
            print(f"User with email '{email}' already exists. Updating role to '{role}' and refreshing password...")
            existing_user.hashed_password = hash_password(password)
            existing_user.role = role
            existing_user.is_active = True
            if full_name:
                existing_user.full_name = full_name
            session.commit()
            print(f"User '{email}' ({role}) successfully updated.")
            return

        new_user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name or email.split("@")[0].title(),
            role=role,
            is_active=True,
        )
        session.add(new_user)
        session.commit()
        print(f"User '{email}' ({role}) created successfully.")


def main() -> None:
    setup_logging(level="INFO")
    parser = argparse.ArgumentParser(description="Policy & Knowledge Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-admin subcommand
    admin_parser = subparsers.add_parser(
        "create-admin",
        help="Seed or update the initial administrator account",
    )
    admin_parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Admin email address (defaults to INITIAL_ADMIN_EMAIL env var)",
    )
    admin_parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Admin password (defaults to INITIAL_ADMIN_PASSWORD env var or prompt)",
    )
    admin_parser.add_argument(
        "--full-name",
        type=str,
        default=None,
        help="Admin full name (defaults to INITIAL_ADMIN_FULL_NAME env var)",
    )

    # create-user subcommand
    user_parser = subparsers.add_parser(
        "create-user",
        help="Seed or update an employee or admin account",
    )
    user_parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="User email address",
    )
    user_parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="User password (min 8 characters)",
    )
    user_parser.add_argument(
        "--role",
        type=str,
        default="employee",
        choices=["admin", "employee"],
        help="User role (admin or employee, default: employee)",
    )
    user_parser.add_argument(
        "--full-name",
        type=str,
        default=None,
        help="User full name",
    )

    args = parser.parse_args()
    if args.command == "create-admin":
        create_initial_admin(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
        )
    elif args.command == "create-user":
        create_user(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            role=args.role,
        )


if __name__ == "__main__":
    main()
