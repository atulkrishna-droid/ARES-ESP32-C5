"""Authentication API Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenRefreshRequest, TokenResponse, UserLoginRequest, UserRegisterRequest
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    user = AuthService.register(db, request)
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


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    return AuthService.login(db, request.username_or_email, request.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    return AuthService.refresh(db, request.refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Successfully logged out session."}
