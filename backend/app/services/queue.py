from __future__ import annotations

from fastapi import BackgroundTasks
from redis.asyncio import Redis

from app.core.config import Settings
from app.services.pipeline import InspectionPipeline


class InlineQueue:
    async def enqueue(self, job_id: str, background_tasks: BackgroundTasks, pipeline: InspectionPipeline) -> None:
        background_tasks.add_task(pipeline.process_job, job_id)


class RedisQueue:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def enqueue(self, job_id: str, background_tasks: BackgroundTasks, pipeline: InspectionPipeline) -> None:
        await self.redis.lpush(self.settings.redis_queue_name, job_id)


def build_queue(settings: Settings) -> InlineQueue | RedisQueue:
    if settings.queue_backend == "redis":
        return RedisQueue(settings)
    return InlineQueue()

