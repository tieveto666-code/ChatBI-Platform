# ChatBI 后端架构设计

> **文档类型**：技术设计文档  
> **版本**：v0.4  
> **更新日期**：2026-05-10  
> **对应 PRD**：ChatBI-PRD.md v0.6

---

## 1. 项目目录结构

```
backend/
├── main.py                         # 应用入口，创建 FastAPI 实例
├── config.py                       # 配置管理（从 .env 读取）
├── .env.example                    # 环境变量模板
├── seed.py                         # 种子数据脚本（首次启动时运行）
│
├── routers/                        # API 路由层
│   ├── __init__.py
│   ├── auth.py                     # POST /auth/login, /auth/register 等
│   ├── chat.py                     # POST /chat/stream, 对话 CRUD
│   ├── datasources.py              # 数据源连接 + 文件上传 CRUD
│   ├── admin_users.py              # 用户管理 CRUD
│   ├── admin_roles.py              # 角色管理 CRUD
│   ├── admin_menus.py              # 菜单管理 CRUD
│   └── agents.py                   # 智能体配置 CRUD
│
├── models/                         # SQLAlchemy ORM 模型
│   ├── __init__.py
│   ├── base.py                     # Base 声明 + 通用 mixin
│   ├── user.py
│   ├── conversation.py
│   ├── message.py
│   ├── db_connection.py
│   ├── file_upload.py
│   ├── file_sheet.py
│   ├── role.py
│   ├── menu.py
│   ├── role_menu.py
│   ├── agent_config.py
│   └── query_log.py
│
├── schemas/                        # Pydantic 请求/响应模型
│   ├── __init__.py
│   ├── common.py                   # 统一响应信封 + 分页
│   ├── auth.py
│   ├── chat.py
│   ├── datasource.py
│   ├── admin.py
│   └── agent.py
│
├── services/                       # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py             # 认证 + JWT
│   ├── chat_engine.py              # NL2SQL 管线编排（核心）
│   ├── llm_service.py              # LLM Provider 封装
│   ├── sql_executor.py             # SQL 执行器
│   ├── sql_validator.py            # SQL 安全校验
│   ├── prompt_builder.py           # Prompt 构建
│   ├── sse_streamer.py             # SSE 流式响应引擎
│   ├── excel_parser.py             # Excel/CSV 解析
│   ├── schema_sync.py              # 数据源 Schema 同步
│   └── admin_service.py            # 用户/角色/菜单管理
│
├── llm/                            # LLM Provider 层
│   ├── __init__.py
│   ├── base.py                     # BaseLLMProvider 抽象接口
│   ├── factory.py                  # LLMProviderFactory
│   ├── deepseek_provider.py        # DeepSeek 实现
│   ├── ollama_provider.py          # Ollama 实现
│   └── mock_provider.py            # Mock 实现（开发/测试用）
│
├── middlewares/                    # 中间件
│   ├── __init__.py
│   └── auth_middleware.py          # JWT 鉴权中间件
│
├── core/                           # 核心工具
│   ├── __init__.py
│   ├── database.py                 # 数据库引擎 + Session 管理
│   ├── exceptions.py               # 自定义异常类
│   ├── error_codes.py              # 错误码枚举
│   └── dependencies.py             # FastAPI 依赖注入（get_db, get_current_user）
│
├── prompts/                        # Prompt 模板文件
│   ├── nl2sql_v1.py                # NL2SQL Prompt 模板（对应 PRD 附录 E）
│   └── summary_v1.py               # 结果总结 Prompt 模板
│
├── tests/                          # 测试
│   ├── conftest.py                 # 测试配置 + Fixtures
│   ├── test_auth.py
│   ├── test_chat_engine.py
│   ├── test_sql_validator.py
│   ├── test_excel_parser.py
│   └── test_admin.py
│
├── requirements.txt                # Python 依赖
└── pyproject.toml
```

---

## 2. 应用入口与启动

