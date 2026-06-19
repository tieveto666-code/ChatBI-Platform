from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.base import TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="角色编码")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="角色描述")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否系统内置")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序号")

    users = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', code='{self.code}')>"
