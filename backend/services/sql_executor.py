from __future__ import annotations
import time
from typing import Any

from sqlalchemy import create_engine, text

from config import settings
from core.exceptions import BusinessError
from core.error_codes import ErrorCode


class SQLExecutor:
    """SQL 执行器 — 执行 SQL 并返回结构化结果"""

    def execute(
        self,
        sql: str,
        db_path_or_url: str | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        """
        执行 SQL 查询，返回结构化结果。

        Returns:
            {"columns": [...], "rows": [...], "total_rows": int, "execution_time_ms": int}
        """
        url = db_path_or_url or settings.DATABASE_URL
        limit = max_rows or settings.SQL_MAX_RESULT_ROWS

        # 对 SQLite 文件路径做转换
        if url.startswith("sqlite:///"):
            # 已经是正确格式
            pass
        elif url.endswith(".db") or url.endswith(".sqlite"):
            url = f"sqlite:///{url}"

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if "sqlite" in url else {},
        )

        start_time = time.time()
        try:
            with engine.connect() as conn:
                if settings.SQL_ENABLE_QUERY_ONLY and "sqlite" in url:
                    conn.execute(text("PRAGMA query_only = ON"))
                result = conn.execute(text(sql))

                columns = list(result.keys())
                rows = []
                count = 0
                for row in result:
                    rows.append(list(row))
                    count += 1
                    if count >= limit:
                        break

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "columns": columns,
                "rows": rows,
                "total_rows": len(rows),
                "execution_time_ms": execution_time,
            }
        except Exception as e:
            raise BusinessError(
                code=ErrorCode.SQL_EXECUTION_ERROR,
                message="SQL 执行失败",
                detail=str(e),
            )
        finally:
            engine.dispose()
