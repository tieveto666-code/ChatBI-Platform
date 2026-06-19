"""从解析后的 Excel/CSV 结构构建用于查询的 SQLite 文件。"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _sanitize_identifier(value: str, fallback: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(value).strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned.lower()


def _dedupe_identifier(base: str, used: set[str]) -> str:
    candidate = base
    index = 1
    while candidate in used:
        candidate = f"{base}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _quote_identifier(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) + chr(34))}"'


def build_file_query_db(parsed: list[dict[str, Any]], query_db_path: Path) -> tuple[list[dict], list[dict]]:
    """创建 query sqlite，返回 (schema_cache, mappings) 与上传接口逻辑一致。"""
    if query_db_path.exists():
        os.remove(str(query_db_path))

    schema_cache: list[dict] = []
    mappings: list[dict] = []
    conn = sqlite3.connect(str(query_db_path))
    try:
        for sheet_index, sheet in enumerate(parsed, start=1):
            table_name = _dedupe_identifier(
                _sanitize_identifier(sheet["table_name"], f"sheet_{sheet_index}"),
                {item["table_name"] for item in schema_cache},
            )

            used_columns: set[str] = set()
            columns = []
            for col_index, column in enumerate(sheet["columns"], start=1):
                source_name = str(column["name"])
                column_name = _dedupe_identifier(
                    _sanitize_identifier(source_name, f"col_{col_index}"),
                    used_columns,
                )
                columns.append({
                    "name": column_name,
                    "type": column.get("type") or "TEXT",
                    "original_name": source_name,
                })

            column_defs = ", ".join(
                f"{_quote_identifier(column['name'])} {column['type']}" for column in columns
            )
            conn.execute(f"CREATE TABLE {_quote_identifier(table_name)} ({column_defs})")

            rows = sheet.get("rows", [])
            if rows:
                placeholders = ", ".join(["?"] * len(columns))
                col_names = ", ".join(_quote_identifier(column["name"]) for column in columns)
                conn.executemany(
                    f"INSERT INTO {_quote_identifier(table_name)} ({col_names}) VALUES ({placeholders})",
                    [tuple((list(row) + [None] * len(columns))[:len(columns)]) for row in rows],
                )

            schema_cache.append({
                "sheet_name": sheet["sheet_name"],
                "table_name": table_name,
                "columns": columns,
                "row_count": len(rows),
            })
            mappings.append({
                "sheet_name": sheet["sheet_name"],
                "table_name": table_name,
                "columns": {
                    column["original_name"]: column["name"] for column in columns
                },
            })

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return schema_cache, mappings
