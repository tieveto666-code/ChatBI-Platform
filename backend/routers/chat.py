from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db, SessionLocal
from core.dependencies import require_menu_path
from models.user import User
from models.conversation import Conversation
from models.message import Message
from schemas.chat import (
    ChatRequest,
    ConversationCreate,
    ConversationUpdate,
    ConversationInfo,
    MessageInfo,
    SQLExecuteRequest,
)
from schemas.common import ApiResponse
from services.chat_engine import ChatEngine
from services.chart_recommender import has_visual_chart
from services.sse_streamer import SSEStreamer
from services.resource_access import list_visible_agents

router = APIRouter()
chat_engine = ChatEngine()


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(require_menu_path("/chat")),
):
    """
    SSE 流式对话接口。
    客户端通过 EventSource 或 fetch + ReadableStream 消费 SSE 事件。
    """
    streamer = SSEStreamer()
    user_id = current_user.id

    async def run_pipeline():
        db = SessionLocal()
        try:
            await chat_engine.process_message(
                user_query=request.message,
                conversation_id=request.conversation_id,
                user_id=user_id,
                db=db,
                datasource_type=request.data_source_type or request.datasource_type or "chat",
                db_connection_id=request.db_connection_id,
                file_upload_id=request.file_upload_id,
                agent_config_id=request.agent_config_id,
                streamer=streamer,
            )
        finally:
            db.close()

    asyncio.create_task(run_pipeline())
    return streamer.to_response()


@router.get("/chat/agents", response_model=ApiResponse)
async def list_chat_agents(
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """对话页可选智能体列表（当前用户有 use 权限）"""
    configs = list_visible_agents(db, current_user)
    default = next((c for c in configs if c.is_default), None)
    return ApiResponse(data={
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "is_default": bool(c.is_default),
                "model_provider": c.model_provider,
                "model_name": c.model_name,
                "default_data_source_type": c.default_data_source_type,
                "default_db_connection_id": c.default_db_connection_id,
                "default_file_upload_id": c.default_file_upload_id,
            }
            for c in configs
        ],
        "default_id": default.id if default else (configs[0].id if configs else None),
    })


def _conversation_info(conversation: Conversation, message_count: int = 0) -> ConversationInfo:
    return ConversationInfo(
        id=conversation.id,
        title=conversation.title,
        data_source_type=conversation.data_source_type,
        db_connection_id=conversation.db_connection_id,
        file_upload_id=conversation.file_upload_id,
        agent_config_id=conversation.agent_config_id,
        message_count=message_count,
        created_at=str(conversation.created_at) if conversation.created_at else None,
        updated_at=str(conversation.updated_at) if conversation.updated_at else None,
    )


# ── 对话 CRUD ──


@router.get("/conversations", response_model=ApiResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """获取当前用户的对话列表"""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    total = query.count()
    conversations = query.order_by(Conversation.updated_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for conv in conversations:
        msg_count = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()
        items.append(_conversation_info(conv, msg_count))

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/conversations/{conversation_id}/execute-sql", response_model=ApiResponse)
async def execute_conversation_sql(
    conversation_id: int,
    request: SQLExecuteRequest,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """手动编辑 SQL 后重新执行，返回可直接渲染的表格与图表数据。"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    is_valid, error_msg = chat_engine.sql_validator.validate(request.sql)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"SQL 校验失败: {error_msg}")

    sql = chat_engine.sql_validator.apply_limit(request.sql)
    result = chat_engine.sql_executor.execute(sql, chat_engine._get_db_path(db, conversation))
    chart_payload = chat_engine._build_chart_sse_payload(result)
    table_data = {
        "columns": result.get("columns", []),
        "rows": chat_engine._rows_to_objects(result),
    }
    chart_data = None
    chart_type = None
    if chart_payload and has_visual_chart(chart_payload):
        chart_type = chart_payload.get("default_type") or chart_payload.get("type")
        default_option = (chart_payload.get("options") or {}).get(chart_type, {})
        chart_data = {
            "default_type": chart_type,
            "available_types": chart_payload.get("available_types", []),
            "x_axis": chart_payload.get("x_axis", []),
            "options": chart_payload.get("options", {}),
            "series": default_option.get("series", chart_payload.get("series", [])),
            "config": chart_payload.get("config", {}),
        }
    elif chart_payload:
        chart_type = chart_payload.get("default_type") or "table"

    return ApiResponse(data={
        "sql": sql,
        "table_data": table_data,
        "chart_data": chart_data,
        "chart_type": chart_type,
    })


@router.post("/conversations", response_model=ApiResponse[ConversationInfo])
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """创建新对话"""
    conversation = Conversation(
        title=request.title,
        user_id=current_user.id,
        data_source_type=request.data_source_type or "chat",
        db_connection_id=request.db_connection_id if request.data_source_type == "db" else None,
        file_upload_id=request.file_upload_id if request.data_source_type in {"excel", "csv"} else None,
        agent_config_id=request.agent_config_id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return ApiResponse(data=_conversation_info(conversation))


@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """获取对话详情"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    msg_count = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).count()

    return ApiResponse(data=_conversation_info(conversation, msg_count))


@router.patch("/conversations/{conversation_id}", response_model=ApiResponse[ConversationInfo])
async def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """更新对话（标题等）"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    if request.title is not None:
        conversation.title = request.title
    if request.data_source_type is not None:
        conversation.data_source_type = request.data_source_type
        conversation.db_connection_id = request.db_connection_id
        conversation.file_upload_id = request.file_upload_id
    elif request.db_connection_id is not None:
        conversation.data_source_type = "db"
        conversation.db_connection_id = request.db_connection_id
        conversation.file_upload_id = None
    elif request.file_upload_id is not None:
        conversation.data_source_type = "excel"
        conversation.file_upload_id = request.file_upload_id
        conversation.db_connection_id = None
    if request.agent_config_id is not None:
        conversation.agent_config_id = request.agent_config_id

    db.commit()
    db.refresh(conversation)

    return ApiResponse(data=_conversation_info(conversation))


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """删除对话"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    db.delete(conversation)
    db.commit()
    return ApiResponse(data={"message": "已删除"})


@router.get("/conversations/{conversation_id}/messages", response_model=ApiResponse)
async def list_messages(
    conversation_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_menu_path("/chat")),
    db: Session = Depends(get_db),
):
    """获取对话的消息列表"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    total = query.count()
    messages = query.order_by(Message.created_at).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for msg in messages:
        items.append(MessageInfo(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            metadata_json=msg.metadata_json,
            created_at=str(msg.created_at) if msg.created_at else None,
        ))

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
