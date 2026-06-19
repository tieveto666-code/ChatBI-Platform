from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.menu_access import get_user_allowed_route_paths
from core.dependencies import get_current_user, require_any_menu_paths, require_menu_path
from models.user import User
from schemas.admin import MenuCreate, MenuUpdate, MenuInfo
from schemas.common import ApiResponse
from services.admin_service import AdminService

router = APIRouter()
admin_service = AdminService()


@router.get("/menus", response_model=ApiResponse)
async def list_menus(
    tree: bool = True,
    current_user: User = Depends(require_any_menu_paths("/admin/menus", "/admin/roles")),
    db: Session = Depends(get_db),
):
    """获取菜单列表（Admin，树形结构）"""
    menus = admin_service.list_menus(db, tree=tree)
    return ApiResponse(data={"items": menus, "total": len(menus)})


@router.post("/menus", response_model=ApiResponse[MenuInfo])
async def create_menu(
    request: MenuCreate,
    current_user: User = Depends(require_menu_path("/admin/menus")),
    db: Session = Depends(get_db),
):
    """创建菜单（Admin）"""
    menu = admin_service.create_menu(
        db=db,
        data=request.model_dump(exclude_none=True),
    )
    return ApiResponse(data=MenuInfo(
        id=menu.id,
        parent_id=menu.parent_id,
        name=menu.name,
        icon=menu.icon,
        path=menu.path,
        component=menu.component,
        sort_order=menu.sort_order,
        is_visible=menu.is_visible,
        permission=getattr(menu, "permission", None),
    ))


# ── 用户可见菜单（非 Admin 用）──


@router.get("/menus/user", response_model=ApiResponse)
async def get_user_menus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户可见的菜单树；allowed_paths 为 role_menus 直接绑定的 path，用于前端路由鉴权。"""
    menus = admin_service.get_user_menus(db, current_user.id)
    allowed_paths = sorted(get_user_allowed_route_paths(db, current_user.id))
    return ApiResponse(
        data={"items": menus, "total": len(menus), "allowed_paths": allowed_paths}
    )


@router.get("/menus/{menu_id}", response_model=ApiResponse[MenuInfo])
async def get_menu(
    menu_id: int,
    current_user: User = Depends(require_menu_path("/admin/menus")),
    db: Session = Depends(get_db),
):
    """获取菜单详情（Admin）"""
    menu = admin_service.get_menu(db, menu_id)
    return ApiResponse(data=MenuInfo(
        id=menu.id,
        parent_id=menu.parent_id,
        name=menu.name,
        icon=menu.icon,
        path=menu.path,
        component=menu.component,
        sort_order=menu.sort_order,
        is_visible=menu.is_visible,
        permission=getattr(menu, "permission", None),
    ))


@router.put("/menus/{menu_id}", response_model=ApiResponse[MenuInfo])
async def update_menu(
    menu_id: int,
    request: MenuUpdate,
    current_user: User = Depends(require_menu_path("/admin/menus")),
    db: Session = Depends(get_db),
):
    """更新菜单（Admin）"""
    menu = admin_service.update_menu(
        db=db,
        menu_id=menu_id,
        data=request.model_dump(exclude_none=True),
    )
    return ApiResponse(data=MenuInfo(
        id=menu.id,
        parent_id=menu.parent_id,
        name=menu.name,
        icon=menu.icon,
        path=menu.path,
        component=menu.component,
        sort_order=menu.sort_order,
        is_visible=menu.is_visible,
        permission=getattr(menu, "permission", None),
    ))


@router.delete("/menus/{menu_id}", response_model=ApiResponse)
async def delete_menu(
    menu_id: int,
    current_user: User = Depends(require_menu_path("/admin/menus")),
    db: Session = Depends(get_db),
):
    """删除菜单（Admin）"""
    admin_service.delete_menu(db, menu_id)
    return ApiResponse(data={"message": "已删除"})

