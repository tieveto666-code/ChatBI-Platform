from __future__ import annotations
import json
from typing import TYPE_CHECKING

from pathlib import Path

from sqlalchemy import create_engine, text

from models.db_connection import DbConnection
from core.exceptions import BusinessError
from core.error_codes import ErrorCode

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SchemaSync:
    """数据库 Schema 同步器 — 从数据源读取 Schema 并缓存"""

    def sync(self, db_connection: DbConnection) -> list[dict]:
        """
        同步数据源 Schema。

        Args:
            db_connection: DbConnection 对象

        Returns:
            list[dict]: Schema 列表 [{table_name, columns: [{name, type, nullable, pk}]}]
        """
        url = self._build_url(db_connection)
        schema = self._read_schema(url)
        return schema

    def sync_and_cache(self, db_connection: DbConnection, db: "Session") -> list[dict]:
        """同步 Schema 并缓存到 db_connections.schema_cache"""
        schema = self.sync(db_connection)
        db_connection.schema_cache = json.dumps(schema, ensure_ascii=False)
        db.commit()
        return schema

    def _build_url(self, conn: DbConnection) -> str:
        """构建 SQLAlchemy 连接 URL"""
        if conn.db_type == "sqlite":
            if not conn.db_path:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="SQLite 数据源未配置 db_path",
                )
            if not Path(conn.db_path).exists():
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"SQLite 文件不存在: {conn.db_path}",
                )
            return f"sqlite:///{conn.db_path}"
        elif conn.db_type == "mysql":
            return f"mysql+pymysql://{conn.username}:{conn.password}@{conn.host}:{conn.port}/{conn.database_name}"
        elif conn.db_type == "postgresql":
            return f"postgresql://{conn.username}:{conn.password}@{conn.host}:{conn.port}/{conn.database_name}"
        else:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"不支持的数据库类型: {conn.db_type}",
            )

    def _read_schema(self, url: str) -> list[dict]:
        """从数据库读取 Schema"""
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if "sqlite" in url else {},
        )

        try:
            with engine.connect() as conn:
                if "sqlite" in url:
                    return self._read_sqlite_schema(conn)
                elif "postgresql" in url:
                    return self._read_postgresql_schema(conn)
                elif "mysql" in url:
                    return self._read_mysql_schema(conn)
                return []
        finally:
            engine.dispose()

    def _read_sqlite_schema(self, conn) -> list[dict]:
        """从 SQLite 读取 Schema"""
        tables_result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ))
        table_names = [row[0] for row in tables_result]

        schema = []
        for table_name in table_names:
            columns_info = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()

            columns = []
            for col in columns_info:
                columns.append({
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3],
                    "pk": bool(col[5]),
                })

            schema.append({
                "table_name": table_name,
                "columns": columns,
                "foreign_keys": self._read_sqlite_foreign_keys(conn, table_name),
            })

        return schema

    def _read_sqlite_foreign_keys(self, conn, table_name: str) -> list[dict]:
        rows = conn.execute(text(f"PRAGMA foreign_key_list('{table_name}')")).fetchall()
        return [
            {
                "column": row[3],
                "ref_table": row[2],
                "ref_column": row[4],
            }
            for row in rows
        ]

    def _read_postgresql_schema(self, conn) -> list[dict]:
        """从 PostgreSQL 读取 Schema"""
        result = conn.execute(text("""
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END as is_pk
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.column_name = kcu.column_name AND c.table_name = kcu.table_name
            LEFT JOIN information_schema.table_constraints tc
                ON kcu.constraint_name = tc.constraint_name AND tc.constraint_type = 'PRIMARY KEY'
            WHERE t.table_schema = 'public'
            ORDER BY t.table_name, c.ordinal_position
        """))

        tables: dict = {}
        for row in result:
            tn = row[0]
            if tn not in tables:
                tables[tn] = {"table_name": tn, "columns": []}
            tables[tn]["columns"].append({
                "name": row[1],
                "type": row[2],
                "nullable": row[3] == "YES",
                "pk": bool(row[4]),
            })

        return list(tables.values())

    def _read_mysql_schema(self, conn) -> list[dict]:
        """从 MySQL 读取 Schema"""
        result = conn.execute(text("""
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                IF(c.column_key = 'PRI', 1, 0) as is_pk
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            WHERE t.table_schema = DATABASE()
            ORDER BY t.table_name, c.ordinal_position
        """))

        tables: dict = {}
        for row in result:
            tn = row[0]
            if tn not in tables:
                tables[tn] = {"table_name": tn, "columns": []}
            tables[tn]["columns"].append({
                "name": row[1],
                "type": row[2],
                "nullable": row[3] == "YES",
                "pk": bool(row[4]),
            })

        return list(tables.values())
