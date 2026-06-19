from __future__ import annotations
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from config import settings
from core.database import get_db
from core.dependencies import require_menu_path
from core.exceptions import BusinessError, ValidationError
from core.error_codes import ErrorCode
from models.user import User
from models.db_connection import DbConnection
from models.file_upload import FileUpload
from models.file_sheet import FileSheet
from schemas.datasource import (
    DbConnectionCreate, DbConnectionUpdate, DbConnectionInfo,
    FileUploadInfo,
    TableSynonymCreate, TableSynonymUpdate, TableSynonymInfo,
)
from schemas.common import ApiResponse
from services.excel_parser import ExcelParser
from services.schema_sync import SchemaSync
from services.file_query_db import build_file_query_db
from services.table_synonym_service import (
    list_table_synonyms,
    create_table_synonym,
    update_table_synonym,
    delete_table_synonym,
    delete_synonyms_for_resource,
)
from services.resource_access import (
    list_visible_db_connections,
    list_visible_file_uploads,
    require_datasource_permission,
)

router = APIRouter()
excel_parser = ExcelParser()
schema_sync = SchemaSync()


def _connection_schema_tables(conn: DbConnection, db: Session) -> list[dict]:
    if conn.schema_cache:
        try:
            return json.loads(conn.schema_cache)
        except json.JSONDecodeError:
            pass
    return schema_sync.sync_and_cache(conn, db)


def _file_schema_tables(db: Session, file_id: int) -> list[dict]:
    sheets = db.query(FileSheet).filter(FileSheet.file_upload_id == file_id).all()
    tables: list[dict] = []
    for sheet in sheets:
        columns = []
        if sheet.columns_schema:
            try:
                columns = json.loads(sheet.columns_schema)
            except json.JSONDecodeError:
                pass
        tables.append({
            "sheet_name": sheet.sheet_name,
            "table_name": sheet.table_name,
            "columns": columns,
        })
    return tables


# ════════════════════════════════════════════
# 文件上传
# ════════════════════════════════════════════


@router.post("/upload", response_model=ApiResponse[FileUploadInfo])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """上传 Excel/CSV 文件"""
    # 检查文件大小
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制",
        )

    # 检查文件类型
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValidationError(
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message=f"不支持的文件格式: {ext}，仅支持 {settings.ALLOWED_EXTENSIONS}",
        )

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    save_path = upload_dir / f"{file_id}{ext}"
    save_path.write_bytes(contents)

    # 解析文件
    try:
        parsed = excel_parser.parse(str(save_path))
    except ValidationError:
        os.remove(str(save_path))
        raise
    except Exception as e:
        os.remove(str(save_path))
        raise BusinessError(
            code=ErrorCode.FILE_PARSE_ERROR,
            message="文件解析失败",
            detail=str(e),
        )

    # 计算总行数和 sheets
    total_rows = len([r for sheets in parsed for r in sheets.get("rows", [])])
    sheet_count = len(parsed)

    # 写入数据库
    file_upload = FileUpload(
        filename=save_path.name,
        original_name=file.filename,
        file_path=str(save_path),
        file_size=file_size,
        sheet_count=sheet_count,
        total_rows=total_rows,
        status="parsed",
        created_by=current_user.id,
        visibility="private",
    )
    db.add(file_upload)
    db.flush()

    query_db_dir = Path(settings.FILE_DB_DIR)
    query_db_dir.mkdir(parents=True, exist_ok=True)
    query_db_path = query_db_dir / f"{file_upload.id}.sqlite"

    try:
        schema_cache, mappings = build_file_query_db(parsed, query_db_path)
    except Exception as e:
        db.rollback()
        if save_path.exists():
            os.remove(str(save_path))
        if query_db_path.exists():
            os.remove(str(query_db_path))
        raise BusinessError(
            code=ErrorCode.FILE_PARSE_ERROR,
            message="文件查询库创建失败",
            detail=str(e),
        )

    file_upload.query_db_path = str(query_db_path)
    file_upload.schema_cache = json.dumps(schema_cache, ensure_ascii=False)

    # 写入 Sheet 信息
    for sheet, mapping in zip(schema_cache, mappings):
        sheet_schema = json.dumps(sheet["columns"], ensure_ascii=False)
        file_sheet = FileSheet(
            file_upload_id=file_upload.id,
            sheet_name=sheet["sheet_name"],
            table_name=sheet["table_name"],
            column_count=len(sheet["columns"]),
            row_count=sheet["row_count"],
            columns_schema=sheet_schema,
            name_mapping_json=json.dumps(mapping, ensure_ascii=False),
        )
        db.add(file_sheet)

    db.commit()
    db.refresh(file_upload)

    return ApiResponse(data=FileUploadInfo(
        id=file_upload.id,
        original_name=file_upload.original_name,
        file_size=file_upload.file_size,
        query_db_ready=bool(file_upload.query_db_path),
        sheet_count=file_upload.sheet_count,
        total_rows=file_upload.total_rows,
        status=file_upload.status,
        created_at=str(file_upload.created_at) if file_upload.created_at else None,
    ))


