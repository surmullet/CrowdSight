"""Authentication and User Management endpoints (JWT Auth & RBAC)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_current_user, get_db, require_role
from crowdsight.service.auth.security import (
    UserRole,
    create_access_token,
    get_password_hash,
    verify_password,
)
from crowdsight.service.storage.models import UserRecord

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Access Control"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., description="Tên đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    email: str
    role: str
    full_name: str
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6)
    role: str = Field(default="OPERATOR", description="ADMIN, OPERATOR, hoặc VIEWER")
    full_name: str = Field(default="")


class UpdateRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(..., description="ADMIN, OPERATOR, hoặc VIEWER")


@router.post("/login", response_model=LoginResponse, summary="Đăng nhập tài khoản và nhận JWT token")
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = db.scalar(
        select(UserRecord).where(UserRecord.username == req.username.strip(), UserRecord.is_active.is_(True))
    )
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "uid": user.id}
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(user),
    )


@router.get("/me", response_model=UserProfileResponse, summary="Lấy thông tin tài khoản hiện tại")
def get_me(
    current_user: UserRecord = Depends(get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.get("/users", response_model=list[UserProfileResponse], summary="Danh sách tài khoản (Chỉ dành cho Admin)")
def list_users(
    db: Session = Depends(get_db),
    _: UserRecord = Depends(require_role(UserRole.ADMIN.value)),
) -> list[UserProfileResponse]:
    users = db.scalars(select(UserRecord).order_by(UserRecord.created_at.desc())).all()
    return [UserProfileResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserProfileResponse, status_code=201, summary="Tạo tài khoản mới (Chỉ dành cho Admin)")
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    _: UserRecord = Depends(require_role(UserRole.ADMIN.value)),
) -> UserProfileResponse:
    valid_roles = {r.value for r in UserRole}
    if req.role.upper() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vai trò không hợp lệ: {req.role}. Các vai trò hợp lệ: {', '.join(valid_roles)}",
        )

    existing = db.scalar(
        select(UserRecord).where((UserRecord.username == req.username.strip()) | (UserRecord.email == req.email.strip()))
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tên đăng nhập hoặc email đã tồn tại trong hệ thống.",
        )

    new_user = UserRecord(
        username=req.username.strip(),
        email=req.email.strip(),
        hashed_password=get_password_hash(req.password),
        role=req.role.upper(),
        full_name=req.full_name.strip(),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserProfileResponse.model_validate(new_user)


@router.put("/users/{user_id}/role", response_model=UserProfileResponse, summary="Thay đổi vai trò tài khoản (Chỉ dành cho Admin)")
def update_user_role(
    user_id: str,
    req: UpdateRoleRequest,
    db: Session = Depends(get_db),
    _: UserRecord = Depends(require_role(UserRole.ADMIN.value)),
) -> UserProfileResponse:
    valid_roles = {r.value for r in UserRole}
    if req.role.upper() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vai trò không hợp lệ: {req.role}. Các vai trò hợp lệ: {', '.join(valid_roles)}",
        )

    target_user = db.get(UserRecord, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    target_user.role = req.role.upper()
    db.commit()
    db.refresh(target_user)
    return UserProfileResponse.model_validate(target_user)
