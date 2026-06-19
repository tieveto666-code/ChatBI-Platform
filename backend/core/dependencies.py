from __future__ import annotations
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config import settings
from core.database import get_db
from core.exceptions import AuthError
from core.error_codes import ErrorCode
from models.user import User
from core.menu_access import get_user_allowed_route_paths, menu_route_allowed

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT Token 解析当前用户"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError(code=ErrorCode.TOKEN_INVALID, message="Token 无效")
    except JWTError:
        raise AuthError(code=ErrorCode.TOKEN_EXPIRED, message="Token 已过期或无效")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise AuthError(code=ErrorCode.TOKEN_INVALID, message="用户不存在")
    if not user.is_active:
        raise AuthError(code=ErrorCode.FORBIDDEN, message="用户已被禁用")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> User | None:
    """可选鉴权 — Token 不存在时返回 None"""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except JWTError:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin 权限守卫（仅按角色 code，保留给需显式限制为 admin 角色的场景）。"""
    role = current_user.role
    if not role or role.code != "admin":
        raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="需要管理员权限")
    return current_user


def require_menu_path(menu_route_path: str):
    """依赖工厂：当前用户角色须在 role_menus 中拥有对应前端 path（或父 path 覆盖子路径）。"""

    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        allowed = get_user_allowed_route_paths(db, current_user.id)
        if not menu_route_allowed(allowed, menu_route_path):
            raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="无权访问该功能")
        return current_user

    return _dep


def require_any_menu_paths(*menu_route_paths: str):
    """满足任一菜单 path 即可（用于用户列表可被「用户管理」或「角色管理」场景调用等）。"""
    paths = tuple(menu_route_paths)

    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        allowed = get_user_allowed_route_paths(db, current_user.id)
        if not any(menu_route_allowed(allowed, p) for p in paths):
            raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="无权访问该功能")
        return current_user

    return _dep
