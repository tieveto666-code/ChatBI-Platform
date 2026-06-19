from __future__ import annotations
from typing import Tuple

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML, DDL

from config import settings


class SQLValidator:
    """
    SQL 安全校验器 — 4 层防护。
    基于 sqlparse AST 解析，替代简单的正则匹配。
    """

    # 禁止的 DDL/DML 关键词
    FORBIDDEN_KEYWORDS: set = {
        "DROP", "ALTER", "TRUNCATE", "CREATE",
        "INSERT", "UPDATE", "DELETE", "REPLACE",
        "GRANT", "REVOKE", "ATTACH", "DETACH",
        "PRAGMA",
    }

    # 允许的表操作白名单（仅 SELECT）
    ALLOWED_STATEMENT_TYPES: set = {"SELECT"}

    def validate(self, sql: str) -> Tuple[bool, str]:
        """
        校验 SQL 安全性。
        Returns: (is_valid, error_message)
        """
        # L0: 空检查
        if not sql or not sql.strip():
            return False, "SQL 为空"

        sql = self.clean_sql(sql)

        try:
            parsed = sqlparse.parse(sql)
        except Exception:
            return False, "SQL 语法解析失败"

        if not parsed:
            return False, "SQL 无法解析"
        if len([statement for statement in parsed if str(statement).strip().strip(";")]) != 1:
            return False, "仅允许单条 SELECT 语句"

        for statement in parsed:
            # L1: 检查根节点类型是否允许
            stmt_type = statement.get_type()
            if stmt_type not in self.ALLOWED_STATEMENT_TYPES:
                return False, f"禁止的非 SELECT 语句: {stmt_type}"

            # L2: 检查是否含 DDL/DML 关键词
            for token in statement.flatten():
                if token.ttype is DDL or token.ttype is DML:
                    if token.value.upper() in self.FORBIDDEN_KEYWORDS:
                        return False, f"包含禁止的关键词: {token.value}"

            # L3: 检查是否有多个语句（分号注入）
            # sqlparse 对多个语句会返回多个 statement

        return True, ""

    def apply_limit(self, sql: str, max_rows: int | None = None) -> str:
        """强制追加 LIMIT 子句（L4 防护）"""
        sql = self.clean_sql(sql).rstrip(";").strip()
        limit = max_rows if max_rows is not None else settings.SQL_MAX_RESULT_ROWS
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {limit}"
        return sql

    def clean_sql(self, sql: str) -> str:
        """移除 LLM 常见 Markdown 包装。"""
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            sql = "\n".join(lines).strip()
        return sql

    def extract_select_sql(self, text: str) -> str | None:
        """从 LLM 输出中提取可执行的 SELECT 语句；无法提取则返回 None。"""
        import re

        if not text or not text.strip():
            return None

        cleaned = self.clean_sql(text)
        if self.validate(cleaned)[0]:
            return cleaned

        for match in re.finditer(r"```(?:sql)?\s*\n(.*?)```", text, re.S | re.I):
            candidate = self.clean_sql(match.group(1))
            if self.validate(candidate)[0]:
                return candidate

        for line in text.splitlines():
            candidate = line.strip().rstrip(";")
            if candidate.upper().startswith("SELECT") and self.validate(candidate)[0]:
                return candidate

        return None

    def is_executable_sql(self, text: str) -> bool:
        """判断文本是否包含可执行 SELECT SQL。"""
        extracted = self.extract_select_sql(text)
        return extracted is not None

    def extract_table_names(self, sql: str) -> list[str]:
        """从 SQL 中提取 FROM/JOIN 后的表名。"""
        tables: list[str] = []
        try:
            parsed = sqlparse.parse(sql)
            for statement in parsed:
                expect_table = False
                for token in statement.flatten():
                    value = token.value.upper()
                    if token.ttype is Keyword and value in {"FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"}:
                        expect_table = True
                        continue
                    if expect_table and not token.is_whitespace:
                        if value in {"ON", "WHERE", "GROUP", "GROUP BY", "ORDER", "ORDER BY", "HAVING", "LIMIT"}:
                            expect_table = False
                            continue
                        table = token.value.strip('"`[]')
                        if table and table not in tables:
                            tables.append(table)
                        expect_table = False
        except Exception:
            pass
        return tables
