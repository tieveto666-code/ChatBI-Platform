from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from core.exceptions import BusinessError
from core.error_codes import ErrorCode
from models.conversation import Conversation
from models.datasource_field_lexicon import DatasourceFieldLexicon


def normalize_synonyms(raw: list[str] | None, standard_term: str = "") -> list[str]:
    """去重、去空，且不与标准词重复。"""
    std = standard_term.strip()
    seen: set[str] = set()
    result: list[str] = []
    for item in raw or []:
        s = str(item).strip()
        if not s or s == std or s in seen:
            continue
        seen.add(s)
        result.append(s)
    return result


def lexicon_to_dict(row: DatasourceFieldLexicon) -> dict:
    return {
        "id": row.id,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "table_name": row.table_name,
        "target_column": row.target_column,
        "standard_term": row.standard_term,
        "synonyms": normalize_synonyms(row.synonyms or [], row.standard_term),
        "created_at": str(row.created_at) if row.created_at else None,
        "updated_at": str(row.updated_at) if row.updated_at else None,
    }


def list_table_synonyms(
    db: Session,
    resource_type: str,
    resource_id: int,
    table_name: str | None = None,
) -> list[dict]:
    q = db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
        DatasourceFieldLexicon.is_active == 1,
    )
    if table_name:
        q = q.filter(DatasourceFieldLexicon.table_name == table_name)
    rows = q.order_by(
        DatasourceFieldLexicon.table_name,
        DatasourceFieldLexicon.target_column,
    ).all()
    return [lexicon_to_dict(r) for r in rows]


def _validate_column(table_name: str, target_column: str, schema_tables: list[dict]) -> None:
    table = next((t for t in schema_tables if t.get("table_name") == table_name), None)
    if not table:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"表 {table_name} 不存在",
        )
    col_names = {c.get("name") for c in (table.get("columns") or [])}
    if target_column not in col_names:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"字段 {target_column} 不在表 {table_name} 中",
        )


def _ensure_unique_column(
    db: Session,
    resource_type: str,
    resource_id: int,
    table_name: str,
    target_column: str,
    exclude_id: int | None = None,
) -> None:
    q = db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
        DatasourceFieldLexicon.table_name == table_name,
        DatasourceFieldLexicon.target_column == target_column,
        DatasourceFieldLexicon.is_active == 1,
    )
    if exclude_id is not None:
        q = q.filter(DatasourceFieldLexicon.id != exclude_id)
    if q.first():
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"字段 {target_column} 已配置术语，请编辑现有条目",
        )


def create_table_synonym(
    db: Session,
    resource_type: str,
    resource_id: int,
    table_name: str,
    target_column: str,
    standard_term: str,
    synonyms: list[str] | None,
    schema_tables: list[dict],
    created_by: int | None,
) -> dict:
    target_column = target_column.strip()
    standard_term = standard_term.strip()
    if not target_column or not standard_term:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="数据字段与标准词均不能为空")

    _validate_column(table_name, target_column, schema_tables)
    _ensure_unique_column(db, resource_type, resource_id, table_name, target_column)

    row = DatasourceFieldLexicon(
        resource_type=resource_type,
        resource_id=resource_id,
        table_name=table_name,
        target_column=target_column,
        standard_term=standard_term,
        synonyms=normalize_synonyms(synonyms, standard_term),
        created_by=created_by,
        is_active=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return lexicon_to_dict(row)


def update_table_synonym(
    db: Session,
    resource_type: str,
    resource_id: int,
    synonym_id: int,
    target_column: str | None,
    standard_term: str | None,
    synonyms: list[str] | None,
    schema_tables: list[dict],
) -> dict:
    row = db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.id == synonym_id,
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
        DatasourceFieldLexicon.is_active == 1,
    ).first()
    if not row:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="字段术语不存在")

    new_col = target_column.strip() if target_column is not None else row.target_column
    new_std = standard_term.strip() if standard_term is not None else row.standard_term
    if not new_col or not new_std:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="数据字段与标准词均不能为空")

    if new_col != row.target_column:
        _validate_column(row.table_name, new_col, schema_tables)
        _ensure_unique_column(
            db, resource_type, resource_id, row.table_name, new_col, exclude_id=synonym_id,
        )

    row.target_column = new_col
    row.standard_term = new_std
    if synonyms is not None:
        row.synonyms = normalize_synonyms(synonyms, new_std)
    else:
        row.synonyms = normalize_synonyms(row.synonyms or [], new_std)

    db.commit()
    db.refresh(row)
    return lexicon_to_dict(row)


