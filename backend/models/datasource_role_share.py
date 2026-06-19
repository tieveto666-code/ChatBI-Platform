from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class DatasourceRoleShare(Base, TimestampMixin):
    """创建者将自建数据源共享给角色。"""

    __tablename__ = "datasource_role_shares"
    __table_args__ = (
        UniqueConstraint("resource_type", "resource_id", "role_id", name="uq_datasource_role_share"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), default="use")
