from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class RoleAgent(Base, TimestampMixin):
    """管理员为角色分配可访问的智能体。"""

    __tablename__ = "role_agents"
    __table_args__ = (UniqueConstraint("role_id", "agent_id", name="uq_role_agent"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), default="use")  # use / edit / admin
