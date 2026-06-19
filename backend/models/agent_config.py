from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class AgentConfig(Base, TimestampMixin):
    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    synonym_map: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    model_provider: Mapped[str] = mapped_column(String(64), default="deepseek")
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    temperature: Mapped[int] = mapped_column(Integer, default=10)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    is_default: Mapped[bool] = mapped_column(Integer, default=False)
    is_active: Mapped[bool] = mapped_column(Integer, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    default_data_source_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    default_db_connection_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("db_connections.id"), nullable=True)
    default_file_upload_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("file_uploads.id"), nullable=True)