@router.get("/files", response_model=ApiResponse)
async def list_files(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """获取上传文件列表（按资源权限过滤）"""
    visible = list_visible_file_uploads(db, current_user)
    total = len(visible)
    start = (page - 1) * page_size
    files = visible[start:start + page_size]

    items = [
        FileUploadInfo(
            id=upload.id,
            original_name=upload.original_name,
            file_size=upload.file_size,
            query_db_ready=bool(upload.query_db_path),
            sheet_count=upload.sheet_count,
            total_rows=upload.total_rows,
            status=upload.status,
            created_at=str(upload.created_at) if upload.created_at else None,
        )
        for upload in files
    ]
    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/files/{file_id}", response_model=ApiResponse[FileUploadInfo])
async def get_file(
    file_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """获取上传文件信息"""
    upload = require_datasource_permission(db, current_user, "file_upload", file_id, "use")
    return ApiResponse(data=FileUploadInfo(
        id=upload.id,
        original_name=upload.original_name,
        file_size=upload.file_size,
        query_db_ready=bool(upload.query_db_path),
        sheet_count=upload.sheet_count,
        total_rows=upload.total_rows,
        status=upload.status,
        created_at=str(upload.created_at) if upload.created_at else None,
    ))


@router.delete("/files/{file_id}", response_model=ApiResponse)
async def delete_file(
    file_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """删除上传文件"""
    upload = require_datasource_permission(db, current_user, "file_upload", file_id, "admin")

    db.query(FileSheet).filter(FileSheet.file_upload_id == file_id).delete()
    delete_synonyms_for_resource(db, "file_upload", file_id)
    if upload.file_path and os.path.exists(upload.file_path):
        os.remove(upload.file_path)
    if upload.query_db_path and os.path.exists(upload.query_db_path):
        os.remove(upload.query_db_path)

    db.delete(upload)
    db.commit()
    return ApiResponse(data={"message": "已删除"})


@router.get("/files/{file_id}/schema", response_model=ApiResponse)
async def get_file_schema(
    file_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """获取上传文件的 Schema"""
    upload = require_datasource_permission(db, current_user, "file_upload", file_id, "use")
    sheets = db.query(FileSheet).filter(FileSheet.file_upload_id == file_id).all()
    tables = []
    for sheet in sheets:
        columns = []
        if sheet.columns_schema:
            try:
                columns = json.loads(sheet.columns_schema)
            except json.JSONDecodeError:
                pass
        tables.append({
            "sheet_name": sheet.sheet_name,
            "table_name": sheet.table_name,
            "columns": columns,
        })

    return ApiResponse(data={"tables": tables})


def _quote_sqlite_ident(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) + chr(34))}"'


def _find_table_in_schema(schema_tables: list[dict], table_name: str) -> dict | None:
    return next((t for t in schema_tables if t.get("table_name") == table_name), None)


def _preview_rows_from_cursor(
    cur: sqlite3.Cursor,
    table_name: str,
    columns_meta: list[dict[str, str]],
) -> dict[str, Any]:
    colnames = [d[0] for d in cur.description] if cur.description else []
    if not columns_meta and colnames:
        columns_meta = [{"name": n, "type": "TEXT"} for n in colnames]
    rows_out: list[dict[str, str]] = []
    for row in cur.fetchall():
        row_dict: dict[str, str] = {}
        for i, col in enumerate(colnames):
            val = row[i]
            row_dict[col] = "" if val is None else str(val)
        rows_out.append(row_dict)
    return {
        "table_name": table_name,
        "columns": columns_meta,
        "rows": rows_out,
    }


def _fetch_connection_table_preview(
    db_conn: DbConnection,
    table_meta: dict,
    limit: int,
) -> dict[str, Any]:
    table_name = str(table_meta["table_name"])
    raw_cols = table_meta.get("columns") or []
    columns_meta = [
        {"name": str(c.get("name", "")), "type": str(c.get("type") or "TEXT")}
        for c in raw_cols
        if c.get("name")
    ]

    if db_conn.db_type == "sqlite":
        if not db_conn.db_path or not os.path.exists(db_conn.db_path):
            raise HTTPException(status_code=400, detail="SQLite 数据库文件不存在")
        qt = _quote_sqlite_ident(table_name)
        sqlite_conn = sqlite3.connect(db_conn.db_path)
        try:
            cur = sqlite_conn.execute(f"SELECT * FROM {qt} LIMIT ?", (limit,))
            return _preview_rows_from_cursor(cur, table_name, columns_meta)
        finally:
            sqlite_conn.close()

    from sqlalchemy import create_engine, text

    url = schema_sync._build_url(db_conn)
    connect_args = {"check_same_thread": False} if db_conn.db_type == "sqlite" else {}
    engine = create_engine(url, connect_args=connect_args)
    try:
        quoted = engine.dialect.identifier_preparer.quote(table_name)
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {quoted} LIMIT :lim"), {"lim": limit})
            colnames = list(result.keys())
            if not columns_meta and colnames:
                columns_meta = [{"name": n, "type": "TEXT"} for n in colnames]
            rows_out: list[dict[str, str]] = []
            for row in result:
                mapping = row._mapping
                rows_out.append({
                    col: "" if mapping[col] is None else str(mapping[col])
                    for col in colnames
                })
            return {
                "table_name": table_name,
                "columns": columns_meta,
                "rows": rows_out,
            }
    finally:
        engine.dispose()


@router.get("/files/{file_id}/preview", response_model=ApiResponse)
async def get_file_preview(
    file_id: int,
    limit: int = 100,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """按 Sheet 返回表格预览（从 query sqlite 读取，列名使用原始表头）。"""
    upload = require_datasource_permission(db, current_user, "file_upload", file_id, "use")
    if not upload.query_db_path or not os.path.exists(upload.query_db_path):
        raise HTTPException(status_code=400, detail="文件查询库未就绪")

    cap = min(max(limit, 1), 500)
    sheets_out: list[dict[str, Any]] = []
    file_sheets = db.query(FileSheet).filter(
        FileSheet.file_upload_id == file_id,
    ).order_by(FileSheet.id).all()

    conn = sqlite3.connect(upload.query_db_path)
    try:
        for fs in file_sheets:
            columns_meta: list[dict[str, str]] = []
            if fs.columns_schema:
                try:
                    raw_cols = json.loads(fs.columns_schema)
                except json.JSONDecodeError:
                    raw_cols = []
                for c in raw_cols:
                    if isinstance(c, dict):
                        db_col = str(c.get("name", ""))
                        orig = str(c.get("original_name") or c.get("name", ""))
                        columns_meta.append({
                            "key": orig,
                            "db_column": db_col,
                            "type": str(c.get("type") or "TEXT"),
                        })
            if not columns_meta:
                continue

            qt = _quote_sqlite_ident(fs.table_name)
            cur = conn.execute(f"SELECT * FROM {qt} LIMIT ?", (cap,))
            db_cols_order = [d[0] for d in cur.description] if cur.description else []
            db_to_display = {m["db_column"]: m["key"] for m in columns_meta}
            rows_out: list[dict[str, str]] = []
            for row in cur.fetchall():
                row_dict: dict[str, str] = {}
                for i, db_col in enumerate(db_cols_order):
                    display = db_to_display.get(db_col, db_col)
                    val = row[i]
                    row_dict[display] = "" if val is None else str(val)
                rows_out.append(row_dict)

            sheets_out.append({
                "sheet_name": fs.sheet_name,
                "columns": [{"name": m["key"], "type": m["type"]} for m in columns_meta],
                "rows": rows_out,
            })
    finally:
        conn.close()

    return ApiResponse(data={"sheets": sheets_out})


# ════════════════════════════════════════════
# 数据库连接
# ════════════════════════════════════════════


@router.get("/connections", response_model=ApiResponse)
async def list_connections(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """获取数据库连接列表（按资源权限过滤）"""
    visible = list_visible_db_connections(db, current_user)
    total = len(visible)
    start = (page - 1) * page_size
    connections = visible[start:start + page_size]

    items = []
    for conn in connections:
        items.append(DbConnectionInfo(
            id=conn.id,
            name=conn.name,
            db_type=conn.db_type,
            db_path=conn.db_path,
            host=conn.host,
            port=conn.port,
            database_name=conn.database_name,
            is_active=conn.is_active,
            created_at=str(conn.created_at) if conn.created_at else None,
        ))

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/connections", response_model=ApiResponse[DbConnectionInfo])
async def create_connection(
    request: DbConnectionCreate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """创建数据库连接"""
    conn = DbConnection(
        name=request.name,
        db_type=request.db_type,
        db_path=request.db_path,
        host=request.host,
        port=request.port,
        database_name=request.database_name,
        username=request.username,
        password=request.password,
        is_active=True,
        created_by=current_user.id,
        visibility="private",
    )
    db.add(conn)
    try:
        schema_sync.sync_and_cache(conn, db)
    except Exception:
        db.rollback()
        raise
    db.refresh(conn)

    return ApiResponse(data=DbConnectionInfo(
        id=conn.id,
        name=conn.name,
        db_type=conn.db_type,
        db_path=conn.db_path,
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        is_active=conn.is_active,
        created_at=str(conn.created_at) if conn.created_at else None,
    ))


@router.get("/connections/{connection_id}", response_model=ApiResponse[DbConnectionInfo])
async def get_connection(
    connection_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """获取数据库连接详情"""
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "use")
    return ApiResponse(data=DbConnectionInfo(
        id=conn.id,
        name=conn.name,
        db_type=conn.db_type,
        db_path=conn.db_path,
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        is_active=conn.is_active,
        created_at=str(conn.created_at) if conn.created_at else None,
    ))


@router.put("/connections/{connection_id}", response_model=ApiResponse[DbConnectionInfo])
async def update_connection(
    connection_id: int,
    request: DbConnectionUpdate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """更新数据库连接"""
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "edit")
    update_data = request.model_dump(exclude_none=True)
    update_data.pop("db_type", None)
    for key, value in update_data.items():
        if hasattr(conn, key):
            setattr(conn, key, value)

    if update_data.get("db_path"):
        conn.schema_cache = None
        schema_sync.sync_and_cache(conn, db)
    else:
        db.commit()
    db.refresh(conn)

    return ApiResponse(data=DbConnectionInfo(
        id=conn.id,
        name=conn.name,
        db_type=conn.db_type,
        db_path=conn.db_path,
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        is_active=conn.is_active,
        created_at=str(conn.created_at) if conn.created_at else None,
    ))


@router.delete("/connections/{connection_id}", response_model=ApiResponse)
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """删除数据库连接"""
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "admin")
    delete_synonyms_for_resource(db, "db_connection", connection_id)
    db.delete(conn)
    db.commit()

    return ApiResponse(data={"message": "已删除"})


@router.get("/connections/{connection_id}/schema", response_model=ApiResponse)
async def sync_connection_schema(
    connection_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """同步数据库连接的 Schema"""
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "use")
    try:
        tables = schema_sync.sync_and_cache(conn, db)
        return ApiResponse(data={"tables": tables})
    except Exception as e:
        raise BusinessError(
            code=ErrorCode.DATABASE_ERROR,
            message="Schema 同步失败",
            detail=str(e),
        )


@router.get("/connections/{connection_id}/tables/{table_name}/preview", response_model=ApiResponse)
async def preview_connection_table(
    connection_id: int,
    table_name: str,
    limit: int = 100,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    """预览数据库连接中指定表的数据（最多 500 行）。"""
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "use")
    schema_tables = _connection_schema_tables(conn, db)
    table_meta = _find_table_in_schema(schema_tables, table_name)
    if not table_meta:
        raise HTTPException(status_code=404, detail="表不存在或未同步 Schema")

    cap = min(max(limit, 1), 500)
    try:
        data = _fetch_connection_table_preview(conn, table_meta, cap)
    except HTTPException:
        raise
    except Exception as e:
        raise BusinessError(
            code=ErrorCode.DATABASE_ERROR,
            message="表数据预览失败",
            detail=str(e),
        )
    return ApiResponse(data=data)


# ════════════════════════════════════════════
# 表级同义词
# ════════════════════════════════════════════


@router.get("/connections/{connection_id}/tables/{table_name}/synonyms", response_model=ApiResponse)
async def list_connection_table_synonyms(
    connection_id: int,
    table_name: str,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "db_connection", connection_id, "use")
    items = list_table_synonyms(db, "db_connection", connection_id, table_name)
    return ApiResponse(data={"items": items})


@router.post("/connections/{connection_id}/tables/{table_name}/synonyms", response_model=ApiResponse[TableSynonymInfo])
async def create_connection_table_synonym(
    connection_id: int,
    table_name: str,
    request: TableSynonymCreate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "edit")
    schema_tables = _connection_schema_tables(conn, db)
    item = create_table_synonym(
        db, "db_connection", connection_id, table_name,
        request.target_column, request.standard_term, request.synonyms,
        schema_tables, current_user.id,
    )
    return ApiResponse(data=item)


@router.put("/connections/{connection_id}/synonyms/{synonym_id}", response_model=ApiResponse[TableSynonymInfo])
async def update_connection_table_synonym(
    connection_id: int,
    synonym_id: int,
    request: TableSynonymUpdate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    conn = require_datasource_permission(db, current_user, "db_connection", connection_id, "edit")
    schema_tables = _connection_schema_tables(conn, db)
    item = update_table_synonym(
        db, "db_connection", connection_id, synonym_id,
        request.target_column, request.standard_term, request.synonyms, schema_tables,
    )
    return ApiResponse(data=item)


@router.delete("/connections/{connection_id}/synonyms/{synonym_id}", response_model=ApiResponse)
async def delete_connection_table_synonym(
    connection_id: int,
    synonym_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "db_connection", connection_id, "edit")
    delete_table_synonym(db, "db_connection", connection_id, synonym_id)
    return ApiResponse(data={"message": "已删除"})


@router.get("/files/{file_id}/tables/{table_name}/synonyms", response_model=ApiResponse)
async def list_file_table_synonyms(
    file_id: int,
    table_name: str,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "file_upload", file_id, "use")
    items = list_table_synonyms(db, "file_upload", file_id, table_name)
    return ApiResponse(data={"items": items})


@router.post("/files/{file_id}/tables/{table_name}/synonyms", response_model=ApiResponse[TableSynonymInfo])
async def create_file_table_synonym(
    file_id: int,
    table_name: str,
    request: TableSynonymCreate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "file_upload", file_id, "edit")
    schema_tables = _file_schema_tables(db, file_id)
    item = create_table_synonym(
        db, "file_upload", file_id, table_name,
        request.target_column, request.standard_term, request.synonyms,
        schema_tables, current_user.id,
    )
    return ApiResponse(data=item)


@router.put("/files/{file_id}/synonyms/{synonym_id}", response_model=ApiResponse[TableSynonymInfo])
async def update_file_table_synonym(
    file_id: int,
    synonym_id: int,
    request: TableSynonymUpdate,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "file_upload", file_id, "edit")
    schema_tables = _file_schema_tables(db, file_id)
    item = update_table_synonym(
        db, "file_upload", file_id, synonym_id,
        request.target_column, request.standard_term, request.synonyms, schema_tables,
    )
    return ApiResponse(data=item)


@router.delete("/files/{file_id}/synonyms/{synonym_id}", response_model=ApiResponse)
async def delete_file_table_synonym(
    file_id: int,
    synonym_id: int,
    current_user: User = Depends(require_menu_path("/datasources")),
    db: Session = Depends(get_db),
):
    require_datasource_permission(db, current_user, "file_upload", file_id, "edit")
    delete_table_synonym(db, "file_upload", file_id, synonym_id)
    return ApiResponse(data={"message": "已删除"})
