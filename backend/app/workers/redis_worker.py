from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.services.notifications import NotificationService
from app.services.openai_json import JSONLLMClient
from app.services.pipeline import InspectionPipeline


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    await create_schema(engine)

    pipeline = InspectionPipeline(
        settings=settings,
        session_factory=session_factory,
        llm=JSONLLMClient(settings),
        notifications=NotificationService(),
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    try:
        while True:
            _, job_id = await redis.brpop(settings.redis_queue_name)
            await pipeline.process_job(job_id)
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

