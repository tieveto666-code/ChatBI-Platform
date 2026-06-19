from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.database import init_db
from routers import auth, chat, datasources, admin_users, admin_roles, admin_menus, agents
from config import settings
from core.exceptions import ChatBIException
from core.error_codes import ErrorCode

app = FastAPI(
    title=settings.APP_NAME,
    description="基于大模型的对话式数据分析助手",
    version=settings.APP_VERSION,
)

# ── CORS 配置 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ── 全局异常处理器 ──
@app.exception_handler(ChatBIException)
async def chatbi_exception_handler(request: Request, exc: ChatBIException):
    status_code = 400
    if 5000 <= exc.code < 6000:
        status_code = 500
    elif exc.code in (4001, 4002):
        status_code = 403
    elif exc.code in (1001, 1003):
        status_code = 401
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.INTERNAL_ERROR,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None,
        },
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
    init_db()
    print("✅ 数据库表已就绪")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
