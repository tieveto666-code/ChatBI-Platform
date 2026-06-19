from __future__ import annotations
import inspect
from typing import AsyncGenerator

from config import settings
from llm.base import LLMResponse
from llm.factory import LLMProviderFactory


class LLMService:
    """LLM 服务 — 封装 LLMProvider，管理 Provider 实例"""

    def __init__(self, provider_name: str | None = None):
        self._provider = None
        self.provider_name = provider_name

    @property
    def provider(self):
        if self._provider is None:
            self._provider = LLMProviderFactory.create(self.provider_name)
        return self._provider

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM，逐 token 产出"""
        result = await self.provider.chat(
            messages=messages,
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            stream=True,
        )
        if inspect.isasyncgen(result):
            async for token in result:
                yield token
        else:
            yield result.text

    async def chat_once(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """非流式调用 LLM，返回完整文本"""
        result = await self.provider.chat(
            messages=messages,
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            stream=False,
        )
        if isinstance(result, LLMResponse):
            return result.text
        return str(result)

    async def health_check(self) -> bool:
        return await self.provider.health_check()

    def refresh_provider(self, provider_name: str | None = None):
        """刷新 Provider 实例（配置变更后调用）"""
        self._provider = LLMProviderFactory.create(provider_name)
