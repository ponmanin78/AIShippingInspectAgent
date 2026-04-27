from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.services.notifications import NotificationService
from app.services.openai_json import JSONLLMClient
from app.services.pipeline import InspectionPipeline
from app.services.queue import build_queue


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    engine = build_engine(resolved_settings)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await create_schema(engine)
        yield
        await engine.dispose()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.pipeline = InspectionPipeline(
        settings=resolved_settings,
        session_factory=session_factory,
        llm=JSONLLMClient(resolved_settings),
        notifications=NotificationService(),
    )
    app.state.queue = build_queue(resolved_settings)

    app.include_router(router)
    return app


app = create_app()