def delete_table_synonym(
    db: Session,
    resource_type: str,
    resource_id: int,
    synonym_id: int,
) -> None:
    row = db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.id == synonym_id,
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
    ).first()
    if not row:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="字段术语不存在")
    db.delete(row)
    db.commit()


def delete_synonyms_for_resource(db: Session, resource_type: str, resource_id: int) -> None:
    db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
    ).delete()


def conversation_resource(conversation: Conversation) -> tuple[str, int] | None:
    dst = (conversation.data_source_type or "").lower()
    if dst in ("excel", "csv", "file") and conversation.file_upload_id:
        return "file_upload", conversation.file_upload_id
    if conversation.db_connection_id:
        return "db_connection", conversation.db_connection_id
    return None


def _format_lexicon_line(row: DatasourceFieldLexicon) -> str:
    syns = normalize_synonyms(row.synonyms or [], row.standard_term)
    syn_part = f"；同义词：{'、'.join(syns)}" if syns else ""
    return (
        f"  - 字段 {row.target_column} | 标准词：{row.standard_term}{syn_part}"
    )


def format_synonyms_for_prompt(
    db: Session,
    conversation: Conversation,
    schema_tables: list[dict],
) -> str:
    """按当前会话数据源与 Schema 表，收集字段术语并格式化为 Prompt 文本。"""
    resource = conversation_resource(conversation)
    if not resource:
        return ""

    resource_type, resource_id = resource
    table_names = {t.get("table_name") for t in schema_tables if t.get("table_name")}
    if not table_names:
        return ""

    rows = db.query(DatasourceFieldLexicon).filter(
        DatasourceFieldLexicon.resource_type == resource_type,
        DatasourceFieldLexicon.resource_id == resource_id,
        DatasourceFieldLexicon.table_name.in_(table_names),
        DatasourceFieldLexicon.is_active == 1,
    ).order_by(
        DatasourceFieldLexicon.table_name,
        DatasourceFieldLexicon.target_column,
    ).all()

    if not rows:
        return ""

    by_table: dict[str, list[DatasourceFieldLexicon]] = defaultdict(list)
    for row in rows:
        by_table[row.table_name].append(row)

    blocks: list[str] = []
    for table_name in sorted(by_table.keys()):
        lines = [_format_lexicon_line(r) for r in by_table[table_name]]
        blocks.append(f"表 {table_name}:\n" + "\n".join(lines))

    return "\n\n".join(blocks)


def migrate_legacy_table_synonyms(engine) -> None:
    """将旧版 term→column 同义词表迁移为字段术语结构。"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "datasource_field_lexicons" in inspector.get_table_names():
        return
    if "datasource_table_synonyms" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        legacy = conn.execute(text(
            "SELECT resource_type, resource_id, table_name, target_column, term "
            "FROM datasource_table_synonyms WHERE is_active = 1"
        )).fetchall()

        grouped: dict[tuple, list[str]] = defaultdict(list)
        for row in legacy:
            key = (row[0], row[1], row[2], row[3])
            term = (row[4] or "").strip()
            if term:
                grouped[key].append(term)

        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS datasource_field_lexicons ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "resource_type VARCHAR(32) NOT NULL, "
            "resource_id INTEGER NOT NULL, "
            "table_name VARCHAR(128) NOT NULL, "
            "target_column VARCHAR(128) NOT NULL, "
            "standard_term VARCHAR(128) NOT NULL, "
            "synonyms JSON NOT NULL, "
            "created_by INTEGER, "
            "is_active INTEGER NOT NULL DEFAULT 1, "
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "CONSTRAINT uq_datasource_field_lexicon_column "
            "UNIQUE (resource_type, resource_id, table_name, target_column))"
        ))

        for (resource_type, resource_id, table_name, target_column), terms in grouped.items():
            standard = terms[0]
            syns = terms[1:]
            conn.execute(
                text(
                    "INSERT INTO datasource_field_lexicons "
                    "(resource_type, resource_id, table_name, target_column, standard_term, synonyms, is_active) "
                    "VALUES (:rt, :rid, :tn, :col, :std, :syns, 1)"
                ),
                {
                    "rt": resource_type,
                    "rid": resource_id,
                    "tn": table_name,
                    "col": target_column,
                    "std": standard,
                    "syns": json.dumps(syns, ensure_ascii=False),
                },
            )

        conn.execute(text("DROP TABLE datasource_table_synonyms"))
