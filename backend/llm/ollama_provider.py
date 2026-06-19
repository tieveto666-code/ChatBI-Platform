from __future__ import annotations
import json
from typing import AsyncGenerator

import httpx

from config import settings
from llm.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """Ollama API Provider"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        # Ollama 的 /api/chat 接口使用 OpenAI 兼容的消息格式
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "num_predict": max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
            },
            "stream": stream,
        }

        if stream:
            return self._stream_chat(payload)

        return await self._non_stream_chat(payload)

    async def _non_stream_chat(self, payload: dict) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(
                text=data["message"]["content"],
                tokens=data.get("eval_count", 0),
                model=data.get("model", self.model),
                finish_reason=data.get("done_reason", ""),
            )

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            break
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                )
                return response.status_code == 200
        except Exception:
            return False
