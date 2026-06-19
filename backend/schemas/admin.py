from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = None
    role_id: int = 3


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    role_id: int | None = None
    password: str | None = None


class UserInfo(BaseModel):
    id: int
    username: str
    email: str | None = None
    role_id: int | None = None
    role_name: str | None = None
    role_code: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    is_active: bool


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=64)
    code: str = Field(..., max_length=64)
    description: str | None = None
    sort_order: int = 0
    menu_ids: list[int] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    menu_ids: list[int] | None = None


class RoleInfo(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    is_system: bool
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MenuCreate(BaseModel):
    parent_id: int | None = None
    name: str = Field(..., max_length=64)
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    sort_order: int = 0
    is_visible: bool = True
    permission: str | None = None


class MenuUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    sort_order: int | None = None
    is_visible: bool | None = None
    permission: str | None = None


class MenuInfo(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    sort_order: int
    is_visible: bool
    permission: str | None = None
    children: list["MenuInfo"] = []

    class Config:
        from_attributes = True
