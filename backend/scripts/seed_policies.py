from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.models.domain import Policy


POLICY_FILE = Path(__file__).resolve().parents[1] / "samples" / "policies.json"


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    await create_schema(engine)
    policy_rows = json.loads(POLICY_FILE.read_text())
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        session.add_all([Policy(**row) for row in policy_rows])
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
