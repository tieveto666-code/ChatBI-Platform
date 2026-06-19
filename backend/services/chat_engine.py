from __future__ import annotations
import asyncio
import json

from sqlalchemy.orm import Session

from config import settings
from core.exceptions import BusinessError, ChatBIException
from core.error_codes import ErrorCode
from models.conversation import Conversation
from models.message import Message
from models.query_log import QueryLog
from models.user import User
from models.agent_config import AgentConfig
from schemas.chat import ChatStreamEvent
from services.llm_service import LLMService
from services.prompt_builder import PromptBuilder
from services.sql_validator import SQLValidator
from services.sql_executor import SQLExecutor
from services.sse_streamer import SSEStreamer
from services.agent_service import (
    resolve_agent_for_user,
    apply_agent_default_datasource,
)
from services.agent_workflow import AgentWorkflowRuntime
from services.table_synonym_service import format_synonyms_for_prompt
from services.chart_recommender import recommend_chart, has_visual_chart


class ChatEngine:
    """
    NL2SQL 管线编排引擎 — 8 步工作流。
    处理用户自然语言问题，返回 SSE 流式响应。
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_builder = PromptBuilder()
        self.sql_validator = SQLValidator()
        self.sql_executor = SQLExecutor()

    async def process_message(
        self,
        user_query: str,
        conversation_id: int | None,
        user_id: int,
        db: Session,
        datasource_type: str = "db",
        db_connection_id: int | None = None,
        file_upload_id: int | None = None,
        agent_config_id: int | None = None,
        streamer: SSEStreamer | None = None,
    ) -> SSEStreamer:
        """
        处理用户消息，返回 SSE 流式响应。

        8 步管线：
        1. 加载对话 & 上下文
        2. 构建 Prompt
        3. 调用 LLM（流式 + 重试）
        4. SQL 安全校验（含重试）
        5. SQL 执行（含重试）
        6. 生成自然语言总结
        7. 图表渲染
        8. 持久化 & 完成
        """
        streamer = streamer or SSEStreamer()

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="用户不存在")

        agent = resolve_agent_for_user(db, user, agent_config_id)
        workflow = AgentWorkflowRuntime(agent)

        sql_text = ""
        result = None
        summary_text = ""
        chart_payload = None

        try:
            # ── [1] 加载对话 & 上下文 ──
            conversation = await self._load_conversation(
                db, conversation_id, user_id,
                datasource_type, db_connection_id, file_upload_id,
                agent.id,
                user_query=user_query,
            )
            if conversation.agent_config_id != agent.id:
                conversation.agent_config_id = agent.id
                db.commit()
                db.refresh(conversation)

            history = await self._load_history(db, conversation.id)

            intent_llm, intent_temp, intent_tokens = workflow.node_llm("intent")
            intent = await self._recognize_intent(
                user_query, history, intent_llm,
                system_prompt=workflow.node_system_prompt("intent"),
                temperature=intent_temp,
                max_tokens=intent_tokens,
            )
            if intent == "other":
                direct_llm, direct_temp, direct_tokens = workflow.node_llm("direct_reply")
                summary_text = await self._generate_direct_reply(
                    user_query=user_query,
                    history=history,
                    streamer=streamer,
                    llm_service=direct_llm,
                    system_prompt=workflow.node_system_prompt("direct_reply"),
                    temperature=direct_temp,
                    max_tokens=direct_tokens,
                )
                assistant_message_id = await self._save_direct_reply(
                    db, conversation, user_query, summary_text,
                )
                await streamer.send(ChatStreamEvent(event="done", data={
                    "conversation_id": conversation.id,
                    "message_id": assistant_message_id,
                    "token_usage": None,
                    "intent": intent,
                }))
                return streamer

            self._sync_request_datasource(
                db,
                conversation,
                datasource_type,
                db_connection_id,
                file_upload_id,
                user,
            )
            if (datasource_type or "chat").lower() == "chat":
                apply_agent_default_datasource(db, user, conversation, agent)
            self._ensure_data_source_for_query(db, conversation)
            schema = await self._load_schema(db, conversation, agent)
            synonym_text = format_synonyms_for_prompt(db, conversation, schema)

            # ── [2] 构建 Prompt ──
            messages = self.prompt_builder.build(
                user_query=user_query,
                schema=schema,
                synonym_text=synonym_text,
                conversation_history=history,
                system_prompt_template=workflow.nl2sql_system_template(),
            )

            # ── [3] 调用 LLM（流式 + 重试）──
            nl2sql_llm, nl2sql_temp, nl2sql_tokens = workflow.node_llm("nl2sql")
            sql_text = ""
            async for event in self._call_llm_with_retry(
                messages, nl2sql_llm, temperature=nl2sql_temp, max_tokens=nl2sql_tokens,
            ):
                if event.event == "token":
                    sql_text += event.data.get("text", "")

            if not sql_text.strip():
                raise BusinessError(
                    code=ErrorCode.LLM_CALL_FAILED,
                    message="LLM 未生成有效 SQL",
                )

            sql_candidate = self.sql_validator.extract_select_sql(sql_text)
            if not sql_candidate:
                prose = sql_text.strip()
                await streamer.send(ChatStreamEvent(event="token", data={"text": prose}))
                assistant_message_id = await self._save_direct_reply(
                    db, conversation, user_query, prose,
                )
                await streamer.send(ChatStreamEvent(event="done", data={
                    "conversation_id": conversation.id,
                    "message_id": assistant_message_id,
                    "token_usage": None,
                    "intent": "ask_data_prose",
                }))
                return streamer

            sql_text = sql_candidate

            # 发送 SQL 事件
            await streamer.send(ChatStreamEvent(event="sql", data={"sql": sql_text}))

            # ── [4] SQL 校验（含重试）──
            fix_llm, fix_temp, fix_tokens = workflow.node_llm("sql_fix")
            sql_text = await self._validate_sql_with_retry(
                sql_text, messages, fix_llm,
                user_prompt_template=workflow.node_user_prompt_template("sql_fix"),
                temperature=fix_temp,
                max_tokens=fix_tokens,
            )

            # ── [5] SQL 执行（含重试）──
            result = await self._execute_sql_with_retry(db, sql_text, conversation)
            await streamer.send(ChatStreamEvent(event="table", data=result))

            # ── [6] 生成自然语言总结（流式 token，符合 SSE 协议）──
            summary_llm, summary_temp, summary_tokens = workflow.node_llm("summary")
            summary_text = await self._generate_summary(
                result, user_query, sql_text, streamer, summary_llm,
                system_prompt=workflow.node_system_prompt("summary"),
                user_prompt_template=workflow.node_user_prompt_template("summary"),
                temperature=summary_temp,
                max_tokens=summary_tokens,
            )

            # ── [7] 图表数据（与 API 规范：type + {name,value}[] + config）──
            chart_payload = self._build_chart_sse_payload(result)
            if chart_payload is not None and has_visual_chart(chart_payload):
                await streamer.send(ChatStreamEvent(event="chart", data=chart_payload))

            # ── [8] 持久化 & 完成 ──
            assistant_message_id = await self._save_conversation(
                db, conversation, user_id, user_query, sql_text, result, summary_text, chart_payload,
            )
            await streamer.send(ChatStreamEvent(event="done", data={
                "conversation_id": conversation.id,
                "message_id": assistant_message_id,
                "token_usage": None,
                "intent": intent,
            }))

        except ChatBIException as e:
            await streamer.send(ChatStreamEvent(
                event="error",
                data={
                    "code": e.code,
                    "message": e.message,
                    "detail": e.detail,
                },
            ))
        except Exception as e:
            await streamer.send(ChatStreamEvent(
                event="error",
                data={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "服务器内部错误",
                    "detail": str(e) if settings.DEBUG else None,
                },
            ))

        return streamer

    # ── 步骤 1: 加载对话、上下文与意图 ──

    async def _load_conversation(
        self,
        db: Session,
        conversation_id: int | None,
        user_id: int,
        datasource_type: str,
        db_connection_id: int | None,
        file_upload_id: int | None,
        agent_config_id: int | None,
        user_query: str = "",
    ) -> Conversation:
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ).first()
            if not conversation:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="对话不存在",
                )
            return conversation

        # 创建新对话：标题默认取首条用户问题（截断至列宽上限）
        def _default_title() -> str:
            t = (user_query or "").strip().replace("\n", " ")
            if t:
                return t[:128]
            return "文件分析" if datasource_type in {"file", "excel", "csv"} else "数据查询"

        # 创建新对话
        conversation = Conversation(
            title=_default_title(),
            user_id=user_id,
            data_source_type=datasource_type or "chat",
            db_connection_id=db_connection_id if datasource_type == "db" else None,
            file_upload_id=file_upload_id,
            agent_config_id=agent_config_id,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def _sync_request_datasource(
        self,
        db: Session,
        conversation: Conversation,
        datasource_type: str,
        db_connection_id: int | None,
        file_upload_id: int | None,
        user,
    ) -> None:
        """将请求中显式指定的数据源同步到会话（覆盖旧绑定）。"""
        from services.resource_access import get_datasource_permission

        dst = (datasource_type or "chat").lower()
        if dst == "chat":
            return

        changed = False
        if dst == "db" and db_connection_id:
            if not get_datasource_permission(db, user, "db_connection", db_connection_id):
                return
            if (
                conversation.data_source_type != "db"
                or conversation.db_connection_id != db_connection_id
            ):
                conversation.data_source_type = "db"
                conversation.db_connection_id = db_connection_id
                conversation.file_upload_id = None
                changed = True
        elif dst in ("excel", "csv", "file") and file_upload_id:
            normalized = "excel" if dst == "file" else dst
            if not get_datasource_permission(db, user, "file_upload", file_upload_id):
                return
            if (
                conversation.data_source_type != normalized
                or conversation.file_upload_id != file_upload_id
            ):
                conversation.data_source_type = normalized
                conversation.file_upload_id = file_upload_id
                conversation.db_connection_id = None
                changed = True

        if changed:
            db.commit()
            db.refresh(conversation)

    def _default_sqlite_connection_id(self, db: Session) -> int | None:
        from models.db_connection import DbConnection

        base_query = db.query(DbConnection).filter(
            DbConnection.db_type == "sqlite",
            DbConnection.is_active == True,  # noqa: E712
        )
        conn = base_query.filter(DbConnection.name == "示例 SQLite（演示订单库）").first()
        if not conn:
            conn = base_query.filter(DbConnection.db_path.like("%demo_business.sqlite%")).first()
        if not conn:
            conn = base_query.order_by(DbConnection.id).first()
        return conn.id if conn else None

    def _ensure_data_source_for_query(self, db: Session, conversation: Conversation) -> None:
        """问数分支需要数据源；未绑定时沿用旧逻辑自动选择第一个 SQLite。"""
        if conversation.db_connection_id or conversation.file_upload_id:
            return
        conversation.db_connection_id = self._default_sqlite_connection_id(db)
        if conversation.db_connection_id:
            conversation.data_source_type = "db"
            db.commit()
            db.refresh(conversation)

    async def _recognize_intent(
        self,
        user_query: str,
        history: list[dict],
        llm_service: LLMService,
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> str:
        """使用模型识别 ask_data / other；模型输出异常时用保守规则兜底。"""
        from prompts.intent_v1 import INTENT_SYSTEM_PROMPT
        messages = [{"role": "system", "content": system_prompt or INTENT_SYSTEM_PROMPT}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": user_query})

        try:
            raw = await llm_service.chat_once(
                messages, temperature=temperature, max_tokens=max_tokens,
            )
            intent = self._parse_intent(raw)
            if intent:
                return intent
        except Exception:
            pass
        return self._fallback_intent(user_query)

    def _parse_intent(self, raw: str) -> str | None:
        text = (raw or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
            intent = parsed.get("intent")
            if intent in {"ask_data", "other"}:
                return intent
        except Exception:
            pass
        lowered = text.lower()
        if "ask_data" in lowered:
            return "ask_data"
        if "other" in lowered:
            return "other"
        return None

    def _fallback_intent(self, user_query: str) -> str:
        """兜底只在模型分类输出不可用时启用，避免阻断问数主流程。"""
        q = user_query.lower()
        data_keywords = {
            "数据", "数据源", "查询", "统计", "分析", "趋势", "分布", "排名", "报表",
            "表", "字段", "订单", "销售", "金额", "收入", "用户", "客户", "商品",
            "多少", "总数", "数量", "平均", "最大", "最小", "同比", "环比", "占比",
            "明细", "筛选", "近", "每天", "每月", "每年",
        }
        return "ask_data" if any(keyword in q for keyword in data_keywords) else "other"

    def _resolve_schema_target(
        self,
        conversation: Conversation,
        agent: AgentConfig,
    ) -> tuple[str | None, int | None, int | None]:
        """
        解析问数 Schema 来源：优先智能体默认数据源，否则使用会话已绑定数据源。
        返回 (data_source_type, db_connection_id, file_upload_id)。
        """
        agent_dst = (agent.default_data_source_type or "").lower()
        if agent_dst == "db" and agent.default_db_connection_id:
            return "db", agent.default_db_connection_id, None
        if agent_dst in ("excel", "csv") and agent.default_file_upload_id:
            return agent_dst, None, agent.default_file_upload_id

        dst = (conversation.data_source_type or "").lower()
        if dst in ("excel", "csv") and conversation.file_upload_id:
            return dst, None, conversation.file_upload_id
        if conversation.db_connection_id:
            return "db", conversation.db_connection_id, None
        if conversation.file_upload_id:
            return dst or "excel", None, conversation.file_upload_id
        return None, None, None

    async def _load_schema(
        self,
        db: Session,
        conversation: Conversation,
        agent: AgentConfig,
    ) -> list[dict]:
        """加载智能体目标数据源中的全量表 Schema。"""
        dst, db_conn_id, file_id = self._resolve_schema_target(conversation, agent)

        if dst in ("excel", "csv") and file_id:
            return self._load_file_schema(db, file_id)

        if dst == "db" and db_conn_id:
            from models.db_connection import DbConnection
            from services.schema_sync import SchemaSync

            conn = db.query(DbConnection).filter(DbConnection.id == db_conn_id).first()
            if conn:
                return SchemaSync().sync_and_cache(conn, db)

        return []

    def _load_file_schema(self, db: Session, file_upload_id: int) -> list[dict]:
        """加载文件数据源全部 Sheet/表的 Schema。"""
        from models.file_upload import FileUpload
        from models.file_sheet import FileSheet

        upload = db.query(FileUpload).filter(FileUpload.id == file_upload_id).first()
        if not upload:
            return []

        if upload.schema_cache:
            try:
                schema = json.loads(upload.schema_cache)
                if isinstance(schema, list) and schema:
                    return schema
            except json.JSONDecodeError:
                pass

        sheets = db.query(FileSheet).filter(
            FileSheet.file_upload_id == file_upload_id,
        ).order_by(FileSheet.id).all()
        schema: list[dict] = []
        for sheet in sheets:
            columns = []
            if sheet.columns_schema:
                try:
                    columns = json.loads(sheet.columns_schema)
                except json.JSONDecodeError:
                    pass
            schema.append({
                "sheet_name": sheet.sheet_name,
                "table_name": sheet.table_name,
                "columns": columns,
            })
        return schema

    async def _load_history(self, db: Session, conversation_id: int) -> list[dict]:
        """加载对话历史消息"""
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id,
        ).order_by(Message.created_at.desc()).limit(20).all()

        history = []
        for msg in reversed(messages):
            history.append({"role": msg.role, "content": msg.content})
        return history

    # ── 步骤 3: LLM 调用（流式 + 重试）──

    async def _call_llm_with_retry(
        self,
        messages: list[dict],
        llm_service: LLMService,
        max_retries: int = 3,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """LLM 调用 + 指数退避重试"""
        for attempt in range(max_retries):
            try:
                async for token in llm_service.chat_stream(
                    messages, temperature=temperature, max_tokens=max_tokens,
                ):
                    yield ChatStreamEvent(event="token", data={"text": token})
                return
            except (TimeoutError, asyncio.TimeoutError):
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise BusinessError(
                    code=ErrorCode.LLM_CALL_FAILED,
                    message="LLM 服务暂时不可用，请稍后再试",
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise BusinessError(
                    code=ErrorCode.LLM_CALL_FAILED,
                    message=f"LLM 调用失败: {str(e)}",
                )

    # ── 步骤 4: SQL 校验（含重试）──

    async def _validate_sql_with_retry(
        self,
        sql: str,
        messages: list[dict],
        llm_service: LLMService,
        user_prompt_template: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int = 2,
    ) -> str:
        """SQL 校验失败时回传 LLM 修正"""
        from prompts.workflow_defaults import SQL_FIX_USER_PROMPT_TEMPLATE
        fix_template = user_prompt_template or SQL_FIX_USER_PROMPT_TEMPLATE
        for attempt in range(max_retries):
            is_valid, error_msg = self.sql_validator.validate(sql)
            if is_valid:
                return self.sql_validator.apply_limit(sql)

            if attempt < max_retries - 1:
                messages.append({"role": "assistant", "content": sql})
                fix_prompt = fix_template.replace("{error_msg}", error_msg or "")
                messages.append({"role": "user", "content": fix_prompt})
                try:
                    sql = await llm_service.chat_once(
                        messages, temperature=temperature, max_tokens=max_tokens,
                    )
                except Exception:
                    raise BusinessError(
                        code=ErrorCode.SQL_EXECUTION_ERROR,
                        message="SQL 修正失败",
                        detail=error_msg,
                    )
            else:
                raise BusinessError(
                    code=ErrorCode.SQL_EXECUTION_ERROR,
                    message="SQL 校验失败",
                    detail=error_msg,
                )
        return sql

    # ── 步骤 5: SQL 执行（含重试）──

    async def _execute_sql_with_retry(
        self, db: Session, sql: str, conversation: Conversation, max_retries: int = 2,
    ) -> dict:
        """SQL 执行 + 异常时重试"""
        # 获取数据源路径
        db_path = self._get_db_path(db, conversation)

        for attempt in range(max_retries):
            try:
                result = self.sql_executor.execute(sql, db_path)
                return result
            except BusinessError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise
        return {"columns": [], "rows": [], "total_rows": 0}

    def _get_db_path(self, db: Session, conversation: Conversation) -> str | None:
        """获取对话绑定的数据库路径"""
        if conversation.file_upload_id:
            from models.file_upload import FileUpload
            upload = db.query(FileUpload).filter(FileUpload.id == conversation.file_upload_id).first()
            if not upload or not upload.query_db_path:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="文件数据源未就绪，请重新上传或等待解析完成",
                )
            return upload.query_db_path

        if conversation.db_connection_id:
            from models.db_connection import DbConnection
            conn = db.query(DbConnection).filter(DbConnection.id == conversation.db_connection_id).first()
            if not conn:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="数据库连接不存在",
                )
            if conn.db_type != "sqlite":
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="MVP 当前仅支持 SQLite 数据源查询",
                )
            if not conn.db_path:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="SQLite 数据源未配置 db_path",
                )
            return conn.db_path
        from models.db_connection import DbConnection
        fallback_id = self._default_sqlite_connection_id(db)
        fallback = db.query(DbConnection).filter(DbConnection.id == fallback_id).first() if fallback_id else None
        if fallback and fallback.db_path:
            return fallback.db_path
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message="未绑定有效的数据源：请指定数据库连接或已解析的文件数据源",
        )

    # ── 步骤 6: 生成自然语言总结 ──

    async def _generate_summary(
        self,
        result: dict,
        user_query: str,
        sql: str,
        streamer: SSEStreamer,
        llm_service: LLMService,
        system_prompt: str = "",
        user_prompt_template: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """使用 LLM 对查询结果生成自然语言总结"""
        from prompts.workflow_defaults import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
        try:
            rows = result.get("rows", [])
            columns = result.get("columns", [])

            if not rows:
                text = "查询未返回数据。"
                await streamer.send(ChatStreamEvent(
                    event="token",
                    data={"text": text},
                ))
                return text

            template = user_prompt_template or SUMMARY_USER_PROMPT_TEMPLATE
            summary_prompt = template.format(
                user_query=user_query,
                sql=sql,
                row_count=len(rows),
                columns=", ".join(columns),
                sample_rows=json.dumps(rows[:5], ensure_ascii=False),
            )

            summary_messages = [
                {"role": "system", "content": system_prompt or SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": summary_prompt},
            ]

            chunks: list[str] = []
            async for token in llm_service.chat_stream(
                summary_messages, temperature=temperature, max_tokens=max_tokens,
            ):
                chunks.append(token)
                await streamer.send(ChatStreamEvent(event="token", data={"text": token}))
            return "".join(chunks).strip() or f"查询完成，返回 {len(rows)} 行数据。"
        except Exception:
            # 总结失败不打断主流程
            return f"查询完成，返回 {len((result or {}).get('rows', []))} 行数据。"

    async def _generate_direct_reply(
        self,
        user_query: str,
        history: list[dict],
        streamer: SSEStreamer,
        llm_service: LLMService,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """其他意图：不加载数据源，直接基于历史上下文调用模型回复。"""
        from prompts.workflow_defaults import DIRECT_REPLY_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt or DIRECT_REPLY_SYSTEM_PROMPT},
        ]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_query})

        chunks: list[str] = []
        async for token in llm_service.chat_stream(
            messages, temperature=temperature, max_tokens=max_tokens,
        ):
            chunks.append(token)
            await streamer.send(ChatStreamEvent(event="token", data={"text": token}))
        text = "".join(chunks).strip()
        if not text:
            text = "我暂时无法生成回复，请稍后再试。"
            await streamer.send(ChatStreamEvent(event="token", data={"text": text}))
        return text

    # ── 步骤 7: 图表 SSE 载荷（对齐 ChatBI-API-Spec）──

    def _build_chart_sse_payload(self, result: dict) -> dict | None:
        """根据查询结果返回多类型图表载荷（含 available_types / options）。"""
        payload = recommend_chart(result)
        if not has_visual_chart(payload):
            return payload if payload.get("available_types") else None
        return payload

    def _analyze_chart_type(self, result: dict) -> dict:
        """Backward-compatible chart helper used by tests and older callers."""
        return recommend_chart(result)

    # ── 步骤 8: 持久化 & 完成 ──

    async def _save_conversation(
        self,
        db: Session,
        conversation: Conversation,
        user_id: int,
        user_query: str,
        sql_text: str,
        result: dict | None,
        summary_text: str,
        chart_payload: dict | None,
    ) -> int | None:
        """保存对话记录和查询日志，返回助手消息 id（供 SSE done 事件）。"""
        try:
            # 保存用户消息
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=user_query,
            )
            db.add(user_msg)

            # 保存助手消息
            metadata = {
                "intent": "ask_data",
                "sql": sql_text,
                "table_data": {
                    "columns": (result or {}).get("columns", []),
                    "rows": self._rows_to_objects(result or {}),
                },
                "chart_data": chart_payload,
                "chart_type": (
                    chart_payload.get("default_type") or chart_payload.get("type")
                    if chart_payload else None
                ),
                "row_count": (result or {}).get("total_rows", 0),
            }
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=summary_text or f"查询完成，返回 {metadata['row_count']} 行数据",
                metadata_json=metadata,
            )
            db.add(assistant_msg)
            db.flush()

            # 记录查询日志
            log = QueryLog(
                user_id=user_id,
                conversation_id=conversation.id,
                user_query=user_query,
                generated_sql=sql_text,
                execution_time_ms=(result or {}).get("execution_time_ms", 0),
                row_count=(result or {}).get("total_rows", 0),
                status="success" if result else "error",
            )
            db.add(log)

            db.commit()
            return assistant_msg.id
        except Exception:
            db.rollback()
        return None

    async def _save_direct_reply(
        self,
        db: Session,
        conversation: Conversation,
        user_query: str,
        reply_text: str,
    ) -> int | None:
        """保存普通聊天分支，不写 QueryLog。"""
        try:
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=user_query,
            )
            db.add(user_msg)

            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=reply_text,
                metadata_json={"intent": "other"},
            )
            db.add(assistant_msg)
            db.flush()
            db.commit()
            return assistant_msg.id
        except Exception:
            db.rollback()
        return None

    def _rows_to_objects(self, result: dict) -> list[dict]:
        columns = result.get("columns", []) or []
        rows = result.get("rows", []) or []
        out: list[dict] = []
        for row in rows:
            if isinstance(row, dict):
                out.append(row)
                continue
            if isinstance(row, (list, tuple)):
                out.append({col: row[i] if i < len(row) else None for i, col in enumerate(columns)})
        return out
