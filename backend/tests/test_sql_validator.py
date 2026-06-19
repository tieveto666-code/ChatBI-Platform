"""
测试 SQL 校验器 — SELECT 通过、DDL/DML 拒绝、apply_limit
"""

import pytest
from services.sql_validator import SQLValidator

validator = SQLValidator()


class TestSQLValidate:
    """SQL 安全校验测试"""

    def test_select_passes(self):
        """普通 SELECT 语句应通过"""
        is_valid, msg = validator.validate("SELECT * FROM users")
        assert is_valid, f"应通过: {msg}"

    def test_select_with_where(self):
        """带 WHERE 的 SELECT"""
        is_valid, msg = validator.validate("SELECT id, name FROM users WHERE id = 1")
        assert is_valid, f"应通过: {msg}"

    def test_select_with_join(self):
        """带 JOIN 的 SELECT"""
        sql = "SELECT u.name, r.name FROM users u JOIN roles r ON u.role_id = r.id"
        is_valid, msg = validator.validate(sql)
        assert is_valid, f"应通过: {msg}"

    def test_select_with_group_by(self):
        """带 GROUP BY 的 SELECT"""
        sql = "SELECT role_id, COUNT(*) FROM users GROUP BY role_id"
        is_valid, msg = validator.validate(sql)
        assert is_valid, f"应通过: {msg}"

    def test_select_with_subquery(self):
        """带子查询的 SELECT"""
        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM conversations)"
        is_valid, msg = validator.validate(sql)
        assert is_valid, f"应通过: {msg}"

    def test_drop_table_rejected(self):
        """DROP TABLE 应被拒绝"""
        is_valid, msg = validator.validate("DROP TABLE users")
        assert not is_valid, "应拒绝 DROP"
        assert "禁止" in msg or "禁止" in msg

    def test_delete_from_rejected(self):
        """DELETE 应被拒绝"""
        is_valid, msg = validator.validate("DELETE FROM users WHERE id = 1")
        assert not is_valid, "应拒绝 DELETE"
        assert "禁止" in msg

    def test_insert_into_rejected(self):
        """INSERT 应被拒绝"""
        is_valid, msg = validator.validate("INSERT INTO users (id) VALUES (1)")
        assert not is_valid, "应拒绝 INSERT"

    def test_update_rejected(self):
        """UPDATE 应被拒绝"""
        is_valid, msg = validator.validate("UPDATE users SET name = 'test' WHERE id = 1")
        assert not is_valid, "应拒绝 UPDATE"

    def test_create_table_rejected(self):
        """CREATE TABLE 应被拒绝"""
        is_valid, msg = validator.validate("CREATE TABLE test (id INT)")
        assert not is_valid, "应拒绝 CREATE"

    def test_alter_table_rejected(self):
        """ALTER TABLE 应被拒绝"""
        is_valid, msg = validator.validate("ALTER TABLE users ADD COLUMN test INT")
        assert not is_valid, "应拒绝 ALTER"

    def test_truncate_rejected(self):
        """TRUNCATE 应被拒绝"""
        is_valid, msg = validator.validate("TRUNCATE TABLE users")
        assert not is_valid, "应拒绝 TRUNCATE"

    def test_empty_sql_rejected(self):
        """空 SQL 应被拒绝"""
        is_valid, msg = validator.validate("")
        assert not is_valid, "应拒绝空 SQL"
        assert "空" in msg

    def test_whitespace_sql_rejected(self):
        """空白 SQL 应被拒绝"""
        is_valid, msg = validator.validate("   ")
        assert not is_valid, "应拒绝空白"

    def test_multiple_statements(self):
        """多个语句（分号注入）"""
        is_valid, msg = validator.validate("SELECT * FROM users; DROP TABLE users")
        # sqlparse 会把多个语句分开，校验器检查第一个语句
        assert not is_valid, "应检测到多语句注入"


class TestSQLLimit:
    """SQL LIMIT 自动追加测试"""

    def test_limit_applied(self):
        """没有 LIMIT 的 SQL 应自动追加"""
        result = validator.apply_limit("SELECT * FROM users")
        assert "LIMIT" in result.upper()

    def test_limit_not_duplicated(self):
        """已有 LIMIT 不应重复追加"""
        result = validator.apply_limit("SELECT * FROM users LIMIT 5")
        assert result.upper().count("LIMIT") == 1

    def test_limit_with_custom_max(self):
        """自定义最大行数"""
        result = validator.apply_limit("SELECT * FROM users", max_rows=100)
        assert "LIMIT 100" in result

    def test_limit_removes_trailing_semicolon(self):
        """处理末尾分号"""
        result = validator.apply_limit("SELECT * FROM users;")
        assert ";" not in result

    def test_complex_sql_with_limit(self):
        """复杂 SQL 也追加 LIMIT"""
        sql = """
        SELECT u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        """
        result = validator.apply_limit(sql)
        assert "LIMIT" in result.upper()


class TestSQLExtractTables:
    """表名提取测试"""

    def test_simple_from(self):
        """简单 FROM"""
        tables = validator.extract_table_names("SELECT * FROM users")
        assert "users" in tables

    def test_multiple_tables(self):
        """多表 JOIN"""
        tables = validator.extract_table_names(
            "SELECT * FROM users JOIN roles ON users.role_id = roles.id"
        )
        assert "users" in tables
        assert "roles" in tables

    def test_no_from(self):
        """没有 FROM 的语句"""
        tables = validator.extract_table_names("SELECT 1")
        assert tables == []

    def test_code_block_cleanup(self):
        """处理 markdown 代码块"""
        sql = """```sql
        SELECT * FROM users
        ```"""
        is_valid, msg = validator.validate(validator.clean_sql(sql))
        assert is_valid, msg


class TestSQLExtractSelect:
    """SELECT 提取测试"""

    def test_extract_from_markdown_prose_returns_none(self):
        prose = """根据当前数据库 Schema，我管理着以下 3 张数据表：

### 1. `orders`（订单表）
| 字段名 | 类型 |
|--------|------|
| id | INTEGER |

请问你想查询什么数据？"""
        assert validator.extract_select_sql(prose) is None
        assert not validator.is_executable_sql(prose)

    def test_extract_from_sql_codeblock(self):
        text = "说明\n```sql\nSELECT id FROM users\n```"
        assert validator.extract_select_sql(text) == "SELECT id FROM users"
