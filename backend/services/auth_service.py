from __future__ import annotations
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
import hashlib
import bcrypt
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AuthError, ValidationError
from core.error_codes import ErrorCode
from models.user import User


class AuthService:
    """认证服务 — 注册、登录、JWT Token 管理"""

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
        ).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        if password_hash.startswith("$2"):
            try:
                return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
            except (ValueError, TypeError):
                return False
        # Backward compatibility for existing seed/registered users.
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

    @staticmethod
    def register(
        db: Session,
        username: str,
        password: str,
        email: str | None = None,
    ) -> User:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValidationError(
                code=ErrorCode.USERNAME_EXISTS,
                message="用户名已被注册",
            )

        password_hash = AuthService._hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role_id=3,  # 默认普通用户角色
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> User:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise AuthError(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="用户名或密码错误",
            )
        if not user.is_active:
            raise AuthError(
                code=ErrorCode.FORBIDDEN,
                message="用户已被禁用",
            )
        if not AuthService._verify_password(password, user.password_hash):
            raise AuthError(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="用户名或密码错误",
            )
        return user

    @staticmethod
    def create_token(user: User) -> dict:
        expires_in = settings.JWT_EXPIRATION_HOURS * 3600
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role_code": user.role.code if user.role else "user",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        access_token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError:
            raise AuthError(
                code=ErrorCode.TOKEN_INVALID,
                message="Token 无效或已过期",
            )