```python
# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
from routers import auth, chat, datasources, admin_users, admin_roles, admin_menus, agents
from config import settings

app = FastAPI(
    title="ChatBI API",
    description="基于大模型的对话式数据分析助手",
    version="0.4.0",
)

# ── CORS 配置 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api", tags=["对话"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["数据源"])
app.include_router(admin_users.router, prefix="/api/admin", tags=["用户管理"])
app.include_router(admin_roles.router, prefix="/api/admin", tags=["角色管理"])
app.include_router(admin_menus.router, prefix="/api/admin", tags=["菜单管理"])
app.include_router(agents.router, prefix="/api/agents", tags=["智能体配置"])


@app.on_event("startup")
async def startup():
    """应用启动时自动创建数据库表"""
    Base.metadata.create_all(bind=engine)
    # 注意：种子数据在首次部署时手动运行 seed.py


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

---

## 3. 配置管理

```python
# backend/config.py

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── 应用基础 ──
    APP_NAME: str = "ChatBI"
    DEBUG: bool = True
    
    # ── 数据库 ──
    DATABASE_URL: str = "sqlite:///./data/chatbi.db"
    
    # ── LLM 配置 ──
    LLM_PROVIDER: str = "mock"                     # deepseek / ollama / mock
    DEEPSEEK_API_KEY: str = "YOUR_API_KEY_HERE"
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    
    # ── Mock 配置（开发环境）──
    MOCK_LLM_FAULT_MODE: str = "none"              # none / timeout / syntax_error / non_sql
    MOCK_LLM_FAULT_DELAY: int = 0
    
    # ── JWT 认证 ──
    JWT_SECRET: str = "change-this-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_IN: int = 86400                     # 24 小时（秒）
    
    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # ── 文件上传 ──
    UPLOAD_DIR: str = "./data/uploads"
    FILE_DB_DIR: str = "./data/file_dbs"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024           # 20MB
    MAX_SHEET_COUNT: int = 50
    MAX_COLUMN_COUNT: int = 200
    MAX_TOTAL_ROWS: int = 1_000_000
    PARSE_MEMORY_LIMIT_BYTES: int = 500 * 1024 * 1024    # 500MB
    
    # ── SQL 安全 ──
    SQL_MAX_RESULT_ROWS: int = 10000
    SQL_ENABLE_QUERY_ONLY: bool = True
    
    # ── 日志 ──
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/chatbi.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

---

## 4. ORM 模型示例

```python
# backend/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """通用时间戳 Mixin"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
```

```python
# backend/models/user.py
from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关系
    role = relationship("Role", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")
```

其他 10 个模型的模式同上（字段与 PRD 附录 D 的 DDL 一一对应），此处不再赘述。

---

## 5. 统一响应信封与错误处理

```python
# backend/core/exceptions.py

class ChatBIException(Exception):
    """业务异常基类"""
    def __init__(self, code: int, message: str, detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail

class AuthError(ChatBIException):
    """1000-1999: 认证错误"""
    pass

class ValidationError(ChatBIException):
    """2000-2999: 参数错误"""
    pass

class BusinessError(ChatBIException):
    """3000-3999: 业务错误"""
    pass

class PermissionError(ChatBIException):
    """4000-4999: 权限错误"""
    pass

class SystemError(ChatBIException):
    """5000-5999: 系统错误"""
    pass
```

```python
# backend/core/error_codes.py
from enum import IntEnum

class ErrorCode(IntEnum):
    SUCCESS = 0
    
    # 认证错误 (1000-1999)
    TOKEN_EXPIRED = 1001
    INVALID_CREDENTIALS = 1002
    TOKEN_INVALID = 1003
    REGISTRATION_FAILED = 1004
    
    # 参数错误 (2000-2999)
    VALIDATION_ERROR = 2001
    MISSING_FIELD = 2002
    
    # 业务错误 (3000-3999)
    SQL_EXECUTION_ERROR = 3001
    LLM_CALL_FAILED = 3002
    FILE_TOO_LARGE = 3003
    FILE_PARSE_ERROR = 3004
    UNSUPPORTED_FILE_TYPE = 3005
    MEMORY_LIMIT_EXCEEDED = 3006
    
    # 权限错误 (4000-4999)
    FORBIDDEN = 4001
    INSUFFICIENT_PERMISSION = 4002
    
    # 系统错误 (5000-5999)
    INTERNAL_ERROR = 5001
    DATABASE_ERROR = 5002
```

```python
# backend/schemas/common.py
from pydantic import BaseModel
from typing import Any, Generic, TypeVar

DataT = TypeVar("DataT")

class ApiResponse(BaseModel, Generic[DataT]):
    """统一响应信封"""
    code: int = 0
    message: str = "success"
    data: DataT | None = None

class PaginatedData(BaseModel, Generic[DataT]):
    """分页数据结构"""
    items: list[DataT]
    total: int
    page: int = 1
    page_size: int = 20

class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: str | None = None
```

