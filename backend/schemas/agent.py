from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class WorkflowNodeConfig(BaseModel):
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentWorkflowConfig(BaseModel):
    intent: WorkflowNodeConfig | None = None
    nl2sql: WorkflowNodeConfig | None = None
    sql_fix: WorkflowNodeConfig | None = None
    summary: WorkflowNodeConfig | None = None
    direct_reply: WorkflowNodeConfig | None = None


class AgentConfigCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: str | None = None
    system_prompt: str | None = None
    workflow_config: dict | None = None
    synonym_map: dict | None = None
    model_provider: str = "deepseek"
    model_name: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    visibility: str = "private"
    default_data_source_type: str | None = None
    default_db_connection_id: int | None = None
    default_file_upload_id: int | None = None
    shared_role_ids: list[int] = []


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    workflow_config: dict | None = None
    synonym_map: dict | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    visibility: str | None = None
    default_data_source_type: str | None = None
    default_db_connection_id: int | None = None
    default_file_upload_id: int | None = None
    shared_role_ids: list[int] | None = None


class AgentConfigInfo(BaseModel):
    id: int
    name: str
    description: str | None = None
    system_prompt: str | None = None
    workflow_config: dict | None = None
    synonym_map: dict | None = None
    model_provider: str
    model_name: str | None = None
    temperature: float
    max_tokens: int
    is_default: bool
    is_active: bool
    created_by: int | None = None
    created_by_name: str | None = None
    visibility: str = "private"
    default_data_source_type: str | None = None
    default_db_connection_id: int | None = None
    default_file_upload_id: int | None = None
    shared_role_ids: list[int] = []
    permission: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class RoleAgentGrant(BaseModel):
    agent_id: int
    permission: str = "use"

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        if v not in ("use", "edit", "admin"):
            raise ValueError("permission 必须是 use / edit / admin")
        return v


class RoleDatasourceGrant(BaseModel):
    resource_type: str
    resource_id: int
    permission: str = "use"

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in ("db_connection", "file_upload"):
            raise ValueError("resource_type 必须是 db_connection / file_upload")
        return v

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        if v not in ("use", "edit", "admin"):
            raise ValueError("permission 必须是 use / edit / admin")
        return v


class RoleResourceUpdate(BaseModel):
    agents: list[RoleAgentGrant] = []
    datasources: list[RoleDatasourceGrant] = []
