from __future__ import annotations

from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Policy


class VectorStore(Protocol):
    async def search_policies(self, *, fleet_type: str, region: str, limit: int = 8) -> list[Policy]:
        ...


class SQLPolicyVectorStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_policies(self, *, fleet_type: str, region: str, limit: int = 8) -> list[Policy]:
        query = (
            select(Policy)
            .where(Policy.region == region)
            .where(or_(Policy.category == fleet_type, Policy.category == "General"))
            .order_by(Policy.category.desc(), Policy.name.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

