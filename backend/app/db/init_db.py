from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.domain import Base


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

