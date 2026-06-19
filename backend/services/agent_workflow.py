from __future__ import annotations

from models.agent_config import AgentConfig
from prompts.workflow_defaults import (
    LLM_NODE_IDS,
    NODE_FIELD_META,
    WORKFLOW_STEP_META,
    default_node_config,
    default_workflow_config,
)
from services.llm_service import LLMService


def _agent_temperature(agent) -> float:
    return (agent.temperature or 10) / 100


def workflow_template() -> dict:
    """供前端渲染固定工作流与字段说明。"""
    return {
        "steps": WORKFLOW_STEP_META,
        "llm_nodes": LLM_NODE_IDS,
        "node_fields": NODE_FIELD_META,
        "defaults": default_workflow_config(),
    }


def _merge_node(node_id: str, stored: dict | None, agent: AgentConfig) -> dict:
    merged = default_node_config(node_id)
    if node_id == "nl2sql" and agent.system_prompt:
        merged["system_prompt"] = agent.system_prompt
    if stored:
        for key, value in stored.items():
            if value is not None and key in merged:
                merged[key] = value
            elif value is not None:
                merged[key] = value
    return merged


def resolve_workflow_config(agent: AgentConfig) -> dict:
    """合并库中 workflow_config 与默认值，返回完整可编辑配置。"""
    stored = agent.workflow_config if isinstance(agent.workflow_config, dict) else {}
    nodes = stored.get("nodes") if isinstance(stored.get("nodes"), dict) else stored
    return {
        node_id: _merge_node(node_id, nodes.get(node_id) if isinstance(nodes, dict) else None, agent)
        for node_id in LLM_NODE_IDS
    }


class AgentWorkflowRuntime:
    """问数管线运行时：按节点解析 Prompt 与 LLM 参数。"""

    def __init__(self, agent: AgentConfig):
        self.agent = agent
        self.config = resolve_workflow_config(agent)

    def node(self, node_id: str) -> dict:
        return self.config[node_id]

    def node_llm(self, node_id: str) -> tuple[LLMService, float, int]:
        cfg = self.node(node_id)
        provider = cfg.get("model_provider") or self.agent.model_provider
        temperature = cfg.get("temperature")
        if temperature is None:
            temperature = _agent_temperature(self.agent)
        else:
            temperature = float(temperature)
        max_tokens = cfg.get("max_tokens") or self.agent.max_tokens or 4096
        return LLMService(provider), temperature, int(max_tokens)

    def node_system_prompt(self, node_id: str) -> str:
        return (self.node(node_id).get("system_prompt") or "").strip()

    def node_user_prompt_template(self, node_id: str) -> str:
        return (self.node(node_id).get("user_prompt_template") or "").strip()

    def nl2sql_system_template(self) -> str:
        from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE
        text = self.node_system_prompt("nl2sql")
        return text or SYSTEM_PROMPT_TEMPLATE


def normalize_workflow_payload(workflow_config: dict | None) -> dict | None:
    if not workflow_config:
        return None
    nodes_in = workflow_config.get("nodes") if isinstance(workflow_config.get("nodes"), dict) else workflow_config
    if not isinstance(nodes_in, dict):
        return None
    nodes_out: dict = {}
    for node_id in LLM_NODE_IDS:
        raw = nodes_in.get(node_id)
        if not isinstance(raw, dict):
            continue
        cleaned: dict = {}
        for key in ("system_prompt", "user_prompt_template", "model_provider", "model_name", "temperature", "max_tokens"):
            if key in raw:
                cleaned[key] = raw[key]
        nodes_out[node_id] = cleaned
    return {"nodes": nodes_out}


def sync_workflow_to_agent(agent: AgentConfig, workflow_config: dict | None) -> None:
    """保存 workflow_config，并同步 nl2sql 系统 Prompt 到 system_prompt 列（兼容旧逻辑）。"""
    normalized = normalize_workflow_payload(workflow_config)
    agent.workflow_config = normalized
    if normalized:
        nl2sql = normalized.get("nodes", {}).get("nl2sql", {})
        prompt = (nl2sql.get("system_prompt") or "").strip()
        if prompt:
            agent.system_prompt = prompt
