from __future__ import annotations
import json
from typing import AsyncGenerator

import httpx

from config import settings
from llm.base import BaseLLMProvider, LLMResponse


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider（OpenAI 兼容接口）"""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
            "stream": stream,
        }

        if stream:
            return self._stream_chat(headers, payload)

        return await self._non_stream_chat(headers, payload)

    async def _non_stream_chat(self, headers: dict, payload: dict) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            self._raise_for_status(response)
            data = response.json()
            choice = data["choices"][0]
            return LLMResponse(
                text=choice["message"]["content"],
                tokens=data["usage"]["total_tokens"] if "usage" in data else 0,
                model=data["model"],
                finish_reason=choice.get("finish_reason", ""),
            )

    async def _stream_chat(self, headers: dict, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_base}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise RuntimeError("DeepSeek 认证失败：请检查 DEEPSEEK_API_KEY 是否有效")
        if response.status_code == 402:
            raise RuntimeError("DeepSeek 账户余额不足或计费不可用")
        response.raise_for_status()
