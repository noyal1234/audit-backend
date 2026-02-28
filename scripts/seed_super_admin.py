"""Seed a SUPER_ADMIN user into the database.

Usage:
    python -m scripts.seed_super_admin

Reads database connection from .env (APP_POSTGRES_*).
Creates the user only if no SUPER_ADMIN exists yet.
"""

import asyncio
import sys
from uuid import uuid4

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.configs.settings import get_instance
from src.database.postgres.schema.user_schema import UserSchema

SUPER_ADMIN_EMAIL = "admin@test.com"
SUPER_ADMIN_PASSWORD = "admin@123"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def seed() -> None:
    settings = get_instance()
    url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        async with AsyncSession(bind=conn) as session:
            result = await session.execute(
                select(UserSchema).where(UserSchema.role_type == "SUPER_ADMIN")
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"[INFO] SUPER_ADMIN already exists: {existing.email} (id={existing.id})")
                await engine.dispose()
                return

            user_id = str(uuid4())
            user = UserSchema(
                id=user_id,
                email=SUPER_ADMIN_EMAIL,
                password_hash=hash_password(SUPER_ADMIN_PASSWORD),
                role_type="SUPER_ADMIN",
                facility_id=None,
                country_id=None,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print(f"[OK] SUPER_ADMIN created:")
            print(f"     Email:    {SUPER_ADMIN_EMAIL}")
            print(f"     Password: {SUPER_ADMIN_PASSWORD}")
            print(f"     ID:       {user_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
