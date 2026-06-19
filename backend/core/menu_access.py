from __future__ import annotations

from sqlalchemy.orm import Session

from models.menu import Menu
from models.role_menu import RoleMenu
from models.user import User


def get_user_allowed_route_paths(db: Session, user_id: int) -> set[str]:
    """角色在 role_menus 中绑定的菜单 path（不含祖先补全，用于 API / 前端鉴权）。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.role_id:
        return set()
    rows = (
        db.query(Menu.path)
        .join(RoleMenu, RoleMenu.menu_id == Menu.id)
        .filter(
            RoleMenu.role_id == user.role_id,
            Menu.path.isnot(None),
            Menu.path != "",
        )
        .distinct()
        .all()
    )
    return {str(r[0]) for r in rows if r[0]}


def menu_route_allowed(allowed_paths: set[str], required_route_path: str) -> bool:
    """
    若 allowed 含 /admin，则允许 /admin/users 等子路径；
    仅含 /admin/users 时不允许 /admin/roles。
    """
    req = (required_route_path or "").strip() or "/"
    req = req.rstrip("/") or "/"
    for p in allowed_paths:
        if not p:
            continue
        base = str(p).strip().rstrip("/") or "/"
        if req == base or req.startswith(base + "/"):
            return True
    return False
