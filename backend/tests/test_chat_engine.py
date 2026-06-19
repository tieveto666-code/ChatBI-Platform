"""
测试聊天引擎 — MockLLMProvider 下的 NL2SQL 管线

测试场景：
- 正常流程：question → SQL → validate → execute → summary → chart
- 超时重试：LLM 超时后自动重试
- 校验失败重试：SQL 校验失败后回传 LLM 修正
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.chat_engine import ChatEngine
from services.sql_validator import SQLValidator
from services.sql_executor import SQLExecutor
from services.llm_service import LLMService
from core.exceptions import BusinessError


class TestChatEngineNormal:
    """正常 NL2SQL 管线测试"""

    @pytest.mark.asyncio
    async def test_process_message_creates_conversation(self, test_db):
        """应成功创建新对话并返回 streamer"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询所有用户",
            conversation_id=None,
            user_id=1,
            db=test_db,
        )
        events = streamer._events
        event_types = [e.event for e in events]

        # 应包含关键事件
        assert "token" in event_types
        assert "sql" in event_types
        assert "done" in event_types

        # 确认对话已创建
        from models.conversation import Conversation
        conv = test_db.query(Conversation).first()
        assert conv is not None
        assert conv.title == "查询所有用户"

    @pytest.mark.asyncio
    async def test_process_message_sql_generated(self, test_db):
        """应生成 SQL 并执行"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询所有用户",
            conversation_id=None,
            user_id=1,
            db=test_db,
        )

        sql_events = [e for e in streamer._events if e.event == "sql"]
        assert len(sql_events) > 0
        sql_data = sql_events[0].data
        assert "sql" in sql_data
        assert "SELECT" in sql_data["sql"].upper()

    @pytest.mark.asyncio
    async def test_process_message_with_existing_conversation(self, test_db):
        """使用已有 conversation_id 应正常处理"""
        from models.conversation import Conversation
        conv = Conversation(
            title="测试对话",
            user_id=1,
            data_source_type="database",
        )
        test_db.add(conv)
        test_db.commit()
        test_db.refresh(conv)

        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="统计用户数量",
            conversation_id=conv.id,
            user_id=1,
            db=test_db,
        )
        events = streamer._events
        assert any(e.event == "done" for e in events)

    @pytest.mark.asyncio
    async def test_chart_analysis(self, test_db):
        """适合可视化的查询应生成图表配置（非 table 类型）"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="统计每日活跃用户",
            conversation_id=None,
            user_id=1,
            db=test_db,
        )

        chart_events = [e for e in streamer._events if e.event == "chart"]
        assert len(chart_events) > 0
        chart_data = chart_events[0].data
        assert "available_types" in chart_data
        assert len(chart_data["available_types"]) >= 2
        assert chart_data.get("options")
        visual = [t for t in chart_data["available_types"] if t != "table"]
        assert len(visual) >= 1

    @pytest.mark.asyncio
    async def test_table_result(self, test_db):
        """应返回表格数据"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询所有用户",
            conversation_id=None,
            user_id=1,
            db=test_db,
        )

        table_events = [e for e in streamer._events if e.event == "table"]
        assert len(table_events) > 0

    @pytest.mark.asyncio
    async def test_other_intent_direct_reply_without_sql(self, test_db):
        """其他意图应直接回复，不生成 SQL/表格/图表事件。"""
        from models.message import Message
        from models.query_log import QueryLog

        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="你好，介绍一下你自己",
            conversation_id=None,
            user_id=1,
            db=test_db,
            datasource_type="chat",
        )

        event_types = [e.event for e in streamer._events]
        assert "token" in event_types
        assert "done" in event_types
        assert "sql" not in event_types
        assert "table" not in event_types
        assert "chart" not in event_types
        assert test_db.query(Message).filter(Message.role == "assistant").count() == 1
        assert test_db.query(QueryLog).count() == 0

    @pytest.mark.asyncio
    async def test_data_intent_keeps_nl2sql_pipeline(self, test_db):
        """问数意图仍走现有 NL2SQL 流程。"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="统计用户数量",
            conversation_id=None,
            user_id=1,
            db=test_db,
            datasource_type="db",
        )

        event_types = [e.event for e in streamer._events]
        assert "sql" in event_types
        assert "table" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_data_intent_uses_agent_default_datasource(self, test_db):
        """问数意图未显式选源时，使用系统内置智能体的默认数据源。"""
        from models.conversation import Conversation

        engine = ChatEngine()
        await engine.process_message(
            user_query="统计用户数量",
            conversation_id=None,
            user_id=1,
            db=test_db,
            datasource_type="chat",
        )

        conv = test_db.query(Conversation).order_by(Conversation.id.desc()).first()
        assert conv.agent_config_id == 1
        assert conv.db_connection_id == 1


