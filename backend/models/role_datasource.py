from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class RoleDatasource(Base, TimestampMixin):
    """管理员为角色分配可访问的数据源。"""

    __tablename__ = "role_datasources"
    __table_args__ = (
        UniqueConstraint("role_id", "resource_type", "resource_id", name="uq_role_datasource"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)  # db_connection / file_upload
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    permission: Mapped[str] = mapped_column(String(20), default="use")
