from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator

from llm.base import BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM Provider — 开发/测试用。
    基于 Q&A 映射表返回固定 SQL，支持故障注入。
    """

    # 默认 Q&A 映射表
    QA_MAP: dict[str, str] = {
        "查询所有用户": "SELECT * FROM users",
        "统计用户数量": "SELECT COUNT(*) as user_count FROM users",
        "查询最近10条对话": "SELECT * FROM conversations ORDER BY created_at DESC LIMIT 10",
        "统计每日活跃用户": "SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as active_users FROM conversations GROUP BY day ORDER BY day",
        "查询用户角色分布": "SELECT r.name as role_name, COUNT(u.id) as user_count FROM users u JOIN roles r ON u.role_id = r.id GROUP BY r.name",
        "查询销售额最高的前5个商品": "SELECT product_name, sales FROM sales_data ORDER BY sales DESC LIMIT 5",
    }

    def __init__(
        self,
        fault_mode: str = "none",
        fault_delay: int = 0,
    ):
        self.fault_mode = fault_mode
        self.fault_delay = fault_delay

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        # 故障注入：超时
        if self.fault_mode == "timeout":
            await asyncio.sleep(9999)

        # 获取用户问题（最后一条 user 消息）
        user_query = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_query = msg["content"]
                break

        system_prompt = messages[0].get("content", "") if messages else ""

        # 故障注入：延迟
        if self.fault_delay > 0:
            await asyncio.sleep(self.fault_delay)

        if "意图识别器" in system_prompt:
            text = self._mock_intent(user_query)
            if stream:
                return self._stream_response(text)
            return LLMResponse(text=text, tokens=len(text), model="mock", finish_reason="stop")

        if "通用 AI 助手" in system_prompt:
            text = "你好，我是 ChatBI 助手。你可以问我一般问题，也可以选择数据源后进行数据查询和分析。"
            if stream:
                return self._stream_response(text)
            return LLMResponse(text=text, tokens=len(text), model="mock", finish_reason="stop")

        # 故障注入：语法错误 SQL
        if self.fault_mode == "syntax_error":
            sql = "SELECTT * FROMO userss WHERE id = 1"
        # 故障注入：非 SQL 输出
        elif self.fault_mode == "non_sql":
            sql = "抱歉，我无法理解您的问题，请重新描述。"
        else:
            # 精确匹配或模糊匹配
            sql = self.QA_MAP.get(user_query)
            if sql is None:
                # 模糊匹配
                matched = False
                for q, a in self.QA_MAP.items():
                    if any(word in user_query for word in q.split()):
                        sql = a
                        matched = True
                        break
                if not matched:
                    sql = f"-- 无法识别的查询，返回模拟结果\nSELECT 1 AS result"

        if stream:
            return self._stream_response(sql)
        else:
            return LLMResponse(
                text=sql,
                tokens=len(sql),
                model="mock",
                finish_reason="stop",
            )

    async def _stream_response(self, text: str) -> AsyncGenerator[str, None]:
        """逐字符模拟流式输出"""
        for char in text:
            yield char
            await asyncio.sleep(0.01)  # 模拟延迟

    def _mock_intent(self, user_query: str) -> str:
        data_keywords = {
            "数据", "数据源", "查询", "统计", "分析", "趋势", "分布", "排名", "报表",
            "表", "字段", "订单", "销售", "金额", "收入", "用户", "客户", "商品",
            "多少", "总数", "数量", "平均", "最大", "最小", "同比", "环比", "占比",
        }
        intent = "ask_data" if any(keyword in user_query for keyword in data_keywords) else "other"
        return json.dumps({"intent": intent}, ensure_ascii=False)

    async def health_check(self) -> bool:
        return True