class TestChatEngineSchemaLoad:
    """Schema 加载：智能体目标库全量表"""

    @pytest.mark.asyncio
    async def test_load_schema_full_tables_from_agent_db(self, test_db):
        """智能体绑定数据库时，应同步目标库全量表 Schema。"""
        from models.conversation import Conversation
        from models.agent_config import AgentConfig
        from services.schema_sync import SchemaSync
        from models.db_connection import DbConnection

        agent = test_db.query(AgentConfig).filter(AgentConfig.id == 1).first()
        agent.default_data_source_type = "db"
        agent.default_db_connection_id = 1
        test_db.commit()

        conn = test_db.query(DbConnection).filter(DbConnection.id == 1).one()
        full_schema = SchemaSync().sync_and_cache(conn, test_db)
        full_names = {t["table_name"] for t in full_schema}
        assert len(full_names) >= 2, "演示库应包含多张表"

        conv = Conversation(
            title="schema test",
            user_id=1,
            data_source_type="db",
            db_connection_id=1,
            agent_config_id=1,
        )
        test_db.add(conv)
        test_db.commit()
        test_db.refresh(conv)

        engine = ChatEngine()
        schema = await engine._load_schema(test_db, conv, agent)
        loaded_names = {t["table_name"] for t in schema}
        assert loaded_names == full_names


class TestChatEngineRetry:
    """超时重试测试"""

    @pytest.mark.asyncio
    async def test_llm_timeout_retry(self, test_db):
        """LLM 超时应自动重试并最终成功"""
        with patch("services.chat_engine.ChatEngine._call_llm_with_retry") as mock_call:
            # 模拟正常返回
            async def mock_stream(messages):
                from schemas.chat import ChatStreamEvent
                yield ChatStreamEvent(event="token", data={"text": "SELECT * FROM users"})

            mock_call.return_value = mock_stream([])

            engine = ChatEngine()
            streamer = await engine.process_message(
                user_query="查询所有用户",
                conversation_id=None,
                user_id=1,
                db=test_db,
            )
            events = streamer._events
            assert any(e.event == "done" for e in events)

    @pytest.mark.asyncio
    async def test_sql_validation_retry(self, test_db):
        """SQL 校验失败应回传 LLM 修正"""
        engine = ChatEngine()

        # Mock SQL validator 第一次失败，第二次成功
        original_validate = SQLValidator.validate
        call_count = [0]

        def mock_validate(self, sql):
            call_count[0] += 1
            if call_count[0] <= 1:
                return False, "包含禁止的关键词: DROP"
            return True, ""

        with patch.object(SQLValidator, "validate", mock_validate):
            with patch.object(LLMService, "chat_once", new=AsyncMock(return_value="SELECT 1 AS result")):
                streamer = await engine.process_message(
                    user_query="查询所有用户",
                    conversation_id=None,
                    user_id=1,
                    db=test_db,
                )
                events = streamer._events
                assert any(e.event == "done" for e in events)
                assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_sql_execution_retry(self, test_db):
        """SQL 执行失败自动重试"""
        engine = ChatEngine()

        original_execute = SQLExecutor.execute
        exec_count = [0]

        def mock_execute(sql, db_path=None, max_rows=None):
            exec_count[0] += 1
            if exec_count[0] <= 1:
                raise BusinessError(code=3001, message="SQL 执行失败", detail="模拟错误")
            return {"columns": ["id"], "rows": [[1]], "total_rows": 1, "execution_time_ms": 0}

        with patch.object(SQLExecutor, "execute", mock_execute):
            streamer = await engine.process_message(
                user_query="查询所有用户",
                conversation_id=None,
                user_id=1,
                db=test_db,
            )
            events = streamer._events
            assert any(e.event == "done" for e in events)
            assert exec_count[0] >= 2


