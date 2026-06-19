#!/usr/bin/env python3
"""
ChatBI 种子数据初始化脚本。
首次部署时运行：python seed.py

注意：请在数据库表创建后运行（应用首次启动时自动建表）。
幂等性：INSERT OR IGNORE，可重复运行。
"""

import json
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from core.database import SessionLocal, init_db
from models.role import Role
from models.menu import Menu
from models.role_menu import RoleMenu
from models.user import User
from models.db_connection import DbConnection
from models.file_upload import FileUpload
from models.file_sheet import FileSheet
from services.excel_parser import ExcelParser
from services.file_query_db import build_file_query_db
from services.schema_sync import SchemaSync
from models.role_agent import RoleAgent
from models.role_datasource import RoleDatasource
from models.agent_config import AgentConfig
from prompts.nl2sql_v1 import SYSTEM_PROMPT_TEMPLATE
from services.auth_service import AuthService

BACKEND_ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = BACKEND_ROOT / "data" / "samples"
DEMO_SQLITE_PATH = SAMPLES_DIR / "demo_business.sqlite"
SAMPLE_XLSX_PATH = SAMPLES_DIR / "sample.xlsx"
SAMPLE_DB_CONN_NAME = "示例 SQLite（演示订单库）"
SAMPLE_EXCEL_ORIGINAL_NAME = "示例销售数据（样例）.xlsx"


def _resolve_under_backend(rel: str) -> Path:
    p = Path(rel)
    return p.resolve() if p.is_absolute() else (BACKEND_ROOT / p).resolve()


def ensure_demo_sqlite() -> Path:
    """创建内置演示用 SQLite（多表 + 示例行），路径相对于 backend 根目录。"""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEMO_SQLITE_PATH))
    try:
        conn.executescript(
            """
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS users;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT,
                city TEXT
            );
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty INTEGER NOT NULL DEFAULT 1,
                amount REAL NOT NULL,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            DELETE FROM orders;
            DELETE FROM products;
            DELETE FROM users;
            INSERT INTO users (id, username, email, city) VALUES
                (1, 'zhangsan', 'zs@example.com', '上海'),
                (2, 'lisi', 'ls@example.com', '北京'),
                (3, 'wangwu', 'ww@example.com', '深圳');
            INSERT INTO products (id, name, price, category) VALUES
                (101, '无线鼠标', 89.0, '外设'),
                (102, '机械键盘', 399.0, '外设'),
                (103, '27寸显示器', 1299.0, '显示设备');
            INSERT INTO orders (id, user_id, product_id, qty, amount, status, created_at) VALUES
                (1001, 1, 101, 2, 178.0, 'paid', '2026-01-10'),
                (1002, 2, 103, 1, 1299.0, 'paid', '2026-01-12'),
                (1003, 1, 102, 1, 399.0, 'pending', '2026-02-01'),
                (1004, 3, 101, 1, 89.0, 'cancelled', '2026-02-05');
            """
        )
        conn.commit()
    finally:
        conn.close()
    return DEMO_SQLITE_PATH.resolve()


def ensure_sample_xlsx() -> Path:
    """生成双 Sheet 的示例 xlsx（订单 / 产品）。"""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    from openpyxl import Workbook

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "订单"
    ws1.append(["订单号", "客户", "金额", "状态"])
    ws1.append(["O-001", "张三", 178.0, "已付款"])
    ws1.append(["O-002", "李四", 1299.0, "已付款"])
    ws1.append(["O-003", "张三", 399.0, "待付款"])

    ws2 = wb.create_sheet("产品")
    ws2.append(["SKU", "名称", "单价", "类目"])
    ws2.append(["P-101", "无线鼠标", 89.0, "外设"])
    ws2.append(["P-102", "机械键盘", 399.0, "外设"])
    ws2.append(["P-103", "27寸显示器", 1299.0, "显示设备"])

    wb.save(SAMPLE_XLSX_PATH)
    return SAMPLE_XLSX_PATH.resolve()


