from __future__ import annotations
from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE, format_schema_for_prompt, FEW_SHOT_EXAMPLES


def build_system_content(template: str, schema_json: str, synonym_text: str) -> str:
    """将 Schema / 同义词注入智能体 Prompt 模板。"""
    synonym_block = synonym_text.strip() or "（无）"
    if "{schema_json}" in template and "{synonym_text}" in template:
        return template.format(schema_json=schema_json, synonym_text=synonym_block)
    return (
        f"{template.rstrip()}\n\n"
        f"## 当前数据库 Schema\n\n{schema_json}\n\n"
        f"## 字段术语映射\n\n{synonym_block}"
    )


class PromptBuilder:
    """NL2SQL Prompt 构建器"""

    def build(
        self,
        user_query: str,
        schema: list[dict] | None = None,
        synonym_text: str = "",
        conversation_history: list[dict] | None = None,
        system_prompt_template: str | None = None,
    ) -> list[dict]:
        """
        构建发送给 LLM 的 messages 列表。

        Args:
            user_query: 用户自然语言问题
            schema: 数据库 Schema 列表
            synonym_text: 业务同义词文本
            conversation_history: 多轮对话历史
            system_prompt_template: 智能体 NL2SQL 系统模板（含占位符或纯文本）

        Returns:
            list[dict]: OpenAI/DeepSeek 兼容的 messages 列表
        """
        schema_json = format_schema_for_prompt(schema or [])
        template = (system_prompt_template or "").strip() or SYSTEM_PROMPT_TEMPLATE
        system_content = build_system_content(template, schema_json, synonym_text)

        messages = [{"role": "system", "content": system_content}]

        if FEW_SHOT_EXAMPLES:
            for example in FEW_SHOT_EXAMPLES:
                messages.append({"role": "user", "content": example["query"]})
                messages.append({"role": "assistant", "content": example["sql"]})

        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_query})

        return messages
