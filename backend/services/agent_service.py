from __future__ import annotations

from sqlalchemy.orm import Session

from models.agent_config import AgentConfig
from models.role_agent import RoleAgent
from models.role_datasource import RoleDatasource
from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE
from schemas.agent import AgentConfigInfo
from core.exceptions import BusinessError
from core.error_codes import ErrorCode
from services.agent_workflow import resolve_workflow_config, sync_workflow_to_agent
from prompts.workflow_defaults import default_workflow_config
from services.resource_access import (
    get_agent_permission,
    get_agent_shared_role_ids,
    set_agent_role_shares,
)


def default_system_prompt() -> str:
    """返回含 {schema_json} / {synonym_text} 占位符的 NL2SQL 模板。"""
    return SYSTEM_PROMPT_TEMPLATE


def agent_llm_temperature(agent: AgentConfig) -> float:
    return (agent.temperature or 10) / 100


def agent_system_prompt_template(agent: AgentConfig) -> str:
    text = (agent.system_prompt or "").strip()
    return text or SYSTEM_PROMPT_TEMPLATE


def format_agent_synonym_text(agent: AgentConfig) -> str:
    if not agent.synonym_map:
        return ""
    return "\n".join(f"{k} → {v}" for k, v in agent.synonym_map.items())


def resolve_agent_for_user(db: Session, user, agent_config_id: int | None) -> AgentConfig:
    """对话页解析智能体：显式 ID 或系统默认，需 use 权限。"""
    from services.resource_access import get_agent_permission, list_visible_agents, require_agent_permission

    if agent_config_id:
        return require_agent_permission(db, user, agent_config_id, "use")

    default = db.query(AgentConfig).filter(
        AgentConfig.is_default == 1,
        AgentConfig.is_active == 1,
    ).first()
    if default and get_agent_permission(db, user, default):
        return default

    visible = list_visible_agents(db, user)
    if not visible:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="无可用智能体，请联系管理员配置")
    return visible[0]


def apply_agent_default_datasource(db: Session, user, conversation, agent: AgentConfig) -> None:
    """将智能体默认数据源同步到会话（问数时使用，覆盖旧的数据源绑定）。"""
    from services.resource_access import get_datasource_permission

    dst = agent.default_data_source_type
    if not dst:
        return

    if dst == "db" and agent.default_db_connection_id:
        if not get_datasource_permission(db, user, "db_connection", agent.default_db_connection_id):
            return
        conversation.data_source_type = "db"
        conversation.db_connection_id = agent.default_db_connection_id
        conversation.file_upload_id = None
        db.commit()
        db.refresh(conversation)
        return

    if dst in ("excel", "csv") and agent.default_file_upload_id:
        if not get_datasource_permission(db, user, "file_upload", agent.default_file_upload_id):
            return
        conversation.data_source_type = dst
        conversation.file_upload_id = agent.default_file_upload_id
        conversation.db_connection_id = None
        db.commit()
        db.refresh(conversation)


def agent_owner_name(db: Session, agent: AgentConfig) -> str:
    if agent.is_default:
        return "系统"
    if not agent.created_by:
        return "—"
    from models.user import User
    owner = db.query(User).filter(User.id == agent.created_by).first()
    return owner.username if owner else "—"


def agent_to_info(db: Session, user, agent: AgentConfig) -> AgentConfigInfo:
    return AgentConfigInfo(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        workflow_config=resolve_workflow_config(agent),
        synonym_map=agent.synonym_map,
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        temperature=agent.temperature / 100 if agent.temperature else 0.1,
        max_tokens=agent.max_tokens,
        is_default=bool(agent.is_default),
        is_active=bool(agent.is_active),
        created_by=agent.created_by,
        created_by_name=agent_owner_name(db, agent),
        visibility=agent.visibility or "private",
        default_data_source_type=agent.default_data_source_type,
        default_db_connection_id=agent.default_db_connection_id,
        default_file_upload_id=agent.default_file_upload_id,
        shared_role_ids=get_agent_shared_role_ids(db, agent.id),
        permission=get_agent_permission(db, user, agent),
        created_at=str(agent.created_at) if agent.created_at else None,
        updated_at=str(agent.updated_at) if agent.updated_at else None,
    )


