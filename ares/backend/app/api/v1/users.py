"""Users API Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
        roles=current_user.role_names,
        permissions=current_user.permission_names,
    )


@router.get("", response_model=List[UserResponse], dependencies=[Depends(require_permission("user.read"))])
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            username=u.username,
            display_name=u.display_name,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
            roles=u.role_names,
            permissions=u.permission_names,
        )
        for u in users
    ]


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_permission("user.write"))])
def update_user(user_id: str, request: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.is_active is not None:
        user.is_active = request.is_active
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        roles=user.role_names,
        permissions=user.permission_names,
    )
