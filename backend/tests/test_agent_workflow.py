"""智能体工作流配置测试"""

from models.agent_config import AgentConfig
from prompts.workflow_defaults import INTENT_SYSTEM_PROMPT, LLM_NODE_IDS
from services.agent_workflow import (
    AgentWorkflowRuntime,
    resolve_workflow_config,
    sync_workflow_to_agent,
    workflow_template,
)


def test_workflow_template_has_all_llm_nodes():
    tpl = workflow_template()
    assert set(tpl["llm_nodes"]) == set(LLM_NODE_IDS)
    assert len(tpl["steps"]) >= len(LLM_NODE_IDS)


def test_resolve_workflow_merges_nl2sql_from_system_prompt():
    agent = AgentConfig(
        name="test",
        system_prompt="自定义 NL2SQL 模板 {schema_json}",
        model_provider="mock",
        temperature=10,
        max_tokens=4096,
    )
    cfg = resolve_workflow_config(agent)
    assert cfg["nl2sql"]["system_prompt"] == "自定义 NL2SQL 模板 {schema_json}"
    assert cfg["intent"]["system_prompt"] == INTENT_SYSTEM_PROMPT


def test_sync_workflow_updates_system_prompt_column():
    agent = AgentConfig(name="test", model_provider="mock", temperature=10, max_tokens=4096)
    sync_workflow_to_agent(agent, {
        "nodes": {
            "nl2sql": {"system_prompt": "新 NL2SQL {schema_json} {synonym_text}"},
        },
    })
    assert agent.system_prompt == "新 NL2SQL {schema_json} {synonym_text}"
    assert agent.workflow_config is not None


def test_runtime_node_llm_inherits_agent_defaults():
    agent = AgentConfig(
        name="test",
        model_provider="mock",
        model_name="mock-model",
        temperature=20,
        max_tokens=2048,
    )
    runtime = AgentWorkflowRuntime(agent)
    _, temp, tokens = runtime.node_llm("intent")
    assert temp == 0.2
    assert tokens == 64
