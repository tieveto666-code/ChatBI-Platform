"""
测试认证模块 — 注册/登录/Token 刷新/获取用户信息
"""

from httpx import AsyncClient
import pytest


class TestAuthRegister:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, test_client: AsyncClient, test_db):
        """正常注册"""
        response = await test_client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "newpass123", "email": "new@test.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "newuser"
        assert data["data"]["email"] == "new@test.com"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, test_client: AsyncClient, test_db):
        """重复用户名注册"""
        response = await test_client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "admin123", "email": "admin2@test.com"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "已被注册" in data["message"] or data["code"] != 0

    @pytest.mark.asyncio
    async def test_register_short_password(self, test_client: AsyncClient, test_db):
        """密码过短"""
        response = await test_client.post(
            "/api/auth/register",
            json={"username": "shortpwd", "password": "123", "email": "short@test.com"},
        )
        assert response.status_code == 422  # Pydantic 校验失败

    @pytest.mark.asyncio
    async def test_register_empty_username(self, test_client: AsyncClient, test_db):
        """用户名为空"""
        response = await test_client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "test123456", "email": "ab@test.com"},
        )
        assert response.status_code == 422


class TestAuthLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient, test_db):
        """正常登录"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["user"]["username"] == "admin"

    @pytest.mark.asyncio
    async def test_login_user_without_role_id(self, test_client: AsyncClient, test_db):
        """role_id 为空时登录响应仍可序列化（避免 500）"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "norole", "password": "norole123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["user"]["role_id"] is None
        assert data["data"]["user"]["username"] == "norole"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient, test_db):
        """错误密码"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code in (400, 401)
        data = response.json()
        assert "错误" in data["message"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_client: AsyncClient, test_db):
        """不存在的用户"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "test123"},
        )
        assert response.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_login_disabled_user(self, test_client: AsyncClient, test_db):
        """已禁用的用户登录"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "disabled_user", "password": "disabled123"},
        )
        assert response.status_code in (400, 403)
        data = response.json()
        assert "禁用" in data["message"]


class TestAuthRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, test_client: AsyncClient, test_db, auth_headers):
        """成功刷新 token"""
        # 获取 token
        login_resp = await test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_resp.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, test_client: AsyncClient, test_db):
        """无效 token 刷新"""
        response = await test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-xxx"},
        )
        assert response.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_logout(self, test_client: AsyncClient, test_db, auth_headers):
        """退出登录"""
        response = await test_client.post(
            "/api/auth/logout",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestAuthUserInfo:
    """用户信息获取测试"""

    @pytest.mark.asyncio
    async def test_get_me(self, test_client: AsyncClient, test_db, auth_headers):
        """获取当前用户信息"""
        response = await test_client.get(
            "/api/auth/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "admin"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, test_client: AsyncClient, test_db):
        """未认证访问"""
        response = await test_client.get("/api/auth/me")
        assert response.status_code == 403
