from __future__ import annotations

from prompts.intent_v1 import INTENT_SYSTEM_PROMPT
from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE

DIRECT_REPLY_SYSTEM_PROMPT = (
    "你是 ChatBI 平台中的通用 AI 助手。请根据对话历史和用户最新问题直接回答。"
    "如果用户询问需要查询数据源才能确认的指标或明细，请提示用户选择数据源后提问。"
)

SUMMARY_SYSTEM_PROMPT = "你是一个数据分析助手，请用简洁的语言总结查询结果。"

SUMMARY_USER_PROMPT_TEMPLATE = """用户问题是：{user_query}

查询 SQL：{sql}

查询结果（共 {row_count} 行）：
列：{columns}
前 5 行数据：{sample_rows}

请用自然语言简要总结查询结果，突出关键发现。"""

SQL_FIX_USER_PROMPT_TEMPLATE = "生成的 SQL 有误: {error_msg}，请修正后重新输出纯 SQL 语句"

LLM_NODE_IDS = ("intent", "nl2sql", "sql_fix", "summary", "direct_reply")

WORKFLOW_STEP_META = [
    {
        "id": "intent",
        "kind": "llm",
        "title": "意图识别",
        "description": "判断用户问题是问数 (ask_data) 还是其他闲聊 (other)",
        "path": "main",
    },
    {
        "id": "direct_reply",
        "kind": "llm",
        "title": "通用回复",
        "description": "other 分支：不查数据源，直接生成对话回复",
        "path": "other",
    },
    {
        "id": "schema_load",
        "kind": "system",
        "title": "加载 Schema / 字段术语",
        "description": "从智能体目标数据源同步全量表结构，并注入表级字段术语",
        "path": "ask_data",
    },
    {
        "id": "nl2sql",
        "kind": "llm",
        "title": "NL2SQL 生成",
        "description": "根据 Schema 与同义词将自然语言转为 SQL",
        "path": "ask_data",
    },
    {
        "id": "sql_validate",
        "kind": "system",
        "title": "SQL 安全校验",
        "description": "规则校验 SELECT 语句安全性",
        "path": "ask_data",
    },
    {
        "id": "sql_fix",
        "kind": "llm",
        "title": "SQL 修正",
        "description": "校验失败时回传模型修正 SQL",
        "path": "ask_data",
    },
    {
        "id": "sql_execute",
        "kind": "system",
        "title": "SQL 执行",
        "description": "在绑定的 SQLite 数据源上执行查询",
        "path": "ask_data",
    },
    {
        "id": "summary",
        "kind": "llm",
        "title": "结果总结",
        "description": "将查询结果转为自然语言说明（流式输出）",
        "path": "ask_data",
    },
    {
        "id": "chart",
        "kind": "system",
        "title": "图表生成",
        "description": "根据结果列类型自动推荐图表",
        "path": "ask_data",
    },
]

NODE_FIELD_META: dict[str, dict] = {
    "intent": {
        "system_prompt": {"label": "系统提示词", "placeholder": "意图识别系统 Prompt"},
        "fields": ["system_prompt", "model"],
    },
    "nl2sql": {
        "system_prompt": {
            "label": "系统提示词",
            "hint": "须包含 {schema_json} 与 {synonym_text} 占位符",
        },
        "fields": ["system_prompt", "model"],
    },
    "sql_fix": {
        "user_prompt_template": {
            "label": "修正提示词模板",
            "hint": "占位符：{error_msg}",
        },
        "fields": ["user_prompt_template", "model"],
    },
    "summary": {
        "system_prompt": {"label": "系统提示词"},
        "user_prompt_template": {
            "label": "用户提示词模板",
            "hint": "占位符：{user_query} {sql} {row_count} {columns} {sample_rows}",
        },
        "fields": ["system_prompt", "user_prompt_template", "model"],
    },
    "direct_reply": {
        "system_prompt": {"label": "系统提示词"},
        "fields": ["system_prompt", "model"],
    },
}


def default_node_config(node_id: str, nl2sql_override: str | None = None) -> dict:
    """返回单个 LLM 节点的默认配置（模型字段为 null 表示继承智能体全局默认）。"""
    base = {
        "model_provider": None,
        "model_name": None,
        "temperature": None,
        "max_tokens": None,
    }
    if node_id == "intent":
        return {**base, "system_prompt": INTENT_SYSTEM_PROMPT, "max_tokens": 64}
    if node_id == "nl2sql":
        return {
            **base,
            "system_prompt": nl2sql_override or SYSTEM_PROMPT_TEMPLATE,
        }
    if node_id == "sql_fix":
        return {**base, "user_prompt_template": SQL_FIX_USER_PROMPT_TEMPLATE, "max_tokens": 2048}
    if node_id == "summary":
        return {
            **base,
            "system_prompt": SUMMARY_SYSTEM_PROMPT,
            "user_prompt_template": SUMMARY_USER_PROMPT_TEMPLATE,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
    if node_id == "direct_reply":
        return {
            **base,
            "system_prompt": DIRECT_REPLY_SYSTEM_PROMPT,
            "temperature": 0.3,
            "max_tokens": 2048,
        }
    raise ValueError(f"unknown node: {node_id}")


def default_workflow_config(nl2sql_override: str | None = None) -> dict:
    return {node_id: default_node_config(node_id, nl2sql_override) for node_id in LLM_NODE_IDS}
