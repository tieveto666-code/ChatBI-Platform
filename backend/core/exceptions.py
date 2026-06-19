from __future__ import annotations
class ChatBIException(Exception):
    """业务异常基类"""

    def __init__(self, code: int, message: str, detail: str | None = None):
        self.code = code
        self.message = message
        self.detail = detail


class AuthError(ChatBIException):
    """1000-1999: 认证错误"""
    pass


class ValidationError(ChatBIException):
    """2000-2999: 参数错误"""
    pass


class BusinessError(ChatBIException):
    """3000-3999: 业务错误"""
    pass


class PermissionError(ChatBIException):
    """4000-4999: 权限错误"""
    pass


class SystemError(ChatBIException):
    """5000-5999: 系统错误"""
    pass
