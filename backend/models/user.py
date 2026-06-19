from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    role_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=True, comment="角色ID"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    role = relationship("Role", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
