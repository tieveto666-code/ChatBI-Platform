from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.exceptions import BusinessError, ValidationError
from core.error_codes import ErrorCode
from models.user import User
from models.role import Role
from models.menu import Menu
from models.role_menu import RoleMenu
from services.auth_service import AuthService


class AdminService:
    """后台管理服务 — 用户/角色/菜单 CRUD"""

    # ════════════════════════════════════════════
    # 用户管理
    # ════════════════════════════════════════════

    @staticmethod
    def list_users(db: Session, page: int = 1, page_size: int = 20, keyword: str = "") -> tuple[list[User], int]:
        query = db.query(User)
        if keyword:
            query = query.filter(
                or_(User.username.contains(keyword), User.email.contains(keyword))
            )
        total = query.count()
        users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return users, total

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="用户不存在",
            )
        return user

    @staticmethod
    def create_user(db: Session, username: str, password: str, email: str | None = None, role_id: int = 3) -> User:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValidationError(
                code=ErrorCode.USERNAME_EXISTS,
                message="用户名已被注册",
            )
        user = User(
            username=username,
            email=email,
            password_hash=AuthService._hash_password(password),
            role_id=role_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, data: dict) -> User:
        user = AdminService.get_user(db, user_id)
        for key, value in data.items():
            if key == "password" and value:
                setattr(user, "password_hash", AuthService._hash_password(value))
            elif key == "username" and value:
                existing = db.query(User).filter(User.username == value, User.id != user_id).first()
                if existing:
                    raise ValidationError(
                        code=ErrorCode.USERNAME_EXISTS,
                        message="用户名已被注册",
                    )
                setattr(user, key, value)
            elif value is not None and hasattr(user, key):
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user_status(db: Session, user_id: int, is_active: bool) -> User:
        user = AdminService.get_user(db, user_id)
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int):
        user = AdminService.get_user(db, user_id)
        if user.role and user.role.code == "admin":
            admin_count = db.query(User).join(Role).filter(Role.code == "admin").count()
            if admin_count <= 1:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="至少需要保留一个管理员账户",
                )
        db.delete(user)
        db.commit()

    # ════════════════════════════════════════════
    # 角色管理
    # ════════════════════════════════════════════

    @staticmethod
    def list_roles(db: Session) -> list[Role]:
        return db.query(Role).order_by(Role.sort_order).all()

    @staticmethod
    def get_role(db: Session, role_id: int) -> Role:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="角色不存在",
            )
        return role

    @staticmethod
    def create_role(db: Session, name: str, code: str, description: str = "", sort_order: int = 0, menu_ids: list[int] | None = None) -> Role:
        existing = db.query(Role).filter(Role.code == code).first()
        if existing:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"角色编码 '{code}' 已存在",
            )
        role = Role(
            name=name,
            code=code,
            description=description,
            sort_order=sort_order,
            is_system=False,
        )
        db.add(role)
        db.flush()

        # 关联菜单
        if menu_ids:
            for mid in menu_ids:
                db.add(RoleMenu(role_id=role.id, menu_id=mid, permission="write"))

        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def update_role(db: Session, role_id: int, data: dict) -> Role:
        role = AdminService.get_role(db, role_id)
        if role.is_system and "name" in data and data["name"]:
            # 系统角色可以改描述和排序，但不能改编码
            data.pop("code", None)

        for key, value in data.items():
            if key == "menu_ids" and value is not None:
                # 更新菜单关联
                AdminService._sync_role_menus(db, role_id, value)
            elif value is not None and hasattr(role, key):
                setattr(role, key, value)

        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role_id: int):
        role = AdminService.get_role(db, role_id)
        if role.is_system:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="系统预设角色不可删除",
            )
        # 将使用该角色的用户迁移到默认角色
        default_role = db.query(Role).filter(Role.code == "user").first()
        if default_role:
            db.query(User).filter(User.role_id == role_id).update({"role_id": default_role.id})
        db.delete(role)
        db.commit()

    @staticmethod
    def get_role_menu_ids(db: Session, role_id: int) -> list[int]:
        records = db.query(RoleMenu).filter(RoleMenu.role_id == role_id).all()
        return [rm.menu_id for rm in records]

    @staticmethod
    def _sync_role_menus(db: Session, role_id: int, menu_ids: list[int]):
        db.query(RoleMenu).filter(RoleMenu.role_id == role_id).delete()
        for mid in menu_ids:
            db.add(RoleMenu(role_id=role_id, menu_id=mid, permission="write"))
        db.flush()

    # ════════════════════════════════════════════
    # 菜单管理
    # ════════════════════════════════════════════

    @staticmethod
    def list_menus(db: Session, tree: bool = True) -> list[Menu]:
        """获取菜单列表，tree=True 返回树形结构"""
        if not tree:
            return db.query(Menu).order_by(Menu.sort_order).all()

        all_menus = db.query(Menu).order_by(Menu.sort_order).all()
        return AdminService._build_menu_tree(all_menus)

    @staticmethod
    def get_menu(db: Session, menu_id: int) -> Menu:
        menu = db.query(Menu).filter(Menu.id == menu_id).first()
        if not menu:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="菜单不存在",
            )
        return menu

    @staticmethod
    def create_menu(db: Session, data: dict) -> Menu:
        menu = Menu(**data)
        db.add(menu)
        db.commit()
        db.refresh(menu)
        return menu

    @staticmethod
    def update_menu(db: Session, menu_id: int, data: dict) -> Menu:
        menu = AdminService.get_menu(db, menu_id)
        for key, value in data.items():
            if value is not None and hasattr(menu, key):
                setattr(menu, key, value)
        db.commit()
        db.refresh(menu)
        return menu

    @staticmethod
    def delete_menu(db: Session, menu_id: int):
        menu = AdminService.get_menu(db, menu_id)
        # 删除子菜单关联
        db.query(Menu).filter(Menu.parent_id == menu_id).delete()
        # 删除角色-菜单关联
        db.query(RoleMenu).filter(RoleMenu.menu_id == menu_id).delete()
        db.delete(menu)
        db.commit()

    @staticmethod
    def expand_role_menu_ids_with_ancestors(db: Session, menu_ids: list[int]) -> set[int]:
        """把角色直接绑定的菜单 ID 扩展为包含祖先，便于拼导航树。"""
        if not menu_ids:
            return set()
        menus = db.query(Menu).filter(Menu.id.in_(menu_ids)).all()
        all_ids: set[int] = set(menu_ids)
        for m in menus:
            pid = m.parent_id
            while pid is not None:
                if pid in all_ids:
                    break
                all_ids.add(pid)
                p = db.query(Menu).filter(Menu.id == pid).first()
                if not p:
                    break
                pid = p.parent_id
        return all_ids

    @staticmethod
    def get_user_menus(db: Session, user_id: int) -> list[dict]:
        """获取用户可见的菜单树（所有角色一律按 role_menus，含祖先节点以便展示层级）。"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.role_id:
            return []

        menu_ids = [m[0] for m in db.query(RoleMenu.menu_id).filter(RoleMenu.role_id == user.role_id).all()]
        if not menu_ids:
            return []

        expanded = AdminService.expand_role_menu_ids_with_ancestors(db, menu_ids)
        all_menus = (
            db.query(Menu)
            .filter(Menu.id.in_(expanded))
            .order_by(Menu.sort_order)
            .all()
        )
        return AdminService._build_menu_tree(all_menus)

    @staticmethod
    def _build_menu_tree(menus: list[Menu]) -> list[dict]:
        """将扁平菜单列表转换为树形结构"""
        menu_map: dict[int, dict] = {}
        for m in menus:
            menu_map[m.id] = {
                "id": m.id,
                "parent_id": m.parent_id,
                "name": m.name,
                "icon": m.icon,
                "path": m.path,
                "component": m.component,
                "sort_order": m.sort_order,
                "is_visible": m.is_visible,
                "permission": getattr(m, "permission", None),
                "children": [],
            }

        roots = []
        for m in menu_map.values():
            if m["parent_id"] is None:
                roots.append(m)
            else:
                parent = menu_map.get(m["parent_id"])
                if parent:
                    parent["children"].append(m)

        # 按 sort_order 排序
        def sort_menus(items: list[dict]):
            items.sort(key=lambda x: x["sort_order"])
            for item in items:
                sort_menus(item["children"])

        sort_menus(roots)
        return roots
