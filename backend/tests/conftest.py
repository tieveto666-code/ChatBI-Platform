"""
ChatBI 后端测试 — conftest
============================================================
Fixtures: test_db (SQLite :memory:), test_client (httpx.AsyncClient),
auth_headers (JWT Token), 预设测试数据（3 角色 + admin 用户 + 菜单）
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncGenerator

TEST_DB_PATH = "/private/tmp/chatbi_backend_tests.sqlite"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["MOCK_LLM_FAULT_MODE"] = "none"

from models import Base, Role, User, Menu, Conversation, Message, QueryLog, DbConnection
from models.agent_config import AgentConfig
from models.role_agent import RoleAgent
from models.datasource_field_lexicon import DatasourceFieldLexicon
from models.role_datasource import RoleDatasource
from models.role_menu import RoleMenu

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE
from services.auth_service import AuthService

from config import settings

# ── 内存 SQLite 引擎 & Session ──
test_engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """FastAPI 依赖覆盖：返回 test_db session"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop():
    """为 pytest-asyncio 创建事件循环（session 级）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_app():
    """创建测试用的 FastAPI 应用实例，带覆盖的依赖"""
    from main import app
    from core.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient fixture"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_db():
    """每个测试函数独立的数据库 session（事务回滚）"""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()

    # ── 预设测试数据（3 角色 + admin 用户 + 菜单）──
    _seed_test_data(db)

    yield db

    db.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest_asyncio.fixture
async def auth_headers(test_client: AsyncClient, test_db) -> dict:
    """获取 admin 用户的 JWT Token（依赖 test_db 确保表与种子数据就绪）"""
    response = await test_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    data = response.json()
    token = data["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_auth_headers(test_client: AsyncClient, test_db) -> dict:
    """获取普通用户的 JWT Token"""
    response = await test_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test123"},
    )
    data = response.json()
    token = data["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════
# 种子数据
# ═══════════════════════════════════════════════


def _seed_test_data(db: Session):
    """注入预设测试数据"""
    # ── 角色 ──
    roles = [
        Role(id=1, name="超级管理员", code="admin", description="拥有全部权限", is_system=True, sort_order=1),
        Role(id=2, name="数据分析师", code="analyst", description="可管理数据源", is_system=True, sort_order=2),
        Role(id=3, name="普通用户", code="user", description="仅对话分析", is_system=True, sort_order=3),
    ]
    for r in roles:
        db.add(r)
    db.flush()

    # ── 菜单 ──
    menus = [
        Menu(id=1, parent_id=None, name="对话分析", icon="ChatIcon", path="/chat", component="ChatPage", sort_order=1, is_visible=True),
        Menu(id=2, parent_id=None, name="数据源管理", icon="StorageIcon", path="/datasources", component="DataSourcesPage", sort_order=2, is_visible=True),
        Menu(id=3, parent_id=None, name="智能体配置", icon="PsychologyIcon", path="/agents", component="AgentConfigPage", sort_order=3, is_visible=True),
        Menu(id=10, parent_id=None, name="系统管理", icon="SettingsIcon", path="/admin", component="AdminLayout", sort_order=99, is_visible=True),
        Menu(id=11, parent_id=10, name="用户管理", icon="PeopleIcon", path="/admin/users", component="UserManager", sort_order=1, is_visible=True),
        Menu(id=12, parent_id=10, name="角色管理", icon="SecurityIcon", path="/admin/roles", component="RoleManager", sort_order=2, is_visible=True),
        Menu(id=13, parent_id=10, name="菜单管理", icon="MenuIcon", path="/admin/menus", component="MenuManager", sort_order=3, is_visible=True),
    ]
    for m in menus:
        db.add(m)
    db.flush()

    # ── 角色-菜单关联 ──
    role_menu_assoc = [
        RoleMenu(role_id=1, menu_id=1, permission="admin"),
        RoleMenu(role_id=1, menu_id=2, permission="admin"),
        RoleMenu(role_id=1, menu_id=3, permission="admin"),
        RoleMenu(role_id=1, menu_id=10, permission="admin"),
        RoleMenu(role_id=1, menu_id=11, permission="admin"),
        RoleMenu(role_id=1, menu_id=12, permission="admin"),
        RoleMenu(role_id=1, menu_id=13, permission="admin"),
        RoleMenu(role_id=2, menu_id=1, permission="write"),
        RoleMenu(role_id=2, menu_id=2, permission="write"),
        RoleMenu(role_id=2, menu_id=3, permission="write"),
        RoleMenu(role_id=3, menu_id=1, permission="read"),
    ]
    for rm in role_menu_assoc:
        db.add(rm)
    db.flush()

    # ── 用户 ──
    users = [
        User(
            username="admin",
            email="admin@test.local",
            password_hash=AuthService._hash_password("admin123"),
            role_id=1,
            is_active=True,
        ),
        User(
            username="analyst_user",
            email="analyst@test.local",
            password_hash=AuthService._hash_password("analyst123"),
            role_id=2,
            is_active=True,
        ),
        User(
            username="testuser",
            email="user@test.local",
            password_hash=AuthService._hash_password("test123"),
            role_id=3,
            is_active=True,
        ),
        User(
            username="disabled_user",
            email="disabled@test.local",
            password_hash=AuthService._hash_password("disabled123"),
            role_id=3,
            is_active=False,
        ),
        User(
            username="norole",
            email="norole@test.local",
            password_hash=AuthService._hash_password("norole123"),
            role_id=None,
            is_active=True,
        ),
    ]
    for u in users:
        db.add(u)
    db.add(DbConnection(
        id=1,
        name="测试 SQLite",
        db_type="sqlite",
        db_path=TEST_DB_PATH,
        is_active=True,
        visibility="public",
    ))
    db.add(AgentConfig(
        id=1,
        name="默认 NL2SQL 智能体",
        description="测试用默认智能体",
        system_prompt=SYSTEM_PROMPT_TEMPLATE,
        synonym_map=None,
        model_provider="mock",
        model_name="mock",
        temperature=10,
        max_tokens=4096,
        is_default=True,
        is_active=True,
        visibility="public",
        default_data_source_type="db",
        default_db_connection_id=1,
    ))
    db.flush()
    db.add(RoleAgent(role_id=1, agent_id=1, permission="admin"))
    db.add(RoleAgent(role_id=2, agent_id=1, permission="use"))
    db.add(RoleAgent(role_id=3, agent_id=1, permission="use"))
    db.add(RoleDatasource(role_id=1, resource_type="db_connection", resource_id=1, permission="admin"))
    db.add(RoleDatasource(role_id=2, resource_type="db_connection", resource_id=1, permission="use"))
    db.add(DatasourceFieldLexicon(
        resource_type="db_connection",
        resource_id=1,
        table_name="orders",
        target_column="amount",
        standard_term="销售额",
        synonyms=["营收", "销售收入"],
        is_active=1,
    ))
    db.commit()
