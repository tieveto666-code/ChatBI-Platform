from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class LLMResponse:
    """LLM 调用返回结果"""
    text: str = ""
    tokens: int = 0
    model: str = ""
    finish_reason: str = ""


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """
        调用 LLM。
        当 stream=True 时返回 AsyncGenerator[str, None]（逐 token 产出字符串）。
        当 stream=False 时返回 LLMResponse。
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        ...
