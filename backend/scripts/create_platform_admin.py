"""Bootstrap the first (or an additional) platform superadmin account.

There's no self-registration endpoint for superadmins — run this from an
environment with direct database access:

    python scripts/create_platform_admin.py --email admin@platform.example

Prompts for a password (use --password only for scripted/CI use, since it
leaks into shell history and the process list).
"""

import argparse
import asyncio
import getpass

from src.core.security import hash_password
from src.domain.entities.platform_admin import PlatformAdmin
from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.value_objects.email import Email
from src.infrastructure.db.repositories.sqlalchemy_platform_admin_repository import (
    SqlAlchemyPlatformAdminRepository,
)
from src.infrastructure.db.session import async_session_factory


async def create_platform_admin(email: str, password: str) -> None:
    async with async_session_factory() as session:
        repo = SqlAlchemyPlatformAdminRepository(session)
        if await repo.get_by_email(email) is not None:
            raise EntityAlreadyExistsError("PlatformAdmin", email)

        admin = await repo.add(
            PlatformAdmin(email=Email(email), hashed_password=hash_password(password))
        )
        await session.commit()
        print(f"Created platform admin {admin.email} ({admin.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", default=None, help="Omit to be prompted securely.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    asyncio.run(create_platform_admin(args.email, password))
