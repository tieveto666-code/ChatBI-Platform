from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_any_menu_paths, require_menu_path
from models.user import User
from schemas.admin import UserCreate, UserUpdate, UserInfo, UserStatusUpdate
from schemas.common import ApiResponse
from services.admin_service import AdminService

router = APIRouter()
admin_service = AdminService()


@router.get("/users", response_model=ApiResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    current_user: User = Depends(require_any_menu_paths("/admin/users", "/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取用户列表（Admin）"""
    users, total = admin_service.list_users(db, page, page_size, keyword)
    items = [
        UserInfo(
            id=u.id,
            username=u.username,
            email=u.email,
            role_id=u.role_id,
            role_name=u.role.name if u.role else None,
            role_code=u.role.code if u.role else None,
            is_active=u.is_active,
            created_at=str(u.created_at) if u.created_at else None,
            updated_at=str(u.updated_at) if u.updated_at else None,
        )
        for u in users
    ]
    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/users", response_model=ApiResponse[UserInfo])
async def create_user(
    request: UserCreate,
    current_user: User = Depends(require_menu_path("/admin/users")),
    db: Session = Depends(get_db),
):
    """创建用户（Admin）"""
    user = admin_service.create_user(
        db=db,
        username=request.username,
        password=request.password,
        email=request.email,
        role_id=request.role_id,
    )
    return ApiResponse(data=UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_code=user.role.code if user.role else None,
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
        updated_at=str(user.updated_at) if user.updated_at else None,
    ))


@router.get("/users/{user_id}", response_model=ApiResponse[UserInfo])
async def get_user(
    user_id: int,
    current_user: User = Depends(require_menu_path("/admin/users")),
    db: Session = Depends(get_db),
):
    """获取用户详情（Admin）"""
    user = admin_service.get_user(db, user_id)
    return ApiResponse(data=UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_code=user.role.code if user.role else None,
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
        updated_at=str(user.updated_at) if user.updated_at else None,
    ))


@router.put("/users/{user_id}", response_model=ApiResponse[UserInfo])
async def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(require_menu_path("/admin/users")),
    db: Session = Depends(get_db),
):
    """更新用户（Admin）"""
    user = admin_service.update_user(
        db=db,
        user_id=user_id,
        data=request.model_dump(exclude_none=True),
    )
    return ApiResponse(data=UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_code=user.role.code if user.role else None,
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
        updated_at=str(user.updated_at) if user.updated_at else None,
    ))


@router.put("/users/{user_id}/status", response_model=ApiResponse[UserInfo])
async def update_user_status(
    user_id: int,
    request: UserStatusUpdate,
    current_user: User = Depends(require_menu_path("/admin/users")),
    db: Session = Depends(get_db),
):
    """启用/禁用用户（Admin）"""
    user = admin_service.update_user_status(
        db=db,
        user_id=user_id,
        is_active=request.is_active,
    )
    return ApiResponse(data=UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_code=user.role.code if user.role else None,
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
        updated_at=str(user.updated_at) if user.updated_at else None,
    ))


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_menu_path("/admin/users")),
    db: Session = Depends(get_db),
):
    """删除用户（Admin）"""
    admin_service.delete_user(db, user_id)
    return ApiResponse(data={"message": "已删除"})
