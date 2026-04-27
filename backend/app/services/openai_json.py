from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings


class AgentError(RuntimeError):
    pass


class JSONLLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def complete_json(
        self,
        *,
        name: str,
        schema: dict[str, Any],
        system: str,
        user: str,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        if self._client is None:
            return fallback

        try:
            response = await self._client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": name,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            raise AgentError(f"OpenAI structured output failed for {name}: {exc}") from exc

