import asyncio
from logging.config import fileConfig
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.database.base import Base
from src.database.postgres.schema.auth_session_schema import AuthSessionSchema  # noqa: F401
from src.database.postgres.schema.audit_schema import AuditCheckpointResultSchema, AuditSchema  # noqa: F401
from src.database.postgres.schema.category_schema import CategorySchema, SubcategorySchema  # noqa: F401
from src.database.postgres.schema.checkpoint_schema import CheckpointSchema  # noqa: F401
from src.database.postgres.schema.country_schema import CountrySchema  # noqa: F401
from src.database.postgres.schema.facility_schema import FacilitySchema  # noqa: F401
from src.database.postgres.schema.media_schema import MediaEvidenceSchema  # noqa: F401
from src.database.postgres.schema.shift_schema import ShiftConfigSchema  # noqa: F401
from src.database.postgres.schema.staff_schema import StaffSchema  # noqa: F401
from src.database.postgres.schema.user_schema import UserSchema  # noqa: F401
from src.database.postgres.schema.zone_schema import ZoneSchema  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def get_url() -> str:
    from src.configs.settings import get_instance
    s = get_instance()
    user = quote_plus(s.postgres_user)
    password = quote_plus(s.postgres_password)
    return (
        f"postgresql+asyncpg://{user}:{password}"
        f"@{s.postgres_host}:{s.postgres_port}/{s.postgres_db}"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL only)."""
    url = get_url().replace("+asyncpg", "")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
