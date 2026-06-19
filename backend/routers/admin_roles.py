from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_any_menu_paths, require_menu_path
from models.user import User
from models.role import Role
from models.agent_config import AgentConfig
from models.db_connection import DbConnection
from models.file_upload import FileUpload
from schemas.admin import RoleCreate, RoleUpdate, RoleInfo
from schemas.agent import RoleResourceUpdate
from schemas.common import ApiResponse
from services.admin_service import AdminService
from services.agent_service import (
    get_role_agent_grants,
    get_role_datasource_grants,
    set_role_agent_grants,
    set_role_datasource_grants,
)

router = APIRouter()
admin_service = AdminService()


@router.get("/roles", response_model=ApiResponse)
async def list_roles(
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取角色列表（Admin）"""
    roles = admin_service.list_roles(db)
    items = []
    for role in roles:
        menu_ids = admin_service.get_role_menu_ids(db, role.id)
        items.append({
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "sort_order": role.sort_order,
            "menu_ids": menu_ids,
            "created_at": str(role.created_at) if role.created_at else None,
            "updated_at": str(role.updated_at) if role.updated_at else None,
        })
    return ApiResponse(data={"items": items, "total": len(items)})


@router.get("/roles/all", response_model=ApiResponse)
async def list_all_roles(
    current_user: User = Depends(require_any_menu_paths("/admin/users", "/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取全部角色（前端下拉使用）"""
    roles = admin_service.list_roles(db)
    return ApiResponse(data=[
        {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "sort_order": role.sort_order,
        }
        for role in roles
    ])


@router.post("/roles", response_model=ApiResponse[RoleInfo])
async def create_role(
    request: RoleCreate,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """创建角色（Admin）"""
    role = admin_service.create_role(
        db=db,
        name=request.name,
        code=request.code,
        description=request.description,
        sort_order=request.sort_order,
        menu_ids=request.menu_ids,
    )
    return ApiResponse(data=RoleInfo(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        sort_order=role.sort_order,
        created_at=str(role.created_at) if role.created_at else None,
        updated_at=str(role.updated_at) if role.updated_at else None,
    ))


@router.get("/roles/{role_id}", response_model=ApiResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取角色详情（Admin）"""
    role = admin_service.get_role(db, role_id)
    menu_ids = admin_service.get_role_menu_ids(db, role.id)
    return ApiResponse(data={
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "is_system": role.is_system,
        "sort_order": role.sort_order,
        "menu_ids": menu_ids,
        "created_at": str(role.created_at) if role.created_at else None,
        "updated_at": str(role.updated_at) if role.updated_at else None,
    })


@router.put("/roles/{role_id}", response_model=ApiResponse[RoleInfo])
async def update_role(
    role_id: int,
    request: RoleUpdate,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """更新角色（Admin）"""
    role = admin_service.update_role(
        db=db,
        role_id=role_id,
        data=request.model_dump(exclude_none=True),
    )
    return ApiResponse(data=RoleInfo(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        sort_order=role.sort_order,
        created_at=str(role.created_at) if role.created_at else None,
        updated_at=str(role.updated_at) if role.updated_at else None,
    ))


@router.put("/roles/{role_id}/menus", response_model=ApiResponse[RoleInfo])
async def update_role_menus(
    role_id: int,
    request: RoleUpdate,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """更新角色菜单权限（Admin）"""
    role = admin_service.update_role(
        db=db,
        role_id=role_id,
        data={"menu_ids": request.menu_ids},
    )
    return ApiResponse(data=RoleInfo(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        sort_order=role.sort_order,
        created_at=str(role.created_at) if role.created_at else None,
        updated_at=str(role.updated_at) if role.updated_at else None,
    ))


@router.delete("/roles/{role_id}", response_model=ApiResponse)
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """删除角色（Admin）"""
    admin_service.delete_role(db, role_id)
    return ApiResponse(data={"message": "已删除"})


@router.get("/roles/{role_id}/resources", response_model=ApiResponse)
async def get_role_resources(
    role_id: int,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取角色的智能体/数据源授权"""
    admin_service.get_role(db, role_id)
    return ApiResponse(data={
        "agents": get_role_agent_grants(db, role_id),
        "datasources": get_role_datasource_grants(db, role_id),
    })


@router.put("/roles/{role_id}/resources", response_model=ApiResponse)
async def update_role_resources(
    role_id: int,
    request: RoleResourceUpdate,
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """更新角色的智能体/数据源授权"""
    admin_service.get_role(db, role_id)
    set_role_agent_grants(db, role_id, [g.model_dump() for g in request.agents])
    set_role_datasource_grants(db, role_id, [g.model_dump() for g in request.datasources])
    db.commit()
    return ApiResponse(data={
        "agents": get_role_agent_grants(db, role_id),
        "datasources": get_role_datasource_grants(db, role_id),
    })


@router.get("/resources/catalog", response_model=ApiResponse)
async def list_resource_catalog(
    current_user: User = Depends(require_menu_path("/admin/roles")),
    db: Session = Depends(get_db),
):
    """角色授权配置用的资源目录（管理员可见全部活跃资源）"""
    agents = db.query(AgentConfig).filter(AgentConfig.is_active == 1).order_by(AgentConfig.id).all()
    connections = db.query(DbConnection).filter(DbConnection.is_active == 1).order_by(DbConnection.id).all()
    files = db.query(FileUpload).order_by(FileUpload.id.desc()).all()
    return ApiResponse(data={
        "agents": [{"id": a.id, "name": a.name, "visibility": a.visibility or "private"} for a in agents],
        "db_connections": [{"id": c.id, "name": c.name, "visibility": c.visibility or "private"} for c in connections],
        "file_uploads": [{"id": f.id, "name": f.original_name, "visibility": f.visibility or "private"} for f in files],
    })
