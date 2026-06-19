from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Generic, TypeVar

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """统一响应信封"""
    code: int = 0
    message: str = "success"
    data: DataT | None = None


class PaginatedData(BaseModel, Generic[DataT]):
    """分页数据结构"""
    items: list[DataT]
    total: int
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: str | None = None
