from __future__ import annotations

from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.init_db import create_schema
from app.main import create_app
from app.models.domain import Policy


@pytest_asyncio.fixture
async def client(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'inspection.sqlite'}",
        storage_dir=tmp_path / "uploads",
        queue_backend="inline",
        openai_api_key=None,
        allowed_origins="http://testserver",
    )
    app = create_app(settings)
    await create_schema(app.state.engine)

    async with app.state.session_factory() as session:
        session.add_all(
            [
                Policy(
                    name="Commercial Freight Invoice Evidence",
                    category="Commercial",
                    region="US",
                    description="Commercial shipments require invoice number, freight description, cargo value, carrier name, and vehicle identifier.",
                ),
                Policy(
                    name="General Shipping Identity Check",
                    category="General",
                    region="US",
                    description="All inspections require supplier name, invoice copy, vehicle identification, and shipment date.",
                ),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    await app.state.engine.dispose()
