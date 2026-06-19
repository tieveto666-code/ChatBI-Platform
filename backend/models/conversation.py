from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    data_source_type: Mapped[str] = mapped_column(String(32), default="db")  # db / excel / csv
    db_connection_id: Mapped[int] = mapped_column(Integer, ForeignKey("db_connections.id"), nullable=True, index=True)
    file_upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    agent_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_configs.id"), nullable=True, index=True)
    selected_tables: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string[]

    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    db_connection = relationship("DbConnection")
    file_upload = relationship("FileUpload")
