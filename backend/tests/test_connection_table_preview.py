"""数据库连接表数据预览 API 测试"""

from __future__ import annotations

import json
import sqlite3

import pytest

from models.db_connection import DbConnection


@pytest.mark.asyncio
async def test_connection_table_preview(test_client, auth_headers, test_db, tmp_path):
    db_path = tmp_path / "biz.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE orders (amount REAL, qty INTEGER)")
    conn.execute("INSERT INTO orders VALUES (100.5, 2)")
    conn.execute("INSERT INTO orders VALUES (200.0, 5)")
    conn.commit()
    conn.close()

    dc = test_db.query(DbConnection).filter(DbConnection.id == 1).one()
    dc.db_path = str(db_path)
    dc.schema_cache = json.dumps([{
        "table_name": "orders",
        "columns": [
            {"name": "amount", "type": "REAL"},
            {"name": "qty", "type": "INTEGER"},
        ],
    }], ensure_ascii=False)
    test_db.commit()

    resp = await test_client.get(
        "/api/datasources/connections/1/tables/orders/preview",
        headers=auth_headers,
        params={"limit": 10},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["table_name"] == "orders"
    assert len(data["rows"]) == 2
    assert data["rows"][0]["amount"] == "100.5"
    assert data["rows"][0]["qty"] == "2"


@pytest.mark.asyncio
async def test_connection_table_preview_not_found(test_client, auth_headers, test_db):
    dc = test_db.query(DbConnection).filter(DbConnection.id == 1).one()
    dc.schema_cache = json.dumps([{
        "table_name": "orders",
        "columns": [{"name": "id", "type": "INTEGER"}],
    }])
    test_db.commit()

    resp = await test_client.get(
        "/api/datasources/connections/1/tables/missing_table/preview",
        headers=auth_headers,
    )
    assert resp.status_code == 404
