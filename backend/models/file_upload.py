from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Integer, Text, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class FileUpload(Base, TimestampMixin):
    __tablename__ = "file_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    original_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    query_db_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    sheet_count: Mapped[int] = mapped_column(Integer, default=0)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    schema_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
