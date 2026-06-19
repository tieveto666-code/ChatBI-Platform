from __future__ import annotations
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class DbConnectionCreate(BaseModel):
    name: str = Field(..., max_length=128)
    db_type: str = "sqlite"
    db_path: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_sqlite_only(self):
        if self.db_type != "sqlite":
            raise ValueError("MVP 当前仅支持 SQLite 数据源")
        if not self.db_path:
            raise ValueError("SQLite 数据源必须填写 db_path")
        path = Path(self.db_path)
        if not path.exists():
            raise ValueError(f"SQLite 文件不存在: {self.db_path}")
        if path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("SQLite 文件扩展名必须是 .db / .sqlite / .sqlite3")
        return self


class DbConnectionUpdate(BaseModel):
    name: str | None = None
    db_path: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_sqlite_path(self):
        if self.db_path:
            path = Path(self.db_path)
            if not path.exists():
                raise ValueError(f"SQLite 文件不存在: {self.db_path}")
            if path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
                raise ValueError("SQLite 文件扩展名必须是 .db / .sqlite / .sqlite3")
        return self


class DbConnectionInfo(BaseModel):
    id: int
    name: str
    db_type: str
    db_path: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    is_active: bool
    created_at: str | None = None

    class Config:
        from_attributes = True


class FileUploadInfo(BaseModel):
    id: int
    original_name: str
    file_size: int
    query_db_ready: bool = False
    sheet_count: int
    total_rows: int
    status: str
    created_at: str | None = None

    class Config:
        from_attributes = True


class SchemaTable(BaseModel):
    table_name: str
    columns: list[dict]


class SchemaResponse(BaseModel):
    tables: list[SchemaTable]


class FieldLexiconCreate(BaseModel):
    target_column: str = Field(..., max_length=128)
    standard_term: str = Field(..., max_length=128)
    synonyms: list[str] = Field(default_factory=list)


class FieldLexiconUpdate(BaseModel):
    target_column: str | None = Field(None, max_length=128)
    standard_term: str | None = Field(None, max_length=128)
    synonyms: list[str] | None = None


class FieldLexiconInfo(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    table_name: str
    target_column: str
    standard_term: str
    synonyms: list[str]
    created_at: str | None = None
    updated_at: str | None = None


# 兼容旧命名（路由 response_model）
TableSynonymCreate = FieldLexiconCreate
TableSynonymUpdate = FieldLexiconUpdate
TableSynonymInfo = FieldLexiconInfo