```python
# main.py 中的全局异常处理器
@app.exception_handler(ChatBIException)
async def chatbi_exception_handler(request, exc: ChatBIException):
    return JSONResponse(
        status_code=400 if exc.code < 5000 else 500,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
    )
```

---

## 6. Chat Engine 核心管线

### 6.1 完整执行流程图

```
用户 POST /api/chat/stream
         │
         ▼
  chat_engine.process_message()
         │
         ├── [1] 加载上下文
         │     ├─ 读取/创建 conversation
         │     ├─ 加载历史消息（最近 N 轮）
         │     └─ 读取数据源 Schema
         │
         ├── [2] 构建 Prompt
         │     ├─ PromptBuilder.build(schema, synonym, history, query)
         │     └─ 返回 messages 列表
         │
         ├── [3] 调用 LLM
         │     ├─ llm.chat(messages, stream=True)
         │     ├─ 流式接收 tokens → SSE: token 事件
         │     └─ 收集完整 SQL
         │     │
         │     ├── [3a] 失败?
         │     │     ├─ 超时 → 重试（最多 3 次，指数退避）
         │     │     └─ 全部失败 → SSE: error → 终止
         │
         ├── [4] SQL 安全校验
         │     ├─ SQLValidator.validate(sql)
         │     │     ├─ L1: sqlparse AST → 检查根节点
         │     │     ├─ L2: 表名白名单
         │     │     └─ L3: 禁止 DDL/DML 关键词
         │     ├─ SSE: sql 事件（展示 SQL）
         │     │
         │     ├── [4a] 校验失败?
         │     │     ├─ 回传 LLM 修正（最多 2 次）
         │     │     └─ 全部失败 → SSE: error → 终止
         │
         ├── [5] SQL 执行
         │     ├─ SQLExecutor.execute(sql, data_source)
         │     ├─ SSE: table 事件
         │     │
         │     ├── [5a] 执行失败?
         │     │     ├─ 回传 LLM 修正（最多 2 次）
         │     │     └─ 全部失败 → SSE: error → 终止
         │
         ├── [6] 生成总结
         │     ├─ LLM 第二次调用（结果→自然语言）
         │     ├─ SSE: token 事件（逐字输出）
         │     │
         │     ├── [6a] 失败?
         │     │     └─ 跳过总结，直接用表格展示
         │
         ├── [7] 图表渲染
         │     ├─ 分析数据特征（时间序列/分类/占比）
         │     ├─ SSE: chart 事件
         │     └─ 自动匹配图表类型
         │
         └── [8] 完成
               ├─ 保存 conversation + message 到数据库
               ├─ SSE: done 事件
               └─ 记录 query_log
```

### 6.2 ChatEngine 核心代码