class TestChatEngineError:
    """异常处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_conversation(self, test_db):
        """使用不存在的 conversation_id 应错误处理"""
        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询所有用户",
            conversation_id=9999,
            user_id=1,
            db=test_db,
        )
        events = streamer._events
        error_events = [e for e in events if e.event == "error"]
        assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_empty_sql_from_llm(self, test_db):
        """LLM 返回空 SQL"""
        with patch.object(LLMService, "chat_stream") as mock_stream:
            async def empty_stream(messages):
                from schemas.chat import ChatStreamEvent
                yield ChatStreamEvent(event="token", data={"text": ""})

            mock_stream.return_value = empty_stream([])

            engine = ChatEngine()
            streamer = await engine.process_message(
                user_query="测试空SQL",
                conversation_id=None,
                user_id=1,
                db=test_db,
            )
            events = streamer._events
            assert any(e.event == "error" for e in events)


class TestChatEngineExcelIntegration:
    """Excel/CSV 文件上传后 NL2SQL 查询集成测试"""

    @pytest.mark.asyncio
    async def test_excel_file_upload_then_query(self, test_db, tmp_path):
        """上传 CSV → 构建 query db → 自然语言提问 → 返回 SQL 与表格结果"""
        from tests.helpers.excel_fixtures import create_file_upload_from_csv

        upload, schema_cache = create_file_upload_from_csv(test_db, tmp_path)
        table_name = schema_cache[0]["table_name"]
        assert table_name == "sales_data"

        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询销售额最高的前5个商品",
            conversation_id=None,
            user_id=1,
            db=test_db,
            datasource_type="excel",
            file_upload_id=upload.id,
        )

        event_types = [e.event for e in streamer._events]
        assert "sql" in event_types
        assert "table" in event_types
        assert "done" in event_types
        assert "error" not in event_types

        sql_events = [e for e in streamer._events if e.event == "sql"]
        assert table_name in sql_events[0].data.get("sql", "")

        table_events = [e for e in streamer._events if e.event == "table"]
        rows = table_events[0].data.get("rows", [])
        assert len(rows) == 5

        from models.conversation import Conversation
        conv = test_db.query(Conversation).order_by(Conversation.id.desc()).first()
        assert conv.file_upload_id == upload.id
        assert conv.data_source_type == "excel"

    @pytest.mark.asyncio
    async def test_agent_excel_default_overrides_stale_db_binding(self, test_db, tmp_path):
        """智能体绑定 Excel 后，应覆盖会话中残留的数据库数据源。"""
        from models.agent_config import AgentConfig
        from models.conversation import Conversation
        from models.role_datasource import RoleDatasource
        from tests.helpers.excel_fixtures import create_file_upload_from_csv

        upload, schema_cache = create_file_upload_from_csv(test_db, tmp_path)
        test_db.add(RoleDatasource(
            role_id=1,
            resource_type="file_upload",
            resource_id=upload.id,
            permission="use",
        ))
        agent = test_db.query(AgentConfig).filter(AgentConfig.id == 1).first()
        agent.default_data_source_type = "excel"
        agent.default_file_upload_id = upload.id
        test_db.commit()

        conv = Conversation(
            title="旧对话",
            user_id=1,
            data_source_type="db",
            db_connection_id=1,
            agent_config_id=1,
        )
        test_db.add(conv)
        test_db.commit()
        test_db.refresh(conv)

        engine = ChatEngine()
        streamer = await engine.process_message(
            user_query="查询销售额最高的前5个商品",
            conversation_id=conv.id,
            user_id=1,
            db=test_db,
            datasource_type="chat",
        )

        assert "error" not in [e.event for e in streamer._events]
        test_db.refresh(conv)
        assert conv.file_upload_id == upload.id
        assert conv.db_connection_id is None
        assert conv.data_source_type == "excel"
        table_name = schema_cache[0]["table_name"]
        sql_events = [e for e in streamer._events if e.event == "sql"]
        assert table_name in sql_events[0].data.get("sql", "")


class TestChatEngineChartAnalysis:
    """图表类型分析测试"""

    def test_time_series_chart(self):
        """时间序列数据应包含折线图等多种类型"""
        engine = ChatEngine()
        result = {"columns": ["date", "count"], "rows": [["2024-01-01", 10], ["2024-01-02", 20]]}
        chart = engine._analyze_chart_type(result)
        assert "line" in chart["available_types"]
        assert chart["default_type"] == "line"

    def test_category_bar_chart(self):
        """分类 + 数值应包含柱状图等多种类型"""
        engine = ChatEngine()
        result = {"columns": ["category", "value"], "rows": [["A", 30], ["B", 50], ["C", 20]]}
        chart = engine._analyze_chart_type(result)
        assert "bar" in chart["available_types"]
        assert chart["default_type"] == "bar"

    def test_bar_line_chart(self):
        """分类 + 两个数值指标应包含柱线复合图"""
        engine = ChatEngine()
        result = {
            "columns": ["month", "sales", "profit"],
            "rows": [["Jan", 100, 10], ["Feb", 150, 18]],
        }
        chart = engine._analyze_chart_type(result)
        assert "bar_line" in chart["available_types"]
        assert chart["default_type"] == "bar_line"

    def test_text_heavy_table(self):
        """无有效数值列时仅返回表格"""
        engine = ChatEngine()
        result = {
            "columns": ["name", "grade"],
            "rows": [["Alice", "A"], ["Bob", "B"]],
        }
        chart = engine._analyze_chart_type(result)
        assert chart["available_types"] == ["table"]
        assert chart["default_type"] == "table"

    def test_empty_result_chart(self):
        """空结果返回 table 类型"""
        engine = ChatEngine()
        result = {"columns": [], "rows": [], "total_rows": 0}
        chart = engine._analyze_chart_type(result)
        assert chart["default_type"] == "table"
