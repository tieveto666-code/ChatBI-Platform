from __future__ import annotations

import re
from datetime import datetime
from typing import Any

ChartType = str  # bar | line | bar_line | table

_TIME_NAME_RE = re.compile(
    r"(date|time|year|month|day|week|quarter|dt|period|created|updated|timestamp|"
    r"日期|时间|月份|年份|季度|周期)",
    re.I,
)

_MAX_CHART_ROWS = 50
_MAX_BAR_CATEGORIES = 30
_MAX_COLS_FOR_CHART = 4
_VISUAL_TYPES = ("bar", "line", "bar_line")


def has_visual_chart(payload: dict[str, Any]) -> bool:
    """载荷中是否包含可渲染的图表类型（非仅 table）。"""
    available = payload.get("available_types") or []
    return any(t in _VISUAL_TYPES for t in available)


def recommend_chart(result: dict[str, Any]) -> dict[str, Any]:
    """
    根据查询结果返回多种可用图表配置。
    载荷含 default_type、available_types、x_axis、options（各类型 series）。
    """
    columns = list(result.get("columns") or [])
    matrix = _normalize_rows(columns, result.get("rows") or [])
    row_count = len(matrix)

    if not columns or row_count == 0:
        return _empty_payload()

    col_kinds = [_infer_column_kind(columns[i], [r[i] for r in matrix]) for i in range(len(columns))]
    numeric_idxs = [i for i, k in enumerate(col_kinds) if k == "numeric"]
    time_idxs = [i for i, k in enumerate(col_kinds) if k == "time"]
    category_idxs = [i for i, k in enumerate(col_kinds) if k == "category"]

    available: list[ChartType] = ["table"]

    if not numeric_idxs:
        return {
            "default_type": "table",
            "available_types": available,
            "x_axis": [],
            "series": [],
            "options": {},
            "config": _config(columns),
        }

    if len(columns) > _MAX_COLS_FOR_CHART or row_count > 100:
        return {
            "default_type": "table",
            "available_types": available,
            "x_axis": [],
            "series": [],
            "options": {},
            "config": _config(columns),
        }

    x_idx = _pick_x_index(columns, col_kinds, time_idxs, category_idxs, numeric_idxs)
    x_labels = [_cell_str(row[x_idx]) for row in matrix]
    metrics = numeric_idxs[:2]
    config = _config(columns, x_idx, metrics[0])

    options: dict[str, dict[str, Any]] = {}

    if len(metrics) >= 1 and row_count <= _MAX_BAR_CATEGORIES:
        options["bar"] = {"series": _bar_series(columns, matrix, metrics)}

    if len(metrics) >= 1 and row_count >= 2 and row_count <= _MAX_CHART_ROWS:
        options["line"] = {"series": _line_series(columns, matrix, metrics)}

    if len(metrics) >= 2 and row_count >= 2 and row_count <= _MAX_CHART_ROWS:
        values_a = [_cell_float(row[metrics[0]]) for row in matrix]
        values_b = [_cell_float(row[metrics[1]]) for row in matrix]
        dual_axis = _needs_dual_axis(values_a, values_b)
        options["bar_line"] = {
            "series": [
                {
                    "name": str(columns[metrics[0]]),
                    "type": "bar",
                    "data": values_a,
                    "yAxisIndex": 0,
                },
                {
                    "name": str(columns[metrics[1]]),
                    "type": "line",
                    "data": values_b,
                    "yAxisIndex": 1 if dual_axis else 0,
                },
            ],
        }

    for t in _VISUAL_TYPES:
        if t in options:
            available.append(t)

    default_type = _pick_default_type(available, time_idxs, len(metrics), x_labels)
    active = options.get(default_type, {}).get("series", []) if default_type != "table" else []

    return {
        "default_type": default_type,
        "available_types": available,
        "type": default_type,
        "x_axis": x_labels if default_type != "table" else [],
        "series": active,
        "options": options,
        "config": config,
    }


