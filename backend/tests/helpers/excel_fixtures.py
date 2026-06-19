"""Excel/CSV 上传与文件查询库测试辅助。"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from models.file_upload import FileUpload
from services.excel_parser import ExcelParser
from services.file_query_db import build_file_query_db

SAMPLE_SALES_CSV = (
    "product_name,sales\n"
    "Apple,100\n"
    "Banana,50\n"
    "Cherry,80\n"
    "Date,120\n"
    "Elderberry,90\n"
)


def create_file_upload_from_csv(
    db: Session,
    work_dir: Path,
    csv_content: str = SAMPLE_SALES_CSV,
    filename: str = "sales_data.csv",
) -> tuple[FileUpload, list[dict]]:
    """解析 CSV、构建 query sqlite，并写入 file_uploads 记录。"""
    work_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = work_dir / "uploads"
    file_dbs_dir = work_dir / "file_dbs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_dbs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = uploads_dir / filename
    csv_path.write_text(csv_content, encoding="utf-8")

    parsed = ExcelParser().parse(str(csv_path))
    query_db_path = file_dbs_dir / "test_query.sqlite"
    schema_cache, _mappings = build_file_query_db(parsed, query_db_path)

    upload = FileUpload(
        filename=filename,
        original_name=filename,
        file_path=str(csv_path),
        query_db_path=str(query_db_path),
        file_size=csv_path.stat().st_size,
        sheet_count=len(parsed),
        total_rows=sum(len(sheet.get("rows", [])) for sheet in parsed),
        schema_cache=json.dumps(schema_cache, ensure_ascii=False),
        status="parsed",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload, schema_cache
