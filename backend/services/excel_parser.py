from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings
from core.exceptions import BusinessError, ValidationError
from core.error_codes import ErrorCode


class ExcelParser:
    """
    Excel/CSV 文件解析器。
    支持 xlsx (openpyxl) 和 csv (pandas) 格式。
    返回结构化 Schema 和数据。
    """

    # 用于列名冲突处理的计数器
    _table_counter: dict[str, int] = {}

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """
        解析 Excel/CSV 文件。

        Returns:
            list of {
                "sheet_name": str,
                "table_name": str,
                "columns": [{"name": str, "type": str}],
                "rows": [list],
            }
        """
        ext = Path(file_path).suffix.lower()

        if ext in (".xlsx", ".xls"):
            return self._parse_excel(file_path)
        elif ext == ".csv":
            return self._parse_csv(file_path)
        else:
            raise ValidationError(
                code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                message=f"不支持的文件格式: {ext}",
            )

    def _parse_excel(self, file_path: str) -> list[dict[str, Any]]:
        """使用 openpyxl/pandas 解析 Excel 文件"""
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = xl.sheet_names

        if len(sheet_names) > settings.MAX_SHEET_COUNT:
            raise ValidationError(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Sheet 数量 ({len(sheet_names)}) 超过限制 ({settings.MAX_SHEET_COUNT})",
            )

        results = []
        total_rows = 0
        used_table_names: set = set()

        for sheet_name in sheet_names:
            df = xl.parse(sheet_name, dtype=str)
            df = df.dropna(how="all").reset_index(drop=True)

            if df.empty:
                continue

            if len(df.columns) > settings.MAX_COLUMN_COUNT:
                raise ValidationError(
                    code=ErrorCode.FILE_PARSE_ERROR,
                    message=f"Sheet '{sheet_name}' 列数 ({len(df.columns)}) 超过限制 ({settings.MAX_COLUMN_COUNT})",
                )

            # 列名冲突处理
            table_name = self._generate_table_name(sheet_name, used_table_names)

            columns = []
            for col in df.columns:
                col_str = str(col)
                if col_str.strip() == "":
                    col_str = f"{table_name}_unnamed"
                col_type = self._infer_column_type(df[col])
                columns.append({"name": col_str, "type": col_type})

            rows = df.values.tolist()
            total_rows += len(rows)

            results.append({
                "sheet_name": sheet_name,
                "table_name": table_name,
                "columns": columns,
                "rows": rows,
            })

        if total_rows > settings.MAX_TOTAL_ROWS:
            raise ValidationError(
                code=ErrorCode.MEMORY_LIMIT_EXCEEDED,
                message=f"总行数 ({total_rows}) 超过限制 ({settings.MAX_TOTAL_ROWS})",
            )

        return results

    def _parse_csv(self, file_path: str) -> list[dict[str, Any]]:
        """使用 pandas 解析 CSV 文件"""
        df = pd.read_csv(file_path, dtype=str, engine="python", on_bad_lines="skip")
        df = df.replace(r"^\s*$", pd.NA, regex=True)
        df = df.dropna(how="all").reset_index(drop=True)

        table_name = Path(file_path).stem
        # 清理表名中的特殊字符
        table_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name)

        columns = []
        for col in df.columns:
            col_str = str(col)
            col_type = self._infer_column_type(df[col])
            columns.append({"name": col_str, "type": col_type})

        rows = df.values.tolist()

        return [{
            "sheet_name": Path(file_path).stem,
            "table_name": table_name,
            "columns": columns,
            "rows": rows,
        }]

    def _generate_table_name(self, sheet_name: str, used_names: set) -> str:
        """生成唯一的表名，处理列名冲突"""
        # 清理 Sheet 名
        base = "".join(c if c.isalnum() or c == "_" else "_" for c in sheet_name)
        if not base or base[0].isdigit():
            base = f"sheet_{base}"

        # 处理重名：自动加表名前缀
        table_name = f"tbl_{base}"
        counter = 1
        while table_name in used_names:
            table_name = f"tbl_{base}_{counter}"
            counter += 1

        used_names.add(table_name)
        return table_name

    def _infer_column_type(self, series: pd.Series) -> str:
        """推断列的数据类型"""
        # 只取前 100 个非空值推断类型
        sample = series.dropna().head(100)

        if sample.empty:
            return "TEXT"

        try:
            pd.to_numeric(sample)
            return "REAL"
        except (ValueError, TypeError):
            pass

        try:
            pd.to_datetime(sample)
            return "TEXT"  # SQLite 没有 DATE 类型，用 TEXT 存储
        except (ValueError, TypeError):
            pass

        return "TEXT"

    def estimate_memory(self, results: list[dict]) -> int:
        """估算解析结果的内存占用（字节）"""
        import sys
        total = 0
        for sheet in results:
            for row in sheet.get("rows", []):
                for cell in row:
                    total += sys.getsizeof(str(cell))
        return total
