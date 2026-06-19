from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse
from schemas.chat import ChatStreamEvent


class SSEStreamer:
    """
    SSE（Server-Sent Events）流式响应管理器。
    支持六种事件类型：token / sql / chart / table / error / done
    """

    def __init__(self):
        self._queue: asyncio.Queue[ChatStreamEvent] = asyncio.Queue()
        self._events: list[ChatStreamEvent] = []

    async def send(self, event: ChatStreamEvent):
        """添加一个事件到流中"""
        self._events.append(event)
        await self._queue.put(event)

    async def _generate(self) -> AsyncGenerator[str, None]:
        """生成 SSE 格式的文本流"""
        while True:
            event = await self._queue.get()
            data = json.dumps(event.data, ensure_ascii=False)
            yield f"event: {event.event}\ndata: {data}\n\n"
            if event.event == "done" or event.event == "error":
                break

    def to_response(self) -> StreamingResponse:
        """转换为 FastAPI StreamingResponse"""
        return StreamingResponse(
            self._generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
