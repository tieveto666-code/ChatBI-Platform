from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.base import TimestampMixin


class RoleMenu(Base, TimestampMixin):
    __tablename__ = "role_menus"
    __table_args__ = (
        UniqueConstraint("role_id", "menu_id", name="uq_role_menu"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=False, comment="角色ID"
    )
    menu_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menus.id"), nullable=False, comment="菜单ID"
    )
    permission: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="权限标识"
    )

    def __repr__(self) -> str:
        return f"<RoleMenu(role_id={self.role_id}, menu_id={self.menu_id})>"
