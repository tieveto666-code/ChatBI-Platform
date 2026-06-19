from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class DatasourceFieldLexicon(Base, TimestampMixin):
    """数据源表字段术语：数据字段 + 标准词 + 多个同义词。"""

    __tablename__ = "datasource_field_lexicons"
    __table_args__ = (
        UniqueConstraint(
            "resource_type", "resource_id", "table_name", "target_column",
            name="uq_datasource_field_lexicon_column",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)  # db_connection | file_upload
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_column: Mapped[str] = mapped_column(String(128), nullable=False)
    standard_term: Mapped[str] = mapped_column(String(128), nullable=False)
    synonyms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
