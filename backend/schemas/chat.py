from __future__ import annotations
from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: int | None = None
    data_source_type: str | None = None      # db / excel / csv
    datasource_type: str | None = None       # backward compatibility
    db_connection_id: int | None = None
    file_upload_id: int | None = None
    agent_config_id: int | None = None

    @model_validator(mode="after")
    def validate_new_conversation_datasource(self):
        """允许先不绑定数据源，由后端意图识别决定走问数还是普通回复。"""
        dst = self.data_source_type or self.datasource_type
        if dst == "db" and self.db_connection_id is None and self.conversation_id is None:
            raise ValueError("data_source_type=db 时必须提供 db_connection_id")
        if dst in ("excel", "csv") and self.file_upload_id is None and self.conversation_id is None:
            raise ValueError("data_source_type 为 excel/csv 时必须提供 file_upload_id")
        return self


class ChatStreamEvent(BaseModel):
    event: str   # token / sql / chart / table / error / done
    data: dict


class ConversationCreate(BaseModel):
    title: str | None = None
    data_source_type: str | None = None
    db_connection_id: int | None = None
    file_upload_id: int | None = None
    agent_config_id: int | None = None

    @model_validator(mode="after")
    def validate_datasource_ids(self):
        """允许创建未绑定数据源的普通对话；显式选择数据源时校验对应 ID。"""
        dst = self.data_source_type
        if dst == "db" and self.db_connection_id is None:
            raise ValueError("data_source_type=db 时必须提供 db_connection_id")
        if dst in ("excel", "csv") and self.file_upload_id is None:
            raise ValueError("data_source_type 为 excel/csv 时必须提供 file_upload_id")
        return self


class ConversationUpdate(BaseModel):
    title: str | None = None
    data_source_type: str | None = None
    db_connection_id: int | None = None
    file_upload_id: int | None = None
    agent_config_id: int | None = None


class ConversationInfo(BaseModel):
    id: int
    title: str | None = None
    data_source_type: str
    db_connection_id: int | None = None
    file_upload_id: int | None = None
    agent_config_id: int | None = None
    message_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=50000)


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    metadata_json: dict | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True
