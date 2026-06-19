from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_menu_path
from core.exceptions import AuthError, BusinessError
from core.error_codes import ErrorCode
from models.agent_config import AgentConfig
from models.role import Role
from models.user import User
from schemas.agent import AgentConfigCreate, AgentConfigUpdate, AgentConfigInfo
from schemas.common import ApiResponse
from services.agent_service import agent_to_info, apply_agent_fields, default_system_prompt
from services.agent_workflow import workflow_template
from services.resource_access import (
    get_agent_permission,
    is_admin,
    list_visible_agents,
    list_visible_db_connections,
    list_visible_file_uploads,
    require_agent_permission,
    require_datasource_permission,
    set_agent_role_shares,
)

router = APIRouter()


def _validate_agent_datasource(db: Session, user: User, data: dict):
    dst = data.get("default_data_source_type")
    if not dst:
        return
    if dst == "db":
        conn_id = data.get("default_db_connection_id")
        if conn_id:
            require_datasource_permission(db, user, "db_connection", conn_id, "use")
    elif dst in ("excel", "csv"):
        file_id = data.get("default_file_upload_id")
        if file_id:
            require_datasource_permission(db, user, "file_upload", file_id, "use")


@router.get("", response_model=ApiResponse)
async def list_agents(
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """获取当前用户可见的智能体列表"""
    configs = list_visible_agents(db, current_user)
    items = [agent_to_info(db, current_user, c) for c in configs]
    return ApiResponse(data={"items": items, "total": len(items)})


@router.get("/workflow-template", response_model=ApiResponse)
async def get_workflow_template(
    current_user: User = Depends(require_menu_path("/agents")),
):
    """固定工作流结构、节点说明与默认 Prompt（智能体配置页使用）"""
    return ApiResponse(data=workflow_template())


@router.get("/datasource-options", response_model=ApiResponse)
async def list_datasource_options(
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """智能体配置页可选的数据源（当前用户有 use 权限）"""
    connections = list_visible_db_connections(db, current_user)
    files = list_visible_file_uploads(db, current_user)
    return ApiResponse(data={
        "db_connections": [
            {"id": c.id, "name": c.name, "db_type": c.db_type, "visibility": c.visibility or "private"}
            for c in connections
        ],
        "file_uploads": [
            {
                "id": f.id,
                "original_name": f.original_name,
                "query_db_ready": bool(f.query_db_path),
                "visibility": f.visibility or "private",
            }
            for f in files
        ],
    })


@router.get("/share-role-options", response_model=ApiResponse)
async def share_role_options(
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """智能体共享时可选择的角色列表"""
    roles = db.query(Role).order_by(Role.sort_order).all()
    return ApiResponse(data=[
        {"id": r.id, "name": r.name, "code": r.code} for r in roles
    ])


@router.post("", response_model=ApiResponse[AgentConfigInfo])
async def create_agent(
    request: AgentConfigCreate,
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """新建智能体（默认 private，创建者拥有 admin 权限）"""
    data = request.model_dump()
    shared_role_ids = data.pop("shared_role_ids", [])
    _validate_agent_datasource(db, current_user, data)

    config = AgentConfig(
        created_by=current_user.id,
        visibility=data.pop("visibility", "private"),
        system_prompt=data.get("system_prompt") or default_system_prompt(),
        is_default=False,
        is_active=True,
    )
    apply_agent_fields(config, data)
    if not config.workflow_config:
        from services.agent_workflow import sync_workflow_to_agent
        from prompts.workflow_defaults import default_workflow_config
        sync_workflow_to_agent(config, {"nodes": default_workflow_config(config.system_prompt)})
    db.add(config)
    db.flush()

    if shared_role_ids and (is_admin(current_user) or config.created_by == current_user.id):
        set_agent_role_shares(db, config.id, shared_role_ids)

    db.commit()
    db.refresh(config)
    return ApiResponse(data=agent_to_info(db, current_user, config))


@router.put("/{agent_id}", response_model=ApiResponse[AgentConfigInfo])
async def update_agent(
    agent_id: int,
    request: AgentConfigUpdate,
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """更新智能体（需 edit 权限或为创建者）"""
    config = require_agent_permission(db, current_user, agent_id, "edit")
    update_data = request.model_dump(exclude_none=True)
    shared_role_ids = update_data.pop("shared_role_ids", None)
    _validate_agent_datasource(db, current_user, update_data)

    if "is_default" in update_data and not is_admin(current_user):
        update_data.pop("is_default", None)

    apply_agent_fields(config, update_data)

    if shared_role_ids is not None:
        perm = get_agent_permission(db, current_user, config)
        if perm not in ("admin",) and not is_admin(current_user):
            raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="无权修改共享角色")
        set_agent_role_shares(db, config.id, shared_role_ids)

    db.commit()
    db.refresh(config)
    return ApiResponse(data=agent_to_info(db, current_user, config))


@router.delete("/{agent_id}", response_model=ApiResponse)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(require_menu_path("/agents")),
    db: Session = Depends(get_db),
):
    """删除智能体（需 admin 权限；系统默认智能体不可删）"""
    config = require_agent_permission(db, current_user, agent_id, "admin")
    if config.is_default:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="默认智能体不可删除")
    db.delete(config)
    db.commit()
    return ApiResponse(data={"message": "已删除"})