```python
# backend/services/chat_engine.py

import asyncio
from datetime import datetime
from services.prompt_builder import PromptBuilder
from services.llm_service import LLMService
from services.sql_validator import SQLValidator
from services.sql_executor import SQLExecutor
from services.sse_streamer import SSEStreamer
from schemas.chat import ChatStreamEvent
from core.exceptions import BusinessError
from core.error_codes import ErrorCode


class ChatEngine:
    """NL2SQL 管线编排引擎 — 4 步工作流模式"""
    
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
    ) -> SSEStreamer:
        """
        处理用户消息，返回 SSE 流式响应。
        
        数据源信息通过 conversation 对象获取：
        1. 根据 conversation_id 从数据库加载 conversation
        2. 从 conversation 读取绑定的 data_source_type + db_connection_id / file_upload_id
        3. 从 db_connections 或 file_uploads 读取实际数据源配置
        4. 执行 NL2SQL 管线
        """
        streamer = SSEStreamer()
        
        try:
            # ── [1] 加载对话 & 数据源上下文 ──
            conversation = await self._load_conversation(conversation_id, user_id)
            schema = await self._load_schema(conversation)
            history = await self._load_history(conversation.id)
            
            # ── [2] 构建 Prompt ──
            messages = self.prompt_builder.build(
                user_query=user_query,
                schema=schema,
                conversation_history=history,
            )
            
            # ── [3] 调用 LLM（流式 + 重试）──
            sql_text = ""
            async for event in self._call_llm_with_retry(messages):
                if event.event == "token":
                    sql_text += event.data.get("text", "")
                await streamer.send(event)
            
            await streamer.send(ChatStreamEvent(event="sql", data={"sql": sql_text}))
            
            # ── [4] SQL 校验（含重试）──
            sql_text = await self._validate_sql_with_retry(sql_text, messages)
            
            # ── [5] SQL 执行（含重试）──
            result = await self._execute_sql_with_retry(sql_text, conversation)
            await streamer.send(ChatStreamEvent(event="table", data=result))
            
            # ── [6] 生成自然语言总结 ──
            await self._generate_summary(result, messages, streamer)
            
            # ── [7] 图表渲染 ──
            chart_data = self._analyze_chart_type(result)
            await streamer.send(ChatStreamEvent(event="chart", data=chart_data))
            
            # ── [8] 完成 ──
            await self._save_conversation(conversation, user_query, sql_text, result)
            await streamer.send(ChatStreamEvent(event="done", data={
                "conversation_id": conversation.id,
            }))
            
        except Exception as e:
            await streamer.send(ChatStreamEvent(
                event="error",
                data={"code": 5001, "message": str(e)}
            ))
        
        return streamer
    
    async def _call_llm_with_retry(self, messages, max_retries=3):
        """LLM 调用 + 指数退避重试"""
        for attempt in range(max_retries):
            try:
                async for event in self.llm_service.chat_stream(messages):
                    yield event
                return  # 成功则退出
            except TimeoutError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 1s → 2s → 4s
                    continue
                raise BusinessError(
                    code=ErrorCode.LLM_CALL_FAILED,
                    message="LLM 服务暂时不可用，请稍后再试"
                )
    
    async def _validate_sql_with_retry(self, sql: str, messages, max_retries=2):
        """SQL 校验失败时回传 LLM 修正"""
        for attempt in range(max_retries):
            is_valid, error_msg = self.sql_validator.validate(sql)
            if is_valid:
                return sql
            
            if attempt < max_retries - 1:
                # 将错误信息回传 LLM，请求修正
                messages.append({"role": "assistant", "content": sql})
                messages.append({
                    "role": "user",
                    "content": f"生成的 SQL 有误: {error_msg}，请修正后重新输出"
                })
                sql = await self.llm_service.chat_once(messages)
            else:
                raise BusinessError(
                    code=ErrorCode.SQL_EXECUTION_ERROR,
                    message="SQL 校验失败",
                    detail=error_msg
                )
        return sql
    
    def _analyze_chart_type(self, result: dict) -> dict:
        """根据数据特征自动选择图表类型"""
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        
        if not rows:
            return {"type": "table", "data": result}
        
        # 时间序列 → 折线图
        if any("date" in col.lower() or "time" in col.lower() for col in columns):
            return {"type": "line", "data": result, "config": {"x_label": columns[0]}}
        
        # 占比数据 → 饼图（只有一列数值 + 一列分类时）
        if len(columns) == 2 and len(rows) <= 10:
            return {"type": "pie", "data": result}
        
        # 默认 → 柱状图
        return {"type": "bar", "data": result, "config": {"x_label": columns[0]}}
```

---

## 7. 数据库初始化与种子数据

### 自动建表流程

