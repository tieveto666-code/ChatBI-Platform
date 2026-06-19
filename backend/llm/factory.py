from __future__ import annotations
from config import settings
from core.exceptions import SystemError
from core.error_codes import ErrorCode
from llm.base import BaseLLMProvider
from llm.deepseek_provider import DeepSeekProvider
from llm.mock_provider import MockLLMProvider


class LLMProviderFactory:
    """LLM Provider 工厂 — 生产环境使用 DeepSeek；mock 仅供测试。"""

    _providers: dict[str, BaseLLMProvider] = {}

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseLLMProvider:
        name = provider_name or settings.LLM_PROVIDER

        if name in cls._providers:
            return cls._providers[name]

        if name == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                raise SystemError(
                    code=ErrorCode.LLM_PROVIDER_NOT_FOUND,
                    message="DeepSeek API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY",
                )
            provider = DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                api_base=settings.DEEPSEEK_API_BASE,
                model=settings.DEEPSEEK_MODEL,
            )
        elif name == "mock":
            provider = MockLLMProvider(
                fault_mode=settings.MOCK_LLM_FAULT_MODE,
                fault_delay=settings.MOCK_LLM_FAULT_DELAY,
            )
        else:
            raise SystemError(
                code=ErrorCode.LLM_PROVIDER_NOT_FOUND,
                message=f"不支持的 LLM Provider: {name}",
            )

        cls._providers[name] = provider
        return provider
