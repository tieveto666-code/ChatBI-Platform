from __future__ import annotations
"""
测试 Excel/CSV 解析器 — CSV 解析、列名冲突处理
"""

import os
import tempfile
import csv

import pytest

from services.excel_parser import ExcelParser
from core.exceptions import ValidationError

parser = ExcelParser()


class TestCSVParsing:
    """CSV 文件解析测试"""

    def test_simple_csv(self):
        """简单 CSV 文件解析"""
        content = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            assert len(result) == 1
            sheet = result[0]
            assert sheet["table_name"].startswith("test_csv")
            assert len(sheet["columns"]) == 3
            assert sheet["columns"][0]["name"] == "name"
            assert sheet["columns"][1]["name"] == "age"
            assert sheet["columns"][2]["name"] == "city"
            assert len(sheet["rows"]) == 2
        finally:
            os.unlink(file_path)

    def test_csv_with_empty_cells(self):
        """带空值的 CSV"""
        content = "name,email,phone\nAlice,alice@test.com,\nBob,,123456\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            assert len(result) == 1
            # 空值应该以 NaN 或 None 形式保留，pandas 会用 NaN 填充
            assert len(result[0]["rows"]) == 2
        finally:
            os.unlink(file_path)

    def test_csv_with_all_empty_rows(self):
        """全空行应被过滤"""
        content = "a,b,c\n1,2,3\n,,,\n4,5,6\n,,,\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            assert len(result) == 1
            # dropna(how="all") 会过滤全空行
            assert len(result[0]["rows"]) == 2  # 2 行有效数据
        finally:
            os.unlink(file_path)

    def test_csv_single_column(self):
        """单列 CSV"""
        content = "value\n1\n2\n3\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            assert len(result[0]["columns"]) == 1
            assert result[0]["columns"][0]["name"] == "value"
        finally:
            os.unlink(file_path)

    def test_csv_with_special_chars(self):
        """特殊字符列名"""
        content = "user id,first-name,last$name\n1,John,Doe\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            # pandas 会保留原始列名，不做转义
            assert len(result[0]["columns"]) == 3
        finally:
            os.unlink(file_path)

    def test_empty_csv(self):
        """空 CSV（只有表头）"""
        content = "name,age\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            # 只有表头没有数据行
            assert len(result) == 1
            assert len(result[0]["rows"]) == 0
        finally:
            os.unlink(file_path)

    def test_csv_type_inference_numeric(self):
        """数值列类型推断"""
        content = "value\n10\n20\n30\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            # dtype=str 读取后尝试推断
            assert result[0]["columns"][0]["type"] in ("REAL", "TEXT")
        finally:
            os.unlink(file_path)

    @staticmethod
    def _create_csv(content: str) -> str:
        """创建临时 CSV 文件"""
        fd, path = tempfile.mkstemp(suffix=".csv", prefix="test_csv_")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path


class TestColumnNameConflict:
    """列名冲突处理测试"""

    def test_unnamed_column(self):
        """空白列名应自动命名"""
        content = "name,,city\nAlice,30,Beijing\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            columns = result[0]["columns"]
            # 空白列名会被 pandas 转换为非空字符串
            col_names = [c["name"] for c in columns]
            assert len(col_names) == 3
            assert "" not in col_names
        finally:
            os.unlink(file_path)

    def test_duplicate_table_name(self):
        """重复表名应自动去重"""
        # 连续调用 parse 测试表名计数
        content1 = "a,b\n1,2\n"
        content2 = "c,d\n3,4\n"

        file1 = self._create_csv(content1, prefix="dup_test")
        file2 = self._create_csv(content2, prefix="dup_test")

        try:
            result1 = parser.parse(file1)
            table1 = result1[0]["table_name"]

            result2 = parser.parse(file2)
            table2 = result2[0]["table_name"]

            # 相同文件名的两个 CSV 表名应不同
            assert table1 != table2
        finally:
            for p in [file1, file2]:
                if os.path.exists(p):
                    os.unlink(p)

    @staticmethod
    def _create_csv(content: str, prefix: str = "test_csv") -> str:
        fd, path = tempfile.mkstemp(suffix=".csv", prefix=prefix)
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path


class TestCSVSchema:
    """CSV Schema 信息测试"""

    def test_get_schema_info(self):
        """解析结果包含完整的 schema 信息"""
        content = "id,name,age\n1,Alice,30\n2,Bob,25\n"
        file_path = self._create_csv(content)
        try:
            result = parser.parse(file_path)
            sheet = result[0]

            assert "sheet_name" in sheet
            assert "table_name" in sheet
            assert "columns" in sheet
            assert "rows" in sheet

            # Schema 信息
            assert len(sheet["columns"]) == 3
            for col in sheet["columns"]:
                assert "name" in col
                assert "type" in col

            # 数据行
            assert len(sheet["rows"]) == 2
            assert sheet["rows"][0] == ["1", "Alice", "30"]
        finally:
            os.unlink(file_path)

    @staticmethod
    def _create_csv(content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv", prefix="test_csv_")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path
