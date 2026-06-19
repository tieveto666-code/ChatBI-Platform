"""
测试管理后台 — 用户/角色/菜单 CRUD + 权限守卫
"""

import pytest
from httpx import AsyncClient


class TestAdminUserManage:
    """用户管理测试"""

    @pytest.mark.asyncio
    async def test_list_users(self, test_client: AsyncClient, test_db, auth_headers):
        """获取用户列表"""
        response = await test_client.get(
            "/api/admin/users",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert data["data"]["total"] >= 4

    @pytest.mark.asyncio
    async def test_list_users_with_keyword(self, test_client: AsyncClient, test_db, auth_headers):
        """关键词搜索用户"""
        response = await test_client.get(
            "/api/admin/users?keyword=admin",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert any(u["username"] == "admin" for u in data["data"]["items"])

    @pytest.mark.asyncio
    async def test_get_user_detail(self, test_client: AsyncClient, test_db, auth_headers):
        """获取指定用户"""
        response = await test_client.get(
            "/api/admin/users/1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == 1

    @pytest.mark.asyncio
    async def test_create_user(self, test_client: AsyncClient, test_db, auth_headers):
        """创建用户"""
        response = await test_client.post(
            "/api/admin/users",
            headers=auth_headers,
            json={
                "username": "new_admin_user",
                "password": "password123",
                "email": "newadmin@test.com",
                "role_id": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "new_admin_user"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, test_client: AsyncClient, test_db, auth_headers):
        """重复用户名"""
        response = await test_client.post(
            "/api/admin/users",
            headers=auth_headers,
            json={
                "username": "admin",
                "password": "password123",
                "email": "dup@test.com",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "已被注册" in data["message"]

    @pytest.mark.asyncio
    async def test_update_user(self, test_client: AsyncClient, test_db, auth_headers):
        """更新用户"""
        response = await test_client.put(
            "/api/admin/users/1",
            headers=auth_headers,
            json={"username": "admin_updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "admin_updated"

    @pytest.mark.asyncio
    async def test_disable_user(self, test_client: AsyncClient, test_db, auth_headers):
        """禁用用户"""
        response = await test_client.put(
            "/api/admin/users/2/status",
            headers=auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_user(self, test_client: AsyncClient, test_db, auth_headers):
        """删除用户"""
        response = await test_client.delete(
            "/api/admin/users/3",  # testuser
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestAdminRoleManage:
    """角色管理测试"""

    @pytest.mark.asyncio
    async def test_list_roles(self, test_client: AsyncClient, test_db, auth_headers):
        """获取角色列表"""
        response = await test_client.get(
            "/api/admin/roles",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 3

    @pytest.mark.asyncio
    async def test_create_role(self, test_client: AsyncClient, test_db, auth_headers):
        """创建角色"""
        response = await test_client.post(
            "/api/admin/roles",
            headers=auth_headers,
            json={
                "name": "访客",
                "code": "guest",
                "description": "仅可查看",
                "sort_order": 4,
                "menu_ids": [1],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "访客"
        assert data["data"]["code"] == "guest"

    @pytest.mark.asyncio
    async def test_create_duplicate_role_code(self, test_client: AsyncClient, test_db, auth_headers):
        """重复角色编码"""
        response = await test_client.post(
            "/api/admin/roles",
            headers=auth_headers,
            json={"name": "重复管理员", "code": "admin"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_role_detail(self, test_client: AsyncClient, test_db, auth_headers):
        """获取角色详情"""
        response = await test_client.get(
            "/api/admin/roles/1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "超级管理员"

    @pytest.mark.asyncio
    async def test_update_role(self, test_client: AsyncClient, test_db, auth_headers):
        """更新角色"""
        response = await test_client.put(
            "/api/admin/roles/2",
            headers=auth_headers,
            json={"name": "高级分析师"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "高级分析师"

    @pytest.mark.asyncio
    async def test_delete_system_role_fails(self, test_client: AsyncClient, test_db, auth_headers):
        """系统角色不可删除"""
        response = await test_client.delete(
            "/api/admin/roles/1",  # admin = 系统角色
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.json()
        assert "不可删除" in data["message"]

    @pytest.mark.asyncio
    async def test_create_and_delete_custom_role(self, test_client: AsyncClient, test_db, auth_headers):
        """创建并删除自定义角色"""
        # 创建
        create_resp = await test_client.post(
            "/api/admin/roles",
            headers=auth_headers,
            json={"name": "临时角色", "code": "temp_role"},
        )
        role_id = create_resp.json()["data"]["id"]

        # 删除
        delete_resp = await test_client.delete(
            f"/api/admin/roles/{role_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 200


class TestAdminMenuManage:
    """菜单管理测试"""

    @pytest.mark.asyncio
    async def test_list_menus_as_tree(self, test_client: AsyncClient, test_db, auth_headers):
        """获取树形菜单"""
        response = await test_client.get(
            "/api/admin/menus",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        assert len(items) >= 3
        assert all(m.get("parent_id") is None for m in items)

    @pytest.mark.asyncio
    async def test_create_menu(self, test_client: AsyncClient, test_db, auth_headers):
        """创建菜单"""
        response = await test_client.post(
            "/api/admin/menus",
            headers=auth_headers,
            json={
                "name": "测试菜单",
                "path": "/test",
                "icon": "TestIcon",
                "sort_order": 50,
                "parent_id": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "测试菜单"

    @pytest.mark.asyncio
    async def test_create_sub_menu(self, test_client: AsyncClient, test_db, auth_headers):
        """创建子菜单"""
        response = await test_client.post(
            "/api/admin/menus",
            headers=auth_headers,
            json={
                "name": "子菜单",
                "path": "/admin/sub",
                "parent_id": 10,
                "sort_order": 5,
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_menu(self, test_client: AsyncClient, test_db, auth_headers):
        """更新菜单"""
        response = await test_client.put(
            "/api/admin/menus/1",
            headers=auth_headers,
            json={"name": "对话分析(已更新)"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "对话分析(已更新)"

    @pytest.mark.asyncio
    async def test_delete_menu(self, test_client: AsyncClient, test_db, auth_headers):
        """删除菜单"""
        response = await test_client.delete(
            "/api/admin/menus/3",  # 智能体配置
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestAdminPermission:
    """权限守卫测试"""

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_users(self, test_client: AsyncClient, test_db, user_auth_headers):
        """非 admin 用户不可访问用户管理"""
        response = await test_client.get(
            "/api/admin/users",
            headers=user_auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_role(self, test_client: AsyncClient, test_db, user_auth_headers):
        """非 admin 用户不可创建角色"""
        response = await test_client.post(
            "/api/admin/roles",
            headers=user_auth_headers,
            json={"name": "test", "code": "test"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_delete_menu(self, test_client: AsyncClient, test_db, user_auth_headers):
        """非 admin 用户不可删除菜单"""
        response = await test_client.delete(
            "/api/admin/menus/1",
            headers=user_auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthorized_no_token(self, test_client: AsyncClient, test_db):
        """无 token 不可访问 admin 接口"""
        response = await test_client.get("/api/admin/users")
        assert response.status_code == 403