def _pick_default_type(
    available: list[str],
    time_idxs: list[int],
    metric_count: int,
    x_labels: list[str],
) -> ChartType:
    visual = [t for t in available if t != "table"]
    if not visual:
        return "table"
    if metric_count >= 2 and "bar_line" in visual:
        return "bar_line"
    if time_idxs and "line" in visual:
        return "line"
    if _looks_sequential(x_labels) and "line" in visual:
        return "line"
    if "bar" in visual:
        return "bar"
    return visual[0]


def _bar_series(columns: list, matrix: list[list], metric_idxs: list[int]) -> list[dict]:
    return [
        {
            "name": str(columns[idx]),
            "type": "bar",
            "data": [_cell_float(row[idx]) for row in matrix],
            "yAxisIndex": 0,
        }
        for idx in metric_idxs
    ]


def _line_series(columns: list, matrix: list[list], metric_idxs: list[int]) -> list[dict]:
    return [
        {
            "name": str(columns[idx]),
            "type": "line",
            "data": [_cell_float(row[idx]) for row in matrix],
            "yAxisIndex": 0,
        }
        for idx in metric_idxs
    ]


def _empty_payload() -> dict[str, Any]:
    return {
        "default_type": "table",
        "available_types": ["table"],
        "type": "table",
        "x_axis": [],
        "series": [],
        "options": {},
        "config": {},
    }


def _normalize_rows(columns: list, rows: list) -> list[list]:
    out: list[list] = []
    for row in rows:
        if isinstance(row, dict):
            out.append([row.get(c) for c in columns])
        elif isinstance(row, (list, tuple)):
            out.append(list(row))
    return out


def _infer_column_kind(name: str, values: list) -> str:
    name_l = str(name).lower()
    if _TIME_NAME_RE.search(name_l):
        return "time"
    sample = [v for v in values[:20] if v is not None and str(v).strip() != ""]
    if not sample:
        return "category"
    if _ratio_numeric(sample) >= 0.8:
        return "numeric"
    if _ratio_time_values(sample) >= 0.6:
        return "time"
    return "category"


def _ratio_numeric(values: list) -> float:
    ok = 0
    for v in values:
        try:
            float(v)
            ok += 1
        except (TypeError, ValueError):
            pass
    return ok / len(values) if values else 0.0


def _ratio_time_values(values: list) -> float:
    ok = 0
    for v in values:
        if _parse_time(str(v)):
            ok += 1
    return ok / len(values) if values else 0.0


def _parse_time(text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if re.match(r"^\d{4}[-/年]\d{1,2}", text):
        return True
    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m", "%Y")
    for fmt in formats:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def _pick_x_index(
    columns: list,
    col_kinds: list[str],
    time_idxs: list[int],
    category_idxs: list[int],
    numeric_idxs: list[int],
) -> int:
    if time_idxs:
        return time_idxs[0]
    if category_idxs:
        return category_idxs[0]
    non_metric = [i for i in range(len(columns)) if i not in numeric_idxs]
    if non_metric:
        return non_metric[0]
    return 0


def _looks_sequential(labels: list[str]) -> bool:
    if len(labels) < 3:
        return False
    nums: list[float] = []
    for lb in labels:
        try:
            nums.append(float(lb))
        except ValueError:
            return False
    return all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1))


def _needs_dual_axis(a: list[float], b: list[float]) -> bool:
    max_a = max(abs(x) for x in a) or 1.0
    max_b = max(abs(x) for x in b) or 1.0
    ratio = max_a / max_b if max_b else max_a
    return ratio > 8 or ratio < 0.125


def _cell_str(val: Any) -> str:
    return "" if val is None else str(val)


def _cell_float(val: Any) -> float:
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _config(columns: list, x_idx: int | None = None, y_idx: int | None = None) -> dict[str, str]:
    cfg: dict[str, str] = {"title": ""}
    if x_idx is not None and x_idx < len(columns):
        cfg["x_label"] = str(columns[x_idx])
    if y_idx is not None and y_idx < len(columns):
        cfg["y_label"] = str(columns[y_idx])
    return cfg
