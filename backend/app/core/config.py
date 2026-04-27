from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = "AIShippingInspectAgent"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/inspection"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "inspection:jobs"
    queue_backend: str = Field(default="inline", pattern="^(inline|redis)$")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    storage_dir: Path = Path("storage/uploads")
    allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
