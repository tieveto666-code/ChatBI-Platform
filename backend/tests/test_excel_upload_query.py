"""
Excel/CSV 上传 → NL2SQL 查询 API 级集成测试
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from config import settings
from llm.mock_provider import MockLLMProvider
from tests.helpers.excel_fixtures import SAMPLE_SALES_CSV


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event = ""
    for line in body.splitlines():
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: ") and current_event:
            events.append((current_event, json.loads(line[6:])))
            current_event = ""
    return events


@pytest.mark.asyncio
async def test_upload_csv_then_chat_stream(test_client, auth_headers, test_db, tmp_path, monkeypatch):
    """API 级闭环：上传 CSV → SSE 对话查询 → 返回 SQL 与表格"""
    upload_dir = tmp_path / "uploads"
    file_db_dir = tmp_path / "file_dbs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(settings, "FILE_DB_DIR", str(file_db_dir))

    files = {"file": ("sales_data.csv", SAMPLE_SALES_CSV.encode("utf-8"), "text/csv")}
    upload_resp = await test_client.post(
        "/api/datasources/upload",
        files=files,
        headers=auth_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    upload_data = upload_resp.json()["data"]
    file_upload_id = upload_data["id"]
    assert upload_data["query_db_ready"] is True

    schema_resp = await test_client.get(
        f"/api/datasources/files/{file_upload_id}/schema",
        headers=auth_headers,
    )
    assert schema_resp.status_code == 200, schema_resp.text
    tables = schema_resp.json()["data"]["tables"]
    assert len(tables) >= 1
    table_name = tables[0]["table_name"]
    columns = [c["name"] for c in tables[0]["columns"]]
    assert "product_name" in columns
    assert "sales" in columns

    query_text = "查询销售额最高的前5个商品"
    mock_sql = f"SELECT product_name, sales FROM {table_name} ORDER BY sales DESC LIMIT 5"

    with patch.dict(MockLLMProvider.QA_MAP, {query_text: mock_sql}, clear=False):
        response = await test_client.post(
            "/api/chat/stream",
            json={
                "message": query_text,
                "data_source_type": "excel",
                "file_upload_id": file_upload_id,
            },
            headers=auth_headers,
        )
    assert response.status_code == 200, response.text

    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "sql" in event_names
    assert "table" in event_names
    assert "done" in event_names
    assert "error" not in event_names

    sql_payload = next(data for name, data in events if name == "sql")
    assert table_name in sql_payload.get("sql", "")

    table_payload = next(data for name, data in events if name == "table")
    assert len(table_payload.get("rows", [])) == 5