def apply_agent_fields(agent: AgentConfig, data: dict):
    if "temperature" in data:
        data["temperature"] = int(round(data["temperature"] * 100))
    workflow_config = data.pop("workflow_config", None)
    if workflow_config is not None:
        sync_workflow_to_agent(agent, workflow_config)
    for key, value in data.items():
        if key == "shared_role_ids":
            continue
        if hasattr(agent, key):
            setattr(agent, key, value)
    if workflow_config is None and "system_prompt" in data and data.get("system_prompt"):
        sync_workflow_to_agent(agent, {"nodes": {"nl2sql": {"system_prompt": data["system_prompt"]}}})


def set_role_agent_grants(db: Session, role_id: int, grants: list[dict]):
    db.query(RoleAgent).filter(RoleAgent.role_id == role_id).delete()
    for item in grants:
        db.add(RoleAgent(
            role_id=role_id,
            agent_id=item["agent_id"],
            permission=item.get("permission", "use"),
        ))


def set_role_datasource_grants(db: Session, role_id: int, grants: list[dict]):
    db.query(RoleDatasource).filter(RoleDatasource.role_id == role_id).delete()
    for item in grants:
        db.add(RoleDatasource(
            role_id=role_id,
            resource_type=item["resource_type"],
            resource_id=item["resource_id"],
            permission=item.get("permission", "use"),
        ))


def get_role_agent_grants(db: Session, role_id: int) -> list[dict]:
    rows = db.query(RoleAgent).filter(RoleAgent.role_id == role_id).all()
    return [{"agent_id": r.agent_id, "permission": r.permission} for r in rows]


def get_role_datasource_grants(db: Session, role_id: int) -> list[dict]:
    rows = db.query(RoleDatasource).filter(RoleDatasource.role_id == role_id).all()
    return [{
        "resource_type": r.resource_type,
        "resource_id": r.resource_id,
        "permission": r.permission,
    } for r in rows]


DEFAULT_AGENT_NAME = "默认 NL2SQL 智能体"


def ensure_default_agent(db: Session) -> AgentConfig:
    """保证存在且已预配置的默认智能体（不可删除，应用启动时调用）。"""
    from models.db_connection import DbConnection

    default = db.query(AgentConfig).filter(AgentConfig.is_default == 1).first()
    demo_conn = (
        db.query(DbConnection)
        .filter(DbConnection.is_active == 1)
        .order_by(DbConnection.id)
        .first()
    )

    if default:
        default.visibility = default.visibility or "public"
        default.is_active = True
        if demo_conn and not default.default_db_connection_id:
            default.default_data_source_type = "db"
            default.default_db_connection_id = demo_conn.id
        if not default.system_prompt:
            default.system_prompt = default_system_prompt()
        if not default.workflow_config:
            sync_workflow_to_agent(default, {"nodes": default_workflow_config(default.system_prompt)})
        db.commit()
        return default

    config = AgentConfig(
        name=DEFAULT_AGENT_NAME,
        description="MVP 内置问数智能体，可在智能体配置页调整工作流与 Prompt",
        system_prompt=default_system_prompt(),
        synonym_map=None,
        model_provider="deepseek",
        model_name="deepseek-chat",
        temperature=10,
        max_tokens=4096,
        is_default=True,
        is_active=True,
        visibility="public",
        default_data_source_type="db" if demo_conn else None,
        default_db_connection_id=demo_conn.id if demo_conn else None,
    )
    db.add(config)
    db.flush()
    sync_workflow_to_agent(config, {"nodes": default_workflow_config(config.system_prompt)})
    db.commit()
    db.refresh(config)
    return config
