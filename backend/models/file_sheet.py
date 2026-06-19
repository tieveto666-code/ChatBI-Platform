from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class FileSheet(Base, TimestampMixin):
    __tablename__ = "file_sheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("file_uploads.id"), nullable=False, index=True)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_schema: Mapped[str] = mapped_column(Text, nullable=True)    # JSON 列定义
    name_mapping_json: Mapped[str] = mapped_column(Text, nullable=True)

    # 关系
    file_upload = relationship("FileUpload")
