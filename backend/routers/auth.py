from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.exceptions import AuthError
from core.error_codes import ErrorCode
from core.dependencies import get_current_user
from models.user import User
from schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, UserInfo,
)
from schemas.common import ApiResponse
from services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=ApiResponse[UserInfo])
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    user = auth_service.register(
        db=db,
        username=request.username,
        password=request.password,
        email=request.email,
    )
    return ApiResponse(data=UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_code=user.role.code if user.role else None,
        is_active=user.is_active,
    ))


@router.post("/login", response_model=ApiResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = auth_service.authenticate(
        db=db,
        username=request.username,
        password=request.password,
    )
    token_data = auth_service.create_token(user)
    return ApiResponse(data={
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "user": UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role_id=user.role_id,
            role_name=user.role.name if user.role else None,
            role_code=user.role.code if user.role else None,
            is_active=user.is_active,
        ).model_dump(),
    })


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    refresh_payload: dict,
    db: Session = Depends(get_db),
):
    """刷新 Token"""
    token = refresh_payload.get("refresh_token", "")
    payload = auth_service.verify_token(token)
    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError(
            code=ErrorCode.TOKEN_INVALID,
            message="用户不存在",
        )
    token_data = auth_service.create_token(user)
    return ApiResponse(data=TokenResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
    ))


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出（客户端需要丢弃 Token）"""
    return ApiResponse(data={"message": "已登出"})


@router.get("/me", response_model=ApiResponse[UserInfo])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return ApiResponse(data=UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        role_code=current_user.role.code if current_user.role else None,
        is_active=current_user.is_active,
    ))