def seed_sample_datasources(db) -> None:
    """预置示例 SQLite 连接 + 示例 Excel 文件记录（幂等）。"""
    demo_path = ensure_demo_sqlite()
    existing_conn = db.query(DbConnection).filter(DbConnection.name == SAMPLE_DB_CONN_NAME).first()
    if not existing_conn:
        conn_row = DbConnection(
            name=SAMPLE_DB_CONN_NAME,
            db_type="sqlite",
            db_path=str(demo_path),
            host=None,
            port=None,
            database_name=None,
            username=None,
            password=None,
            is_active=True,
            visibility="public",
        )
        db.add(conn_row)
        db.flush()
        print(f"  ✅ 创建示例数据库连接: {SAMPLE_DB_CONN_NAME} -> {demo_path}")
    else:
        existing_conn.db_path = str(demo_path)
        existing_conn.db_type = "sqlite"
        existing_conn.is_active = True
        existing_conn.visibility = "public"
        conn_row = existing_conn
        print(f"  ℹ️  已更新示例数据库连接路径: {demo_path}")

    try:
        schema = SchemaSync().sync(conn_row)
        conn_row.schema_cache = json.dumps(schema, ensure_ascii=False)
        db.flush()
        print("  ✅ 示例 SQLite Schema 已缓存")
    except Exception as e:
        print(f"  ⚠️  示例 SQLite Schema 缓存跳过: {e}")

    if db.query(FileUpload).filter(FileUpload.original_name == SAMPLE_EXCEL_ORIGINAL_NAME).first():
        print(f"  ℹ️  示例 Excel 已存在: {SAMPLE_EXCEL_ORIGINAL_NAME}")
        return

    ensure_sample_xlsx()
    upload_dir = _resolve_under_backend(settings.UPLOAD_DIR)
    file_db_dir = _resolve_under_backend(settings.FILE_DB_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_db_dir.mkdir(parents=True, exist_ok=True)

    ext = ".xlsx"
    stored_name = f"{uuid.uuid4()}{ext}"
    dest_path = upload_dir / stored_name
    shutil.copy2(SAMPLE_XLSX_PATH, dest_path)

    excel_parser = ExcelParser()
    parsed = excel_parser.parse(str(dest_path))
    total_rows = len([r for sheets in parsed for r in sheets.get("rows", [])])
    sheet_count = len(parsed)
    file_size = dest_path.stat().st_size

    file_upload = FileUpload(
        filename=stored_name,
        original_name=SAMPLE_EXCEL_ORIGINAL_NAME,
        file_path=str(dest_path.resolve()),
        file_size=file_size,
        sheet_count=sheet_count,
        total_rows=total_rows,
        status="parsed",
        visibility="public",
    )
    db.add(file_upload)
    db.flush()

    query_db_path = file_db_dir / f"{file_upload.id}.sqlite"
    schema_cache, mappings = build_file_query_db(parsed, query_db_path)
    file_upload.query_db_path = str(query_db_path.resolve())
    file_upload.schema_cache = json.dumps(schema_cache, ensure_ascii=False)

    for sheet, mapping in zip(schema_cache, mappings):
        sheet_schema = json.dumps(sheet["columns"], ensure_ascii=False)
        db.add(FileSheet(
            file_upload_id=file_upload.id,
            sheet_name=sheet["sheet_name"],
            table_name=sheet["table_name"],
            column_count=len(sheet["columns"]),
            row_count=sheet["row_count"],
            columns_schema=sheet_schema,
            name_mapping_json=json.dumps(mapping, ensure_ascii=False),
        ))

    print(f"  ✅ 创建示例 Excel 记录: {SAMPLE_EXCEL_ORIGINAL_NAME}（{sheet_count} 个 Sheet）")


def seed_sample_field_lexicons(db) -> None:
    """为示例数据源预置字段术语（标准词 + 同义词）。"""
    from models.datasource_field_lexicon import DatasourceFieldLexicon

    demo_conn = db.query(DbConnection).filter(DbConnection.name == SAMPLE_DB_CONN_NAME).first()
    if demo_conn:
        samples = [
            ("orders", "amount", "销售额", ["营收", "销售收入"]),
            ("orders", "qty", "订单量", ["数量", "件数"]),
            ("users", "username", "用户名", ["账户名", "用户名称"]),
        ]
        for table_name, target_column, standard_term, synonyms in samples:
            exists = db.query(DatasourceFieldLexicon).filter(
                DatasourceFieldLexicon.resource_type == "db_connection",
                DatasourceFieldLexicon.resource_id == demo_conn.id,
                DatasourceFieldLexicon.table_name == table_name,
                DatasourceFieldLexicon.target_column == target_column,
            ).first()
            if not exists:
                db.add(DatasourceFieldLexicon(
                    resource_type="db_connection",
                    resource_id=demo_conn.id,
                    table_name=table_name,
                    target_column=target_column,
                    standard_term=standard_term,
                    synonyms=synonyms,
                    is_active=1,
                ))
        print("  ✅ 示例 SQLite 字段术语已就绪")


def seed_role_resource_grants(db):
    """为预置角色分配公共资源的使用权限。"""
    analyst = db.query(Role).filter(Role.code == "analyst").first()
    user_role = db.query(Role).filter(Role.code == "user").first()
    default_agent = db.query(AgentConfig).filter(AgentConfig.is_default == 1).first()
    demo_conn = db.query(DbConnection).filter(DbConnection.name == SAMPLE_DB_CONN_NAME).first()
    demo_file = db.query(FileUpload).filter(FileUpload.original_name == SAMPLE_EXCEL_ORIGINAL_NAME).first()

    if default_agent:
        for role in (analyst, user_role):
            if not role:
                continue
            exists = db.query(RoleAgent).filter(
                RoleAgent.role_id == role.id,
                RoleAgent.agent_id == default_agent.id,
            ).first()
            if not exists:
                db.add(RoleAgent(role_id=role.id, agent_id=default_agent.id, permission="use"))

    if analyst and demo_conn:
        exists = db.query(RoleDatasource).filter(
            RoleDatasource.role_id == analyst.id,
            RoleDatasource.resource_type == "db_connection",
            RoleDatasource.resource_id == demo_conn.id,
        ).first()
        if not exists:
            db.add(RoleDatasource(
                role_id=analyst.id,
                resource_type="db_connection",
                resource_id=demo_conn.id,
                permission="use",
            ))

    if analyst and demo_file:
        exists = db.query(RoleDatasource).filter(
            RoleDatasource.role_id == analyst.id,
            RoleDatasource.resource_type == "file_upload",
            RoleDatasource.resource_id == demo_file.id,
        ).first()
        if not exists:
            db.add(RoleDatasource(
                role_id=analyst.id,
                resource_type="file_upload",
                resource_id=demo_file.id,
                permission="use",
            ))

    db.flush()
    print("  ✅ 预置角色资源授权已同步")


def hash_password(password: str) -> str:
    """密码哈希。AuthService 兼容历史 SHA256，这里新 seed 使用 bcrypt。"""
    return AuthService._hash_password(password)


def seed():
    print("🌱 ChatBI 种子数据初始化开始...")
    
    # 1. 确保表已创建
    init_db()
    print("✅ 数据库表已就绪")
    
    db = SessionLocal()
    
    try:
        # ── 2. 预设角色 ──
        roles_data = [
            {"name": "超级管理员", "code": "admin",    "description": "拥有全部系统权限",                   "is_system": True,  "sort_order": 1},
            {"name": "数据分析师",  "code": "analyst",  "description": "可使用对话分析、管理数据源、配置智能体", "is_system": True,  "sort_order": 2},
            {"name": "普通用户",   "code": "user",     "description": "仅可使用对话分析和查看结果",            "is_system": True,  "sort_order": 3},
        ]
        
        for rd in roles_data:
            existing = db.query(Role).filter(Role.code == rd["code"]).first()
            if existing:
                print(f"  ℹ️  角色已存在: {rd['name']} (code={rd['code']})")
            else:
                role = Role(**rd)
                db.add(role)
                db.flush()
                print(f"  ✅ 创建角色: {rd['name']} (code={rd['code']})")
        
        # ── 3. 预设菜单 ──
        menus_data = [
            # 顶级菜单
            {"id": 1,  "parent_id": None, "name": "对话分析",     "icon": "ChatIcon",     "path": "/chat",          "component": "ChatPage",          "sort_order": 1,  "is_visible": True},
            {"id": 2,  "parent_id": None, "name": "数据源管理",    "icon": "StorageIcon",  "path": "/datasources",   "component": "DataSourcesPage",   "sort_order": 2,  "is_visible": True},
            {"id": 3,  "parent_id": None, "name": "智能体配置",    "icon": "PsychologyIcon","path": "/agents",       "component": "AgentConfigPage",   "sort_order": 3,  "is_visible": True},
            {"id": 10, "parent_id": None, "name": "系统管理",      "icon": "SettingsIcon", "path": "/admin",         "component": "AdminLayout",       "sort_order": 99, "is_visible": True},
            
            # 系统管理子菜单
            {"id": 11, "parent_id": 10, "name": "用户管理",       "icon": "PeopleIcon",   "path": "/admin/users",   "component": "UserManager",       "sort_order": 1,  "is_visible": True},
            {"id": 12, "parent_id": 10, "name": "角色管理",       "icon": "SecurityIcon", "path": "/admin/roles",   "component": "RoleManager",       "sort_order": 2,  "is_visible": True},
            {"id": 13, "parent_id": 10, "name": "菜单管理",       "icon": "MenuIcon",     "path": "/admin/menus",   "component": "MenuManager",       "sort_order": 3,  "is_visible": True},
        ]
        
        for md in menus_data:
            existing = db.query(Menu).filter(Menu.id == md["id"]).first()
            if existing:
                print(f"  ℹ️  菜单已存在: {md['name']} (id={md['id']})")
            else:
                menu = Menu(**md)
                db.add(menu)
                db.flush()
                print(f"  ✅ 创建菜单: {md['name']} (id={md['id']})")
        
        db.flush()
        
        # ── 4. 角色-菜单关联 ──
        # admin 角色：所有菜单
        admin_role = db.query(Role).filter(Role.code == "admin").first()
        if admin_role:
            all_menus = db.query(Menu).all()
            for menu in all_menus:
                existing = db.query(RoleMenu).filter(
                    RoleMenu.role_id == admin_role.id,
                    RoleMenu.menu_id == menu.id
                ).first()
                if not existing:
                    db.add(RoleMenu(role_id=admin_role.id, menu_id=menu.id, permission="admin"))
            db.flush()
            print(f"  ✅ admin 角色关联 {len(all_menus)} 个菜单")
        
        # analyst 角色：对话 + 数据源 + 智能体
        analyst_role = db.query(Role).filter(Role.code == "analyst").first()
        if analyst_role:
            analyst_menu_ids = [1, 2, 3]
            for mid in analyst_menu_ids:
                existing = db.query(RoleMenu).filter(
                    RoleMenu.role_id == analyst_role.id,
                    RoleMenu.menu_id == mid
                ).first()
                if not existing:
                    db.add(RoleMenu(role_id=analyst_role.id, menu_id=mid, permission="write"))
            db.flush()
            print(f"  ✅ analyst 角色关联 {len(analyst_menu_ids)} 个菜单")
        
        # user 角色：仅对话
        user_role = db.query(Role).filter(Role.code == "user").first()
        if user_role:
            existing = db.query(RoleMenu).filter(
                RoleMenu.role_id == user_role.id,
                RoleMenu.menu_id == 1
            ).first()
            if not existing:
                db.add(RoleMenu(role_id=user_role.id, menu_id=1, permission="read"))
            db.flush()
            print(f"  ✅ user 角色关联 1 个菜单")
        
        # ── 5. 默认 admin 用户 ──
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@chatbi.local",
                password_hash=hash_password("admin123"),
                role_id=admin_role.id if admin_role else 1,
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
            print(f"  ✅ 创建默认管理员: admin / admin123")
        else:
            print(f"  ℹ️  管理员已存在: admin")
        
        # ── 6. 示例数据源（内置 SQLite + 示例 Excel）──
        seed_sample_datasources(db)
        seed_sample_field_lexicons(db)

        # ── 7. 默认智能体配置 ──
        demo_conn = db.query(DbConnection).filter(DbConnection.name == SAMPLE_DB_CONN_NAME).first()
        default_agent = db.query(AgentConfig).filter(AgentConfig.is_default == 1).first()
        if not default_agent:
            db.add(AgentConfig(
                name="默认 NL2SQL 智能体",
                description="MVP 内置问数智能体，可在智能体配置页调整 Prompt",
                system_prompt=SYSTEM_PROMPT_TEMPLATE,
                synonym_map=None,
                model_provider="deepseek",
                model_name="deepseek-chat",
                temperature=10,
                max_tokens=4096,
                is_default=True,
                is_active=True,
                visibility="public",
                default_data_source_type="db" if demo_conn else None,
                default_db_connection_id=demo_conn.id if demo_conn else None,
            ))
            db.flush()
            print("  ✅ 创建默认智能体配置")
        else:
            print(f"  ℹ️  默认智能体已存在: {default_agent.name}")
            default_agent.visibility = "public"
            if demo_conn and not default_agent.default_db_connection_id:
                default_agent.default_data_source_type = "db"
                default_agent.default_db_connection_id = demo_conn.id
                print("  ✅ 已为默认智能体绑定示例 SQLite 数据源")

        seed_role_resource_grants(db)

        db.commit()
        print("\n🎉 ChatBI 种子数据初始化完成！")
        print("   ─────────────────────────────────")
        print("   默认管理员: admin / admin123")
        print("   预设角色: admin, analyst, user")
        print("   预设菜单: 对话分析, 数据源管理, 智能体配置, 系统管理(含子菜单)")
        print("   示例资产: backend/data/samples/demo_business.sqlite, sample.xlsx")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 种子数据初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
