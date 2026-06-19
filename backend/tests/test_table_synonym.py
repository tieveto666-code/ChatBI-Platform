"""字段术语（标准词 + 同义词）服务测试"""

from models.conversation import Conversation
from models.datasource_field_lexicon import DatasourceFieldLexicon
from services.table_synonym_service import (
    create_table_synonym,
    format_synonyms_for_prompt,
    list_table_synonyms,
    normalize_synonyms,
)


class TestFieldLexiconService:
    def test_normalize_synonyms_dedupes_and_excludes_standard(self):
        result = normalize_synonyms(["营收", "销售额", "营收", ""], "销售额")
        assert result == ["营收"]

    def test_create_and_list_field_lexicons(self, test_db):
        schema = [{
            "table_name": "orders",
            "columns": [
                {"name": "amount", "type": "REAL"},
                {"name": "qty", "type": "INTEGER"},
            ],
        }]
        row = create_table_synonym(
            test_db, "db_connection", 1, "orders",
            "qty", "订单量", ["数量", "件数"], schema, created_by=1,
        )
        assert row["standard_term"] == "订单量"
        assert row["synonyms"] == ["数量", "件数"]

        items = list_table_synonyms(test_db, "db_connection", 1, "orders")
        cols = {i["target_column"] for i in items}
        assert "amount" in cols
        assert "qty" in cols

    def test_create_multiple_fields_in_same_table(self, test_db):
        schema = [{
            "table_name": "orders",
            "columns": [
                {"name": "amount", "type": "REAL"},
                {"name": "qty", "type": "INTEGER"},
                {"name": "status", "type": "TEXT"},
            ],
        }]
        create_table_synonym(
            test_db, "db_connection", 1, "orders",
            "qty", "订单量", ["数量", "件数"], schema, created_by=1,
        )
        create_table_synonym(
            test_db, "db_connection", 1, "orders",
            "status", "订单状态", ["状态"], schema, created_by=1,
        )

        items = list_table_synonyms(test_db, "db_connection", 1, "orders")
        assert len(items) == 3
        by_col = {i["target_column"]: i for i in items}
        assert by_col["amount"]["standard_term"] == "销售额"
        assert by_col["qty"]["synonyms"] == ["数量", "件数"]
        assert by_col["status"]["standard_term"] == "订单状态"

    def test_format_synonyms_for_prompt_groups_by_table(self, test_db):
        test_db.add(DatasourceFieldLexicon(
            resource_type="db_connection",
            resource_id=1,
            table_name="users",
            target_column="username",
            standard_term="用户名",
            synonyms=["账户名"],
            is_active=1,
        ))
        test_db.commit()

        conv = Conversation(
            title="测试",
            user_id=1,
            data_source_type="db",
            db_connection_id=1,
        )
        schema = [{"table_name": "orders", "columns": []}]
        text = format_synonyms_for_prompt(test_db, conv, schema)
        assert "表 orders:" in text
        assert "字段 amount | 标准词：销售额" in text
        assert "同义词：营收、销售收入" in text
        assert "users" not in text

    def test_format_synonyms_for_file_upload(self, test_db):
        test_db.add(DatasourceFieldLexicon(
            resource_type="file_upload",
            resource_id=2,
            table_name="sales_data",
            target_column="sales",
            standard_term="营收",
            synonyms=["销售额"],
            is_active=1,
        ))
        test_db.commit()

        conv = Conversation(
            title="文件问数",
            user_id=1,
            data_source_type="excel",
            file_upload_id=2,
        )
        schema = [{"table_name": "sales_data", "columns": []}]
        text = format_synonyms_for_prompt(test_db, conv, schema)
        assert "表 sales_data:" in text
        assert "字段 sales | 标准词：营收" in text
        assert "同义词：销售额" in text
