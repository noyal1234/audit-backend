from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import Base

SchemaType = TypeVar("SchemaType", bound=Base)


class BasePostgresRepository(Generic[SchemaType]):
    """Base repository with async session and generic schema type."""

    def __init__(self, session_factory: Any, schema_class: type[SchemaType]) -> None:
        self._session_factory = session_factory
        self._schema_class = schema_class

    async def _get_by_id_raw(self, id: str) -> SchemaType | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(self._schema_class).where(self._schema_class.id == id)
            )
            return result.scalar_one_or_none()
