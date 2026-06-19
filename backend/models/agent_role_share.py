from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class AgentRoleShare(Base, TimestampMixin):
    """创建者将自建智能体共享给角色。"""

    __tablename__ = "agent_role_shares"
    __table_args__ = (UniqueConstraint("agent_id", "role_id", name="uq_agent_role_share"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), default="use")
