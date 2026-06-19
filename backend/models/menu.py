from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.base import TimestampMixin


class Menu(Base, TimestampMixin):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menus.id"), nullable=True, comment="父菜单ID"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="菜单名称")
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="图标")
    path: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="路由路径")
    component: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="组件路径")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序号")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否可见")

    children = relationship("Menu", backref="parent", remote_side=[id])

    def __repr__(self) -> str:
        return f"<Menu(id={self.id}, name='{self.name}', path='{self.path}')>"