```python
# backend/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 多线程
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """首次启动时自动创建所有表（替代 Alembic MVP 方案）"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖注入：获取数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 架构说明

- **MVP 不引入 Alembic**：使用 `Base.metadata.create_all()` 在应用启动时自动建表
- **表结构变更**：直接修改 ORM 模型 + 手动执行 `Base.metadata.create_all()`（SQLite 的 `CREATE TABLE IF NOT EXISTS` 幂等）
- **PostgreSQL 升迁时**：再引入 Alembic 管理正式迁移

---

## 8. JWT 鉴权中间件

```python
# backend/middlewares/auth_middleware.py

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import settings
from core.exceptions import AuthError
from core.error_codes import ErrorCode

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT Token 解析当前用户"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError(code=ErrorCode.TOKEN_INVALID, message="Token 无效")
    except JWTError:
        raise AuthError(code=ErrorCode.TOKEN_EXPIRED, message="Token 已过期")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise AuthError(code=ErrorCode.TOKEN_INVALID, message="用户不存在")
    if not user.is_active:
        raise AuthError(code=ErrorCode.FORBIDDEN, message="用户已被禁用")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin 权限守卫"""
    role = current_user.role
    if role.code != "admin":
        raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="需要管理员权限")
    return current_user
```

---

## 9. SQL 安全校验器

```python
# backend/services/sql_validator.py

import sqlparse
from typing import Tuple


class SQLValidator:
    """
    SQL 安全校验器 — 4 层防护。
    基于 sqlparse AST 解析，替代简单的正则匹配。
    """
    
    # 禁止的 DDL/DML 关键词
    FORBIDDEN_KEYWORDS = {
        "DROP", "ALTER", "TRUNCATE", "CREATE",
        "INSERT", "UPDATE", "DELETE", "REPLACE",
        "GRANT", "REVOKE", "ATTACH", "DETACH",
        "PRAGMA",
    }
    
    def validate(self, sql: str) -> Tuple[bool, str]:
        """
        校验 SQL 安全性。
        Returns: (is_valid, error_message)
        """
        # L0: 空检查
        if not sql or not sql.strip():
            return False, "SQL 为空"
        
        try:
            parsed = sqlparse.parse(sql)
        except Exception:
            return False, "SQL 语法解析失败"
        
        if not parsed:
            return False, "SQL 无法解析"
        
        for statement in parsed:
            # L1: 检查根是否为 SELECT
            if statement.get_type() != "SELECT":
                return False, f"禁止的非 SELECT 语句: {statement.get_type()}"
            
            # L2: 检查是否含 DDL/DML 关键词
            for token in statement.flatten():
                if token.ttype is sqlparse.tokens.Keyword.DDL or \
                   token.ttype is sqlparse.tokens.Keyword.DML:
                    if token.value.upper() in self.FORBIDDEN_KEYWORDS:
                        return False, f"包含禁止的关键词: {token.value}"
        
        return True, ""
    
    def apply_limit(self, sql: str, max_rows: int = 10000) -> str:
        """强制追加 LIMIT 子句（L4 防护）"""
        sql = sql.strip().rstrip(";").strip()
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {max_rows}"
        return sql
```

---

## 10. Excel/CSV 文件查询库说明

### 10.1 数据流向

```
用户上传 Excel/CSV
                       │
                       ▼
文件校验（类型/大小/编码）→ 保存原始文件到 data/uploads/
                       │
                       ▼
ExcelParser 解析多 Sheet / CSV
                       │
                       ▼
创建 data/file_dbs/{file_upload_id}.sqlite
          → 每个 Sheet 创建一张表
          → 批量写入数据
          → 写入 file_uploads / file_sheets 元数据（含 Schema 缓存、原始名称映射、query_db_path）
                       │
                       ▼
用户创建对话（绑定 file_upload_id） → 对话开始
                       │
                       ▼
提问时 → ChatEngine 根据 conversation.file_upload_id 读取 file_uploads.query_db_path
          → PromptBuilder 注入 file_sheets 的 Schema
          → SQLExecutor 以只读连接查询文件查询库
                       │
                       ▼
删除上传文件 → 删除原始文件 + 文件查询库 + file_sheets 元数据
```

### 10.2 关键设计

| 要点 | 说明 |
|------|------|
| **文件查询库** | 每个上传文件生成一个 SQLite 查询库，路径写入 `file_uploads.query_db_path`；这保证历史 Excel 文件可复用 |
| **Schema 来源** | NL2SQL Prompt 使用 `file_sheets.columns_schema` 和 `file_uploads.schema_cache`，不在提问时重新解析原文件 |
| **执行路径** | `SQLExecutor.execute(sql, db_path=file_upload.query_db_path, readonly=True)`，与普通 SQLite 数据源复用同一执行器 |
| **名称清洗** | 表名、列名必须转换为 SQLite 安全标识符；原始 Sheet/列名保留在映射 JSON 中，用于前端展示和 Prompt 解释 |
| **事务一致性** | 上传解析、查询库创建、元数据写入必须视为一个事务；任一步失败都删除临时文件和半成品查询库 |
| **过期清理** | 可选 `file_uploads.expired_at` 默认 7 天后，由 `FileCleanupService` 清理过期记录、原始文件和查询库 |

## 11. 路由文件示例

```python
# backend/routers/chat.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.chat import ChatRequest, ChatStreamResponse
from services.chat_engine import ChatEngine

router = APIRouter()
chat_engine = ChatEngine()


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE 流式对话接口。
    客户端通过 EventSource 或 fetch + ReadableStream 消费。
    """
    streamer = await chat_engine.process_message(
        user_query=request.message,
        conversation_id=request.conversation_id,
        user_id=current_user.id,
        db=db,
        datasource_type=request.data_source_type,
        db_connection_id=request.db_connection_id,
        file_upload_id=request.file_upload_id,
        agent_config_id=request.agent_config_id,
    )
    return streamer.to_response()
```

---

*本文档对应 ChatBI PRD v0.6 的后端实现设计。开发者可基于此文档直接搭建后端项目骨架。*
